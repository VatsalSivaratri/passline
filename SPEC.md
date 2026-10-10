# Passline: system specification

What the code does today. For the target design and the reasoning behind it, see `DECISIONS.md` and the Limitations section of the README.

## Components

| Component | Technology | Location |
| --- | --- | --- |
| Frontend | Next.js 14, React 18, TypeScript, Tailwind | `frontend/` |
| API | FastAPI, Pydantic v2, Python 3.12 | `backend/main.py`, `backend/routers/` |
| Processing | Runs in the API process via FastAPI `BackgroundTasks` | `backend/routers/modules.py` |
| Database | MongoDB through Motor (async) | `MONGODB_URI` |
| Vision model | Google Gemini via `google-genai` | `backend/services/gemini_analysis.py` |
| Depth model | Depth Anything V2 metric ViT-S (Hypersim), PyTorch or ONNX Runtime | `backend/services/depth_backends.py` |
| Report text | OpenAI-compatible endpoint (Purdue AnvilGPT) | `backend/services/report_generator.py` |
| PDF | ReportLab | `backend/services/report_generator.py` |
| File storage | Local directories, served as static files | `uploads/`, `frames/`, `reports/` |

## User flow

1. Create an audit and answer the facility questionnaire (`/audit/[id]/questionnaire`).
2. See suggested spaces for the facility type (`/audit/[id]/modules`).
3. Record or upload a video per space (`/audit/[id]/capture/[moduleType]`). The space type can be chosen or left as `auto`.
4. Watch processing status (`/audit/[id]/processing/[moduleId]`).
5. Generate and view the report, download the PDF (`/audit/[id]/report`).

## API

All routes are under `/api`. Static files are served at `/uploads`, `/frames` and `/reports`. `GET /health` returns `{"status": "ok"}`.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/audits` | Create an audit; returns `audit_id` |
| PUT | `/audits/{audit_id}/questionnaire` | Save facility info; returns suggested modules and a rule count |
| GET | `/audits/{audit_id}` | Full audit document |
| POST | `/audits/{audit_id}/modules` | Create a module (one space) with a `module_type` or `auto` |
| PATCH | `/audits/{audit_id}/modules/{module_id}/name` | Rename a module |
| POST | `/audits/{audit_id}/modules/{module_id}/upload` | Upload the video (multipart `video`); starts processing |
| GET | `/audits/{audit_id}/modules/{module_id}/status` | Status, progress, violation count, error message |
| GET | `/audits/{audit_id}/modules/{module_id}/results` | Detections, measurements, violations, frames, warnings |
| POST | `/audits/{audit_id}/report` | Start report generation for completed modules |
| GET | `/audits/{audit_id}/report` | Report summary and violations with narratives |
| GET | `/audits/{audit_id}/report/pdf` | Download the PDF |

## Data model

One MongoDB document per audit (collection `audits`), with modules embedded as an array.

```
audit
  audit_id, created_at, updated_at
  facility: { state, facility_type, building_age, recent_renovation, renovation_cost, parking_spaces }
  applicable_rules: [rule_id]        from the questionnaire
  modules: [module]
  report: { overall_score, total_violations, critical_violations, violations, pdf_path, ... }

module
  module_id, module_type, room_name
  status: created | extracting_frames | classifying | analyzing | checking_compliance | complete | error
  progress: 0-100
  video_path, key_frames, annotated_frames, depth_map_frames
  gemini_analysis: { features: [...] }
  depth_measurements, calibrated
  violations: [violation]
  warnings: [string]                 degradations that did not stop processing
  error_message

violation
  violation_id, module_id, module_type, rule_id
  code ("ADA §404.2.7"), element, finding, severity (critical | high | medium | low)
  calibrated, confidence, remediation_cost: { low, high }
```

## Processing pipeline (per module)

| Step | Code | Behavior | On failure |
| --- | --- | --- | --- |
| 1. Frames | `video_processing.extract_key_frames` | FFmpeg at 2 fps; blur filter relative to 2 neighbors on each side (drop if under half their median Laplacian variance, never judge frames below a texture floor); SSIM dedup at 0.92; greedy selection of up to 20 distinct frames | `VideoProcessingError`; module status `error` |
| 2. Room type | `gemini_analysis.classify_room` | Only when `module_type == "auto"`; one of 34 types | Continues as `unclassified` with a warning |
| 3. Calibration | `calibration.calibrate_frames` | Credit card or letter paper; Canny at 3 downscaled sizes with morphological closing; aspect within 10%, rectangularity at least 0.85; returns pixels per inch at full resolution | Uncalibrated; not an error |
| 4. Features | `gemini_analysis.analyze_features` | Up to 16 frames; temperature 0; response schema with 39 feature types and typed properties | `AnalysisError`; module status `error` |
| 5. Depth | `depth_estimation.process_frames_depth` | Metric depth per frame; colorized maps saved | Warning "Depth model unavailable"; no depth maps |
| 6. Rules | `rules_engine.evaluate` | Each feature checked against rules for its type | Rules that cannot evaluate a value are logged and skipped |
| 7. Save | `routers/modules.py` | Annotated frames, results and warnings written to the module | |

Step 5 computes depth but no measurement currently feeds step 6. All current rules read properties reported by the vision model.

## Rules

`backend/data/rules.yaml`, evaluated by `backend/services/rules_engine.py`. 45 rules citing 40 sections of the 2010 ADA Standards.

```yaml
- id: door_hardware_knob
  feature_type: door_hardware
  section: 404.2.7
  element: Door Hardware
  severity: high
  when:
    all:
    - field: handle_type
      op: in
      value: [round_knob, knob]
  finding: Round knob hardware requires tight grasp; lever-style hardware required.
  remediation_cost_usd: [75, 200]
```

- `when` holds exactly one of `all` (every clause) or `any` (at least one).
- Ops: `eq`, `in`, `is` (identity, for true/false), `is_not`, `gt`. A clause may set `default` for an absent property.
- `finding` may include `{property}` placeholders.
- Rules load through Pydantic models; duplicate IDs and malformed conditions fail at load time.
- `remediation_cost_usd` values are unsourced estimates carried over from the hackathon version.

## Report

`report_generator.generate_report` groups violations by module (no merging across rooms), sorts by severity, asks the LLM endpoint for a description, remediation and priority note per violation, sums remediation ranges, and writes a PDF.

Known issues: the overall score divides by the number of rules selected from the older `data/rule_table.json` by the questionnaire, not by the YAML rule set, so it is not meaningful; cost ranges are unsourced; LLM text is not checked against the rule data.

## Configuration

Environment variables in `backend/.env`; see `backend/.env.example` and the README. Tunable constants (frame rate, SSIM threshold, frame limits, blur parameters, calibration thresholds) are module-level constants in `config.py`, `video_processing.py` and `calibration.py`.

## Legacy files

`backend/data/rule_table.json`, `backend/services/compliance_checker.py` and `backend/models/rules.py` hold the earlier module-level rule table. They are used only for the questionnaire's rule count and module suggestions. `backend/db_adapter.py` (a JSON-file stand-in for MongoDB) and `backend/list_models.py` are not used by the app.
