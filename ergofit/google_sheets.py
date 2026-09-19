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

COMPARISON_HEADERS = [
    "Κωδικός πελάτη","Εταιρεία","Τμήμα","Θέση εργασίας","Γραμμή","ID αξιολόγησης","Ημερομηνία",
    "ROSA","Αυχένας 0-10","Ώμος 0-10","Άνω άκρο 0-10","Μέση 0-10","Κάτω άκρα 0-10",
    "Περιοχές με συμπτώματα","Άμεση προτεραιότητα","Χρειάζεται προσοχή","Θέματα καρέκλας",
    "Ευρήματα στάσης","Ενεργά διαλείμματα","Κόπωση ματιών","Σημειώσεις"
]

REGIONS = {
    "Neck": "neck",
    "Shoulder(s)": "shoulder",
    "Elbow / forearm / wrist / hand": "upper_limb",
    "Low back": "low_back",
    "Lower limbs": "lower_limb",
}


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


def _yn_el(v: Any) -> str:
    if v is True:
        return "ΝΑΙ"
    if v is False:
        return "ΟΧΙ"
    return "—"


def _upsert_client(book, assessment: dict[str, Any]) -> None:
    client_id = str(assessment.get("subject_id", "")).strip()
    if not client_id:
        return

    ws = book.worksheet("Clients")
    values = [
        client_id,
        str(assessment.get("client_name_or_code", client_id) or client_id),
        str(assessment.get("company", "") or ""),
        str(assessment.get("department", "") or ""),
        str(assessment.get("job_title", "") or ""),
        assessment.get("age", ""),
        assessment.get("sex", ""),
        assessment.get("height", ""),
        assessment.get("weight", ""),
        _now(),
        "TRUE",
        "",
    ]

    try:
        cell = ws.find(client_id, in_column=1)
    except Exception:
        cell = None

    if cell:
        # Keep original created_at when available.
        existing = ws.row_values(cell.row)
        if len(existing) >= 10 and existing[9]:
            values[9] = existing[9]
        ws.update(f"A{cell.row}:L{cell.row}", [values], value_input_option="USER_ENTERED")
    else:
        ws.append_row(values, value_input_option="USER_ENTERED")


def _symptom_score(assessment: dict[str, Any], region_key: str) -> int:
    details = assessment.get("symptom_details", {}) or {}
    item = details.get(region_key, {}) or {}
    try:
        return int(item.get("severity", 0) or 0)
    except Exception:
        return 0


def _summary_values(payload: dict[str, Any], assessment_id: str) -> list[Any]:
    assessment = payload.get("assessment", {}) or {}
    findings = payload.get("findings", []) or []
    rosa = assessment.get("rosa", {}) or {}

    priority_count = sum(
        1 for f in findings
        if isinstance(f, dict) and f.get("status") == "priority"
    )
    attention_count = sum(
        1 for f in findings
        if isinstance(f, dict) and f.get("status") == "attention"
    )

    symptom_details = assessment.get("symptom_details", {}) or {}
    symptomatic_regions = sum(
        1 for item in symptom_details.values()
        if isinstance(item, dict) and int(item.get("severity", 0) or 0) > 0
    )

    return [
        str(assessment.get("subject_id", "") or ""),
        str(assessment.get("company", "") or ""),
        str(assessment.get("department", "") or ""),
        str(assessment.get("job_title", "") or ""),
        "",  # line type filled by caller
        assessment_id,
        str(assessment.get("assessment_date", "") or ""),
        int(rosa.get("final", assessment.get("rosa_final", 0)) or 0),
        _symptom_score(assessment, "Neck"),
        _symptom_score(assessment, "Shoulder(s)"),
        _symptom_score(assessment, "Elbow / forearm / wrist / hand"),
        _symptom_score(assessment, "Low back"),
        _symptom_score(assessment, "Lower limbs"),
        symptomatic_regions,
        priority_count,
        attention_count,
        len(assessment.get("chair_failed", []) or []),
        len(assessment.get("posture_out", []) or []),
        _yn_el(assessment.get("active_breaks")),
        _yn_el(assessment.get("digital_eye_strain")),
        "",
    ]


def _difference_values(
    baseline_payload: dict[str, Any],
    followup_payload: dict[str, Any],
    baseline_id: str,
    followup_id: str,
) -> list[Any]:
    before = _summary_values(baseline_payload, baseline_id)
    after = _summary_values(followup_payload, followup_id)

    # Numeric comparison columns: after - before. Negative means reduction.
    diff = after.copy()
    diff[4] = "Διαφορά (μετά - πριν)"
    diff[5] = f"{baseline_id} → {followup_id}"
    diff[6] = str((followup_payload.get("assessment", {}) or {}).get("assessment_date", "") or "")

    for idx in range(7, 18):
        try:
            diff[idx] = float(after[idx]) - float(before[idx])
            if isinstance(after[idx], int) and isinstance(before[idx], int):
                diff[idx] = int(diff[idx])
        except Exception:
            diff[idx] = ""

    diff[18] = f"{before[18]} → {after[18]}"
    diff[19] = f"{before[19]} → {after[19]}"
    diff[20] = "Στις αριθμητικές στήλες: αρνητική τιμή = μείωση, θετική τιμή = αύξηση."
    return diff


def _get_payload_by_id(book, assessment_id: str) -> dict[str, Any] | None:
    if not assessment_id:
        return None
    records = book.worksheet("Assessments").get_all_records()
    for record in records:
        if str(record.get("assessment_id", "")).strip() == assessment_id.strip():
            raw = record.get("payload_json", "")
            if raw:
                return json.loads(raw)
    return None


def _comparison_block_start(ws, client_id: str) -> int | None:
    values = ws.get_all_values()
    for idx, row in enumerate(values[1:], start=2):
        if row and str(row[0]).strip() == client_id and len(row) > 4 and row[4] == "1η Αξιολόγηση":
            return idx
    return None


def _write_comparison_block(
    book,
    payload: dict[str, Any],
    assessment_id: str,
    stage: str,
    parent_id: str,
) -> None:
    ws = book.worksheet("Πριν_Μετά")
    assessment = payload.get("assessment", {}) or {}
    client_id = str(assessment.get("subject_id", "")).strip()
    if not client_id:
        return

    start_row = _comparison_block_start(ws, client_id)

    if stage == "baseline":
        baseline_row = _summary_values(payload, assessment_id)
        baseline_row[4] = "1η Αξιολόγηση"

        if start_row is None:
            followup_placeholder = [
                client_id,
                str(assessment.get("company", "") or ""),
                str(assessment.get("department", "") or ""),
                str(assessment.get("job_title", "") or ""),
                "2η Αξιολόγηση",
            ] + [""] * (len(COMPARISON_HEADERS) - 5)
            difference_placeholder = [
                client_id,
                str(assessment.get("company", "") or ""),
                str(assessment.get("department", "") or ""),
                str(assessment.get("job_title", "") or ""),
                "Διαφορά (μετά - πριν)",
            ] + [""] * (len(COMPARISON_HEADERS) - 5)
            ws.append_rows(
                [baseline_row, followup_placeholder, difference_placeholder],
                value_input_option="USER_ENTERED",
            )
        else:
            ws.update(
                f"A{start_row}:U{start_row}",
                [baseline_row],
                value_input_option="USER_ENTERED",
            )
        return

    # Follow-up: fill the second line and calculate the third.
    if start_row is None:
        baseline_payload = _get_payload_by_id(book, parent_id)
        if baseline_payload:
            baseline_row = _summary_values(baseline_payload, parent_id)
            baseline_row[4] = "1η Αξιολόγηση"
            ws.append_rows(
                [
                    baseline_row,
                    [client_id, baseline_row[1], baseline_row[2], baseline_row[3], "2η Αξιολόγηση"] + [""] * (len(COMPARISON_HEADERS) - 5),
                    [client_id, baseline_row[1], baseline_row[2], baseline_row[3], "Διαφορά (μετά - πριν)"] + [""] * (len(COMPARISON_HEADERS) - 5),
                ],
                value_input_option="USER_ENTERED",
            )
            start_row = _comparison_block_start(ws, client_id)

    if start_row is None:
        return

    followup_row = _summary_values(payload, assessment_id)
    followup_row[4] = "2η Αξιολόγηση"
    ws.update(
        f"A{start_row + 1}:U{start_row + 1}",
        [followup_row],
        value_input_option="USER_ENTERED",
    )

    baseline_payload = _get_payload_by_id(book, parent_id)
    if baseline_payload:
        diff_row = _difference_values(
            baseline_payload,
            payload,
            parent_id,
            assessment_id,
        )
        ws.update(
            f"A{start_row + 2}:U{start_row + 2}",
            [diff_row],
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

        client_id = str(assessment.get("subject_id", "")).strip()
        if not client_id:
            return False, "Χρειάζεται όνομα ή κωδικός πελάτη πριν από την αποθήκευση.", None

        stage = str(assessment.get("assessment_stage", "baseline"))
        assessment_id = str(assessment.get("assessment_id", "")).strip() or _new_id("EF")
        parent_id = str(assessment.get("parent_assessment_id", "") or "")

        company = str(assessment.get("company", "") or "")
        department = str(assessment.get("department", "") or "")
        _upsert_client(book, assessment)

        rosa = assessment.get("rosa", {}) or {}
        chair_failed = assessment.get("chair_failed", []) or []
        posture_out = assessment.get("posture_out", []) or []

        row_map = {
            "assessment_id": assessment_id,
            "worker_id": client_id,
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
                    client_id,
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
                    client_id,
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
                    client_id,
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

        _write_comparison_block(book, payload, assessment_id, stage, parent_id)

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
    return _get_payload_by_id(book, assessment_id)
