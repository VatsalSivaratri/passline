"""
Step 7: Report Generation

1. Deduplicates violations across modules
2. Sorts by severity
3. Calls Claude API for narrative text per violation
4. Generates PDF
5. Stores report in MongoDB
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from openai import OpenAI

from config import ANVILGPT_API_KEY, ANVILGPT_BASE_URL, ANVILGPT_MODEL, REPORTS_DIR, FRAMES_DIR
from models.audit import Violation, ViolationWithNarrative, RemediationCost

logger = logging.getLogger(__name__)

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

_CLIENT = OpenAI(
    api_key=ANVILGPT_API_KEY,
    base_url=ANVILGPT_BASE_URL,
    timeout=180.0,
)


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def deduplicate_violations(all_violations: List[dict]) -> List[dict]:
    """
    If the same rule_id is violated in multiple modules, keep the most severe.
    Severity is determined by _SEVERITY_ORDER (lower = worse).
    """
    by_rule: dict[str, dict] = {}
    for v in all_violations:
        rid = v["rule_id"]
        if rid not in by_rule:
            by_rule[rid] = v
        else:
            existing_sev = _SEVERITY_ORDER.get(by_rule[rid]["severity"], 99)
            new_sev = _SEVERITY_ORDER.get(v["severity"], 99)
            if new_sev < existing_sev:
                by_rule[rid] = v
    return list(by_rule.values())


def sort_violations(violations: List[dict]) -> List[dict]:
    return sorted(violations, key=lambda v: _SEVERITY_ORDER.get(v.get("severity", "low"), 99))


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------

def compute_score(violations: List[dict], total_checks: int) -> float:
    if total_checks == 0:
        return 100.0
    failed = len(violations)
    passed = max(0, total_checks - failed)
    return round((passed / total_checks) * 100, 1)


def sum_remediation(violations: List[dict]) -> dict:
    low = sum(v.get("remediation_cost", {}).get("low", 0) for v in violations)
    high = sum(v.get("remediation_cost", {}).get("high", 0) for v in violations)
    return {"low": low, "high": high}


# ---------------------------------------------------------------------------
# Narrative generation via Featherless API
# ---------------------------------------------------------------------------

def _generate_narrative_sync(violation: dict, facility: dict) -> dict:
    """Synchronous Featherless API call. Run in thread pool for async contexts."""
    prompt = (
        f"Violation data:\n"
        f"- ADA Section: {violation.get('code', 'N/A')}\n"
        f"- Element: {violation.get('element', 'N/A')}\n"
        f"- Finding: {violation.get('finding', 'N/A')}\n"
        f"- Required standard: {violation.get('required_value', 'N/A')}\n"
        f"- Measurement calibrated: {violation.get('calibrated', False)}\n"
        f"- Estimated remediation cost: "
        f"${violation.get('remediation_cost', {}).get('low', 0)}-"
        f"${violation.get('remediation_cost', {}).get('high', 0)}\n"
        f"- Facility type: {facility.get('facility_type', 'commercial')}\n"
        f"- State: {facility.get('state', 'federal')}\n\n"
        "Return JSON only, no markdown:\n"
        '{"description": "...", "remediation": "...", "priority_rationale": "..."}'
    )

    response = _CLIENT.chat.completions.create(
        model=ANVILGPT_MODEL,
        max_tokens=300,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional ADA compliance consultant writing violation descriptions "
                    "for a building audit report. Be clear, actionable, and cite the specific ADA section. "
                    "Keep each field to 2-3 sentences maximum."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )

    text = response.choices[0].message.content.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Model returned invalid JSON for violation {violation.get('rule_id')}")
        return {
            "description": violation.get("finding", ""),
            "remediation": "Consult a licensed contractor for remediation options.",
            "priority_rationale": f"Severity: {violation.get('severity', 'unknown')}.",
        }


async def generate_narratives(violations: List[dict], facility: dict) -> List[dict]:
    """Generate Claude narrative for each violation concurrently (max 5 at a time)."""
    semaphore = asyncio.Semaphore(5)

    async def _one(v: dict) -> dict:
        async with semaphore:
            loop = asyncio.get_event_loop()
            narrative = await loop.run_in_executor(None, _generate_narrative_sync, v, facility)
            return {**v, **narrative}

    return await asyncio.gather(*[_one(v) for v in violations])


# ---------------------------------------------------------------------------
# PDF Generation
# ---------------------------------------------------------------------------

def generate_pdf(
    audit_id: str,
    facility: dict,
    report: dict,
    module_groups: List[dict],
) -> str:
    """
    Generate PDF report. Returns relative path to PDF file.
    Uses ReportLab for generation.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, PageBreak,
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        pdf_name = f"audit_{audit_id}.pdf"
        pdf_path = REPORTS_DIR / pdf_name
        doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=24, spaceAfter=12)
        h2_style = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=14, spaceAfter=8)
        h3_style = ParagraphStyle("h3", parent=styles["Heading3"], fontSize=12, spaceAfter=6)
        body_style = styles["BodyText"]

        SEVERITY_COLORS = {
            "critical": colors.HexColor("#dc2626"),
            "high": colors.HexColor("#ea580c"),
            "medium": colors.HexColor("#d97706"),
            "low": colors.HexColor("#65a30d"),
        }

        story = []

        # --- Cover Page ---
        story.append(Paragraph("PASSLINE ADA Compliance Audit Report", title_style))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1e40af")))
        story.append(Spacer(1, 0.2 * inch))

        # Facility info table
        facility_data = [
            ["Facility Type", facility.get("facility_type", "—").title()],
            ["State", facility.get("state", "—")],
            ["Building Age", facility.get("building_age", "—")],
            ["Audit Date", report.get("generated_at", datetime.utcnow().strftime("%Y-%m-%d"))],
        ]
        t = Table(facility_data, colWidths=[2 * inch, 4 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3 * inch))

        # Score summary
        score = report.get("overall_score", 0)
        score_color = colors.HexColor("#16a34a") if score >= 80 else (
            colors.HexColor("#d97706") if score >= 60 else colors.HexColor("#dc2626")
        )
        score_style = ParagraphStyle("score", fontSize=48, textColor=score_color, alignment=TA_CENTER)
        story.append(Paragraph(f"Compliance Score: {score}%", score_style))
        story.append(Spacer(1, 0.1 * inch))

        summary_data = [
            ["Total Violations", str(report.get("total_violations", 0))],
            ["Critical Violations", str(report.get("critical_violations", 0))],
            ["Modules Audited", str(report.get("modules_audited", 0))],
            ["Est. Remediation Cost",
             f"${report.get('estimated_remediation_total', {}).get('low', 0):,.0f} – "
             f"${report.get('estimated_remediation_total', {}).get('high', 0):,.0f}"],
        ]
        t2 = Table(summary_data, colWidths=[3 * inch, 3 * inch])
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eff6ff")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ]))
        story.append(t2)
        story.append(PageBreak())

        # --- Violations by Room ---
        story.append(Paragraph("Violations by Room", h2_style))
        story.append(HRFlowable(width="100%", thickness=1))
        story.append(Spacer(1, 0.15 * inch))

        for mg in module_groups:
            module_type = mg.get("module_type", "unknown")
            room_label = mg.get("room_name") or module_type.replace("_", " ").title()
            violations = mg.get("violations", [])

            # Room header
            room_style = ParagraphStyle(
                "room", parent=h2_style, fontSize=13,
                textColor=colors.HexColor("#1e40af"),
                spaceBefore=12, spaceAfter=4,
            )
            story.append(Paragraph(room_label, room_style))
            if not violations:
                story.append(Paragraph("No violations found in this room.", body_style))
                story.append(Spacer(1, 0.1 * inch))
                continue

            for v in violations:
                sev = v.get("severity", "low")
                sev_color = SEVERITY_COLORS.get(sev, colors.grey)
                sev_style = ParagraphStyle("sev", parent=h3_style, textColor=sev_color)
                story.append(Paragraph(
                    f"[{sev.upper()}] {v.get('element', '')} — {v.get('code', '')}",
                    sev_style,
                ))
                story.append(Paragraph(f"<b>Finding:</b> {v.get('finding', '')}", body_style))
                if v.get("description"):
                    story.append(Paragraph(f"<b>Description:</b> {v['description']}", body_style))
                if v.get("remediation"):
                    story.append(Paragraph(f"<b>Remediation:</b> {v['remediation']}", body_style))
                if v.get("priority_rationale"):
                    story.append(Paragraph(f"<b>Priority:</b> {v['priority_rationale']}", body_style))
                cost = v.get("remediation_cost", {})
                story.append(Paragraph(
                    f"<b>Estimated Cost:</b> ${cost.get('low', 0):,.0f} – ${cost.get('high', 0):,.0f}",
                    body_style,
                ))
                story.append(Spacer(1, 0.12 * inch))
                story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
                story.append(Spacer(1, 0.08 * inch))

            story.append(Spacer(1, 0.1 * inch))

        doc.build(story)
        logger.info(f"PDF generated: {pdf_path}")
        return pdf_name

    except ImportError:
        logger.error("ReportLab not installed. Skipping PDF generation.")
        return ""
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        return ""


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------

async def generate_report(
    audit_id: str,
    audit_doc: dict,
    db,
) -> dict:
    """
    Full report generation pipeline.
    Violations are kept per-module — no deduplication. The same violation
    type appearing in two rooms is listed under each room separately.
    """
    facility = audit_doc.get("facility", {})
    modules = audit_doc.get("modules", [])
    applicable_rules = audit_doc.get("applicable_rules", [])

    # Build per-module violation groups (preserve all, no dedup)
    module_groups = []
    all_violations = []
    for m in modules:
        if m.get("status") != "complete":
            continue
        mvs = sort_violations(m.get("violations", []))
        module_groups.append({
            "module_id": m["module_id"],
            "module_type": m.get("module_type", "unknown"),
            "room_name": m.get("room_name"),
            "violations": mvs,
        })
        all_violations.extend(mvs)

    # Score across all violations (no dedup)
    total_checks = len(applicable_rules)
    score = compute_score(all_violations, total_checks)
    cost_total = sum_remediation(all_violations)
    critical_count = sum(1 for v in all_violations if v.get("severity") == "critical")

    # Generate narratives for every violation
    logger.info(f"Generating narratives for {len(all_violations)} violations...")
    try:
        all_with_narratives = await generate_narratives(all_violations, facility)
    except Exception as e:
        logger.error(f"Narrative generation failed: {e}. Using raw violations.")
        all_with_narratives = [
            {**v, "description": v.get("finding", ""), "remediation": "", "priority_rationale": ""}
            for v in all_violations
        ]

    # Re-attach narratives back to per-module groups
    narrative_by_id = {v["violation_id"]: v for v in all_with_narratives}
    module_groups_with_narratives = [
        {
            **mg,
            "violations": [narrative_by_id.get(v["violation_id"], v) for v in mg["violations"]],
        }
        for mg in module_groups
    ]

    # Generate PDF
    generated_at = datetime.utcnow().isoformat()
    report_partial = {
        "overall_score": score,
        "total_violations": len(all_violations),
        "critical_violations": critical_count,
        "modules_audited": len(module_groups),
        "estimated_remediation_total": cost_total,
        "generated_at": generated_at,
        "pdf_path": None,
    }

    pdf_name = generate_pdf(
        audit_id, facility, report_partial, module_groups_with_narratives
    )
    report_partial["pdf_path"] = pdf_name or None

    # Flat list for API response (preserves all violations in order)
    flat_violations = [v for mg in module_groups_with_narratives for v in mg["violations"]]

    # Persist to MongoDB
    await db["audits"].update_one(
        {"audit_id": audit_id},
        {
            "$set": {
                "report": {
                    **report_partial,
                    "violations": flat_violations,
                    "module_violations": module_groups_with_narratives,
                },
                "updated_at": datetime.utcnow().isoformat(),
            }
        },
    )

    return {**report_partial, "violations": flat_violations, "module_violations": module_groups_with_narratives}
