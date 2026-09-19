from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import gspread
from google.oauth2.service_account import Credentials


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

ASSESSMENT_HEADERS = [
    "assessment_id","worker_id","company","department","assessment_stage","assessment_date",
    "parent_assessment_id","age","sex","height_cm","weight_kg","bmi","computer_hours_day",
    "mouse_hours_day","sitting_hours_day","longest_same_posture_min","active_breaks",
    "digital_eye_strain","high_repetition","hand_force","forearm_rotation","arm_elevation",
    "job_demand","low_control","low_support","seat_height_cm","desk_height_cm",
    "monitor_distance_cm","monitor_top","keyboard_close","forearm_support","glare","lighting_ok",
    "noise_ok","thermal_ok","software_ok","chair_failed_count","posture_findings_count",
    "rosa_chair","rosa_section_b","rosa_section_c","rosa_monitor_peripherals","rosa_final",
    "interventions_notes","payload_json"
]


def _client(service_account_info: dict[str, Any]) -> gspread.Client:
    credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    return gspread.authorize(credentials)


def _open(service_account_info: dict[str, Any], spreadsheet_id: str):
    return _client(service_account_info).open_by_key(spreadsheet_id)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"


def _bool(v: Any) -> str:
    if v is True:
        return "TRUE"
    if v is False:
        return "FALSE"
    return ""


def _ensure_worker(book, worker_id: str, company: str, department: str) -> None:
    if not worker_id:
        return
    ws = book.worksheet("Workers")
    try:
        cell = ws.find(worker_id, in_column=1)
    except Exception:
        cell = None
    if cell:
        return
    ws.append_row(
        [worker_id, company, department, worker_id, _now(), "TRUE", ""],
        value_input_option="USER_ENTERED",
    )


def save_assessment(
    service_account_info: dict[str, Any],
    spreadsheet_id: str,
    payload: dict[str, Any],
) -> tuple[bool, str, str | None]:
    try:
        book = _open(service_account_info, spreadsheet_id)
        assessment = payload.get("assessment", {}) or {}
        findings = payload.get("findings", []) or []

        worker_id = str(assessment.get("subject_id", "")).strip()
        if not worker_id:
            return False, "Χρειάζεται κωδικός εργαζομένου πριν από την αποθήκευση.", None

        stage = str(assessment.get("assessment_stage", "baseline"))
        assessment_id = str(assessment.get("assessment_id", "")).strip() or _new_id("EF")
        parent_id = str(assessment.get("parent_assessment_id", "") or "")

        company = str(assessment.get("company", "") or "")
        department = str(assessment.get("department", "") or "")
        _ensure_worker(book, worker_id, company, department)

        rosa = assessment.get("rosa", {}) or {}
        chair_failed = assessment.get("chair_failed", []) or []
        posture_out = assessment.get("posture_out", []) or []

        row_map = {
            "assessment_id": assessment_id,
            "worker_id": worker_id,
            "company": company,
            "department": department,
            "assessment_stage": stage,
            "assessment_date": str(assessment.get("assessment_date", "")),
            "parent_assessment_id": parent_id,
            "age": assessment.get("age", ""),
            "sex": assessment.get("sex", ""),
            "height_cm": assessment.get("height", ""),
            "weight_kg": assessment.get("weight", ""),
            "bmi": assessment.get("bmi", ""),
            "computer_hours_day": assessment.get("computer_hours", ""),
            "mouse_hours_day": assessment.get("mouse_hours", ""),
            "sitting_hours_day": assessment.get("sitting_hours", ""),
            "longest_same_posture_min": assessment.get("long_sitting_bout", ""),
            "active_breaks": _bool(assessment.get("active_breaks")),
            "digital_eye_strain": _bool(assessment.get("digital_eye_strain")),
            "high_repetition": _bool(assessment.get("high_repetition")),
            "hand_force": _bool(assessment.get("hand_force")),
            "forearm_rotation": _bool(assessment.get("forearm_rotation")),
            "arm_elevation": _bool(assessment.get("arm_elevation")),
            "job_demand": _bool(assessment.get("job_demand")),
            "low_control": _bool(assessment.get("low_control")),
            "low_support": _bool(assessment.get("low_support")),
            "seat_height_cm": assessment.get("seat_height", ""),
            "desk_height_cm": assessment.get("desk_height", ""),
            "monitor_distance_cm": assessment.get("monitor_distance", ""),
            "monitor_top": assessment.get("monitor_top", ""),
            "keyboard_close": _bool(assessment.get("keyboard_close")),
            "forearm_support": _bool(assessment.get("forearm_support")),
            "glare": _bool(assessment.get("glare")),
            "lighting_ok": _bool(assessment.get("lighting_ok")),
            "noise_ok": _bool(assessment.get("noise_ok")),
            "thermal_ok": _bool(assessment.get("thermal_ok")),
            "software_ok": _bool(assessment.get("software_ok")),
            "chair_failed_count": len(chair_failed),
            "posture_findings_count": len(posture_out),
            "rosa_chair": rosa.get("chair", ""),
            "rosa_section_b": rosa.get("section_b", ""),
            "rosa_section_c": rosa.get("section_c", ""),
            "rosa_monitor_peripherals": rosa.get("monitor_peripherals", ""),
            "rosa_final": rosa.get("final", assessment.get("rosa_final", "")),
            "interventions_notes": assessment.get("interventions_notes", ""),
            "payload_json": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        }

        book.worksheet("Assessments").append_row(
            [row_map.get(h, "") for h in ASSESSMENT_HEADERS],
            value_input_option="USER_ENTERED",
        )

        symptoms_ws = book.worksheet("Symptoms")
        for region, item in (assessment.get("symptom_details", {}) or {}).items():
            symptoms_ws.append_row(
                [
                    assessment_id,
                    worker_id,
                    stage,
                    str(assessment.get("assessment_date", "")),
                    region,
                    item.get("severity", 0),
                    _bool(item.get("interference")),
                    item.get("label", region),
                    _now(),
                ],
                value_input_option="USER_ENTERED",
            )

        findings_ws = book.worksheet("Findings")
        for finding in findings:
            findings_ws.append_row(
                [
                    assessment_id,
                    worker_id,
                    stage,
                    str(assessment.get("assessment_date", "")),
                    finding.get("domain", ""),
                    finding.get("status", ""),
                    finding.get("title", ""),
                    finding.get("detail", ""),
                    _bool(finding.get("modifiable")),
                    ",".join(finding.get("evidence_ids", []) or []),
                    _now(),
                ],
                value_input_option="USER_ENTERED",
            )

        if stage == "followup" and str(assessment.get("interventions_notes", "")).strip():
            book.worksheet("Interventions").append_row(
                [
                    _new_id("INT"),
                    worker_id,
                    parent_id,
                    assessment_id,
                    str(assessment.get("assessment_date", "")),
                    "ergonomic_intervention",
                    str(assessment.get("interventions_notes", "")).strip(),
                    "completed",
                    "",
                    _now(),
                ],
                value_input_option="USER_ENTERED",
            )

        return True, "Η αξιολόγηση αποθηκεύτηκε στο Google Sheets.", assessment_id
    except Exception as exc:
        return False, f"Αποτυχία αποθήκευσης στο Google Sheets: {exc}", None


def list_worker_assessments(
    service_account_info: dict[str, Any],
    spreadsheet_id: str,
    worker_id: str,
) -> list[dict[str, Any]]:
    if not worker_id.strip():
        return []
    book = _open(service_account_info, spreadsheet_id)
    records = book.worksheet("Assessments").get_all_records()
    matches = [r for r in records if str(r.get("worker_id", "")).strip() == worker_id.strip()]
    matches.sort(key=lambda r: str(r.get("assessment_date", "")), reverse=True)
    return matches


def load_assessment_payload(
    service_account_info: dict[str, Any],
    spreadsheet_id: str,
    assessment_id: str,
) -> dict[str, Any] | None:
    book = _open(service_account_info, spreadsheet_id)
    records = book.worksheet("Assessments").get_all_records()
    for record in records:
        if str(record.get("assessment_id", "")).strip() == assessment_id.strip():
            raw = record.get("payload_json", "")
            if raw:
                return json.loads(raw)
    return None
