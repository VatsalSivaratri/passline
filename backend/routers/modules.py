import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from config import UPLOAD_DIR, FRAMES_DIR, MODULE_INSTRUCTIONS
from pydantic import BaseModel
from models.audit import CreateModuleRequest, CreateModuleResponse, ModuleStatusResponse

class RenameModuleRequest(BaseModel):
    room_name: str
from services.video_processing import extract_key_frames, VideoProcessingError
from services.calibration import calibrate_frames
from services.depth_estimation import process_frames_depth
from services.gemini_analysis import AnalysisError, analyze_features, classify_room
from services.feature_rules import check_feature_compliance

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# POST /audits/{audit_id}/modules
# ---------------------------------------------------------------------------

@router.post("/audits/{audit_id}/modules")
async def create_module(
    audit_id: str,
    body: CreateModuleRequest,
    request: Request,
):
    db = request.app.state.db
    audit = await db["audits"].find_one({"audit_id": audit_id})
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    module_id = str(uuid.uuid4())
    instructions_data = MODULE_INSTRUCTIONS.get(body.module_type, {})
    instructions = instructions_data.get("instructions", "Record the area slowly and steadily.")

    module_doc = {
        "module_id": module_id,
        "module_type": body.module_type,
        "status": "created",
        "progress": 0,
        "video_path": None,
        "key_frames": [],
        "gemini_analysis": None,
        "depth_measurements": None,
        "calibrated": False,
        "violations": [],
        "annotated_frames": [],
        "depth_map_frames": [],
        "error_message": None,
        "warnings": [],
    }

    await db["audits"].update_one(
        {"audit_id": audit_id},
        {
            "$push": {"modules": module_doc},
            "$set": {"updated_at": datetime.utcnow().isoformat()},
        },
    )

    return CreateModuleResponse(module_id=module_id, instructions=instructions)


# ---------------------------------------------------------------------------
# PATCH /audits/{audit_id}/modules/{module_id}/name
# ---------------------------------------------------------------------------

@router.patch("/audits/{audit_id}/modules/{module_id}/name")
async def rename_module(
    audit_id: str,
    module_id: str,
    body: RenameModuleRequest,
    request: Request,
):
    db = request.app.state.db
    audit = await db["audits"].find_one({"audit_id": audit_id})
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    if not _find_module(audit, module_id):
        raise HTTPException(status_code=404, detail="Module not found")
    await _update_module(db, audit_id, module_id, {"room_name": body.room_name.strip()})
    return {"ok": True}


# ---------------------------------------------------------------------------
# POST /audits/{audit_id}/modules/{module_id}/upload
# ---------------------------------------------------------------------------

@router.post("/audits/{audit_id}/modules/{module_id}/upload")
async def upload_video(
    audit_id: str,
    module_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
):
    db = request.app.state.db
    audit = await db["audits"].find_one({"audit_id": audit_id})
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    module = _find_module(audit, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Save video to disk
    ext = Path(video.filename).suffix if video.filename else ".mp4"
    video_filename = f"{audit_id}_{module_id}{ext}"
    video_path = UPLOAD_DIR / video_filename

    contents = await video.read()
    with open(str(video_path), "wb") as f:
        f.write(contents)

    # Update status to uploading→extracting_frames
    await _update_module(db, audit_id, module_id, {
        "status": "extracting_frames",
        "progress": 5,
        "video_path": str(video_path),
    })

    # Kick off async pipeline
    background_tasks.add_task(
        run_processing_pipeline,
        audit_id=audit_id,
        module_id=module_id,
        module_type=module["module_type"],
        video_path=str(video_path),
        db=db,
        depth_estimator=request.app.state.depth_estimator,
    )

    return {"status": "processing", "module_id": module_id}


# ---------------------------------------------------------------------------
# GET /audits/{audit_id}/modules/{module_id}/status
# ---------------------------------------------------------------------------

@router.get("/audits/{audit_id}/modules/{module_id}/status")
async def get_module_status(audit_id: str, module_id: str, request: Request):
    db = request.app.state.db
    audit = await db["audits"].find_one({"audit_id": audit_id})
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    module = _find_module(audit, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    violations_found = len(module.get("violations", [])) if module.get("status") == "complete" else None

    return ModuleStatusResponse(
        status=module.get("status", "unknown"),
        progress=module.get("progress", 0),
        module_type=module.get("module_type"),
        violations_found=violations_found,
        error_message=module.get("error_message"),
    )


# ---------------------------------------------------------------------------
# GET /audits/{audit_id}/modules/{module_id}/results
# ---------------------------------------------------------------------------

@router.get("/audits/{audit_id}/modules/{module_id}/results")
async def get_module_results(audit_id: str, module_id: str, request: Request):
    db = request.app.state.db
    audit = await db["audits"].find_one({"audit_id": audit_id})
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    module = _find_module(audit, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    if module.get("status") not in ("complete", "error"):
        raise HTTPException(status_code=202, detail="Processing not yet complete")

    return {
        "module_type": module.get("module_type"),
        "gemini_analysis": module.get("gemini_analysis"),
        "depth_measurements": module.get("depth_measurements"),
        "calibrated": module.get("calibrated", False),
        "violations": module.get("violations", []),
        "annotated_frames": module.get("annotated_frames", []),
        "depth_map_frames": module.get("depth_map_frames", []),
        "warnings": module.get("warnings", []),
    }


# ---------------------------------------------------------------------------
# Processing pipeline (runs in background)
# ---------------------------------------------------------------------------

async def run_processing_pipeline(
    audit_id: str,
    module_id: str,
    module_type: str,
    video_path: str,
    db,
    depth_estimator,
):
    # Anything that degraded the result without stopping it. Saved with the
    # module so the report can say what was not checked, instead of hiding it.
    warnings: list = []
    try:
        # --- Step 3: Extract key frames ---
        await _update_module(db, audit_id, module_id, {
            "status": "extracting_frames", "progress": 10
        })
        frame_paths = await extract_key_frames(video_path, audit_id, module_id)

        # --- Step 3b: Auto-classify room type if not specified ---
        if module_type == "auto":
            await _update_module(db, audit_id, module_id, {
                "status": "classifying", "progress": 12,
            })
            try:
                module_type = await classify_room(frame_paths)
            except AnalysisError as e:
                # Feature rules don't depend on room type, so the run can continue,
                # but it must not claim a room type it doesn't know.
                logger.error(f"Room classification failed for module {module_id}: {e}")
                module_type = "unclassified"
                warnings.append(f"Room type could not be determined: {e}")
            await _update_module(db, audit_id, module_id, {
                "module_type": module_type, "progress": 18,
            })
            logger.info(f"Module {module_id} auto-classified as: {module_type}")

        # --- Step 4: Calibration ---
        await _update_module(db, audit_id, module_id, {
            "status": "analyzing", "progress": 25, "key_frames": frame_paths
        })
        frames_bgr = []
        for p in frame_paths:
            img = cv2.imread(str(FRAMES_DIR / p))
            if img is not None:
                frames_bgr.append(img)

        from services.calibration import calibrate_frames
        calibration = calibrate_frames(frames_bgr)

        # --- Step 5A: Gemini feature detection ---
        await _update_module(db, audit_id, module_id, {"progress": 40})
        # No fallback here: with no detections there is nothing to check, and an
        # empty list would read as "no violations". AnalysisError goes to the
        # handler below and marks the module as errored.
        features_result = await analyze_features(frame_paths)

        features = features_result.get("features", [])
        await _update_module(db, audit_id, module_id, {
            "gemini_analysis": features_result, "progress": 55
        })

        # --- Step 5B: Depth estimation ---
        await _update_module(db, audit_id, module_id, {"progress": 60})
        if depth_estimator is None:
            from services.depth_estimation import DepthEstimator
            depth_estimator = DepthEstimator()

        depth_result = process_frames_depth(
            frame_paths, audit_id, module_id, depth_estimator, features_result, calibration
        )
        measurements = depth_result["measurements"]
        depth_map_frames = depth_result["depth_map_frames"]
        if not depth_result["depth_available"]:
            warnings.append("Depth model unavailable: no measurements were taken.")

        # --- Annotated frames ---
        await _update_module(db, audit_id, module_id, {"progress": 75})
        annotated_frames = _generate_annotated_frames(
            frame_paths, audit_id, module_id, features_result
        )

        # --- Step 6: Compliance check ---
        await _update_module(db, audit_id, module_id, {
            "status": "checking_compliance", "progress": 85
        })

        violations = check_feature_compliance(
            features=features,
            module_id=module_id,
            depth_measurements=measurements,
            calibrated=calibration["calibrated"],
        )

        violations_dicts = [v.model_dump() for v in violations]

        # --- Complete ---
        await _update_module(db, audit_id, module_id, {
            "status": "complete",
            "progress": 100,
            "gemini_analysis": features_result,
            "depth_measurements": measurements,
            "calibrated": calibration["calibrated"],
            "violations": violations_dicts,
            "annotated_frames": annotated_frames,
            "depth_map_frames": depth_map_frames,
            "warnings": warnings,
        })
        logger.info(f"Module {module_id} complete. {len(violations_dicts)} violation(s) found.")

    except AnalysisError as e:
        logger.error(f"Feature detection failed for module {module_id}: {e}")
        await _update_module(db, audit_id, module_id, {
            "status": "error",
            "error_message": f"Feature detection failed, so this space was not checked: {e}",
            "warnings": warnings,
        })
    except VideoProcessingError as e:
        logger.error(f"Video processing error for module {module_id}: {e}")
        await _update_module(db, audit_id, module_id, {
            "status": "error",
            "error_message": str(e),
        })
    except Exception as e:
        logger.exception(f"Unexpected error in pipeline for module {module_id}: {e}")
        await _update_module(db, audit_id, module_id, {
            "status": "error",
            "error_message": f"Unexpected error: {str(e)[:200]}",
        })


# ---------------------------------------------------------------------------
# Annotated frame generation
# ---------------------------------------------------------------------------

def _generate_annotated_frames(
    frame_paths: list,
    audit_id: str,
    module_id: str,
    gemini_result: dict,
) -> list:
    """Draw bounding boxes and feature labels on frames using OpenCV."""
    annotated = []
    out_dir = FRAMES_DIR / audit_id / module_id

    # Group features by frame_index
    features = gemini_result.get("features", [])
    features_by_frame: dict[int, list] = {}
    for f in features:
        idx = f.get("frame_index", 0)
        features_by_frame.setdefault(idx, []).append(f)

    # Color palette per feature type (cycles through a fixed set)
    _COLORS = [
        (0, 255, 0),    # green
        (255, 165, 0),  # orange
        (0, 200, 255),  # cyan
        (255, 0, 128),  # pink
        (128, 0, 255),  # purple
        (0, 255, 180),  # teal
        (255, 220, 0),  # yellow
        (200, 100, 0),  # brown
    ]
    _type_colors: dict[str, tuple] = {}

    def _color_for(ftype: str) -> tuple:
        if ftype not in _type_colors:
            _type_colors[ftype] = _COLORS[len(_type_colors) % len(_COLORS)]
        return _type_colors[ftype]

    def _bbox_coords(bbox, img_w, img_h):
        if not bbox:
            return None
        try:
            return (
                int(float(bbox["x1"]) * img_w),
                int(float(bbox["y1"]) * img_h),
                int(float(bbox["x2"]) * img_w),
                int(float(bbox["y2"]) * img_h),
            )
        except (TypeError, ValueError, KeyError):
            return None

    for i, rel_path in enumerate(frame_paths):
        full_path = FRAMES_DIR / rel_path
        img = cv2.imread(str(full_path))
        if img is None:
            continue

        h, w = img.shape[:2]

        for feature in features_by_frame.get(i, []):
            ftype = feature.get("feature_type", "feature")
            bbox = feature.get("bounding_box")
            color = _color_for(ftype)
            label = ftype.replace("_", " ")

            coords = _bbox_coords(bbox, w, h)
            if coords:
                x1, y1, x2, y2 = coords
                cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
                # Label background for readability
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
                cv2.rectangle(img, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
                cv2.putText(img, label, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)
            else:
                # No bbox — print label in top-left corner area, stacked
                y_offset = 20 + list(features_by_frame.get(i, [])).index(feature) * 22
                cv2.putText(img, label, (8, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        ann_name = f"annotated_{i + 1:03d}.jpg"
        ann_path = out_dir / ann_name
        cv2.imwrite(str(ann_path), img)
        annotated.append(f"{audit_id}/{module_id}/{ann_name}")

    return annotated


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_module(audit: dict, module_id: str) -> Optional[dict]:
    for m in audit.get("modules", []):
        if m.get("module_id") == module_id:
            return m
    return None


async def _update_module(db, audit_id: str, module_id: str, updates: dict):
    set_fields = {f"modules.$.{k}": v for k, v in updates.items()}
    set_fields["updated_at"] = datetime.utcnow().isoformat()
    await db["audits"].update_one(
        {"audit_id": audit_id, "modules.module_id": module_id},
        {"$set": set_fields},
    )
