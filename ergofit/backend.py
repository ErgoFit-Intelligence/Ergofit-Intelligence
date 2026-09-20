from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode

import requests


def submit_payload(webhook_url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    if not webhook_url:
        return False, "Webhook is not configured."
    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "text/plain;charset=utf-8"},
            timeout=30,
            allow_redirects=True,
        )
        try:
            body = response.json()
        except Exception:
            return False, f"Non-JSON response ({response.status_code})."
        if body.get("success"):
            return True, f"Row #{body.get('row', '?')} added."
        return False, str(body.get("error", "Unknown backend error"))
    except requests.RequestException as exc:
        return False, f"Network error: {exc}"


def ping_google_sheets_webapp(webapp_url: str, token: str) -> tuple[bool, str]:
    if not webapp_url or not token:
        return False, "Google Sheets web app is not configured."
    try:
        response = requests.get(
            webapp_url,
            params={"action": "ping", "token": token},
            timeout=30,
            allow_redirects=True,
        )
        body = response.json()
        if body.get("success"):
            return True, str(body.get("message", "Connected"))
        return False, str(body.get("error", "Unknown Google Sheets error"))
    except Exception as exc:
        return False, f"Google Sheets connection error: {exc}"


def save_assessment_webapp(
    webapp_url: str,
    token: str,
    payload: dict[str, Any],
) -> tuple[bool, str, str | None]:
    if not webapp_url or not token:
        return False, "Η σύνδεση με το Google Sheets δεν έχει ρυθμιστεί.", None
    try:
        response = requests.post(
            webapp_url,
            data=json.dumps(
                {"token": token, "payload": payload},
                ensure_ascii=False,
            ).encode("utf-8"),
            headers={"Content-Type": "text/plain;charset=utf-8"},
            timeout=45,
            allow_redirects=True,
        )
        try:
            body = response.json()
        except Exception:
            return False, f"Μη έγκυρη απόκριση από το Google Sheets ({response.status_code}).", None

        if body.get("success"):
            assessment_id = body.get("assessment_id")
            return True, "Η αξιολόγηση αποθηκεύτηκε στο Google Sheets.", assessment_id

        return False, str(body.get("error", "Άγνωστο σφάλμα Google Sheets.")), None
    except requests.RequestException as exc:
        return False, f"Σφάλμα σύνδεσης με το Google Sheets: {exc}", None


def list_assessments_webapp(
    webapp_url: str,
    token: str,
    client_id: str,
) -> list[dict[str, Any]]:
    if not webapp_url or not token or not client_id.strip():
        return []

    response = requests.get(
        webapp_url,
        params={
            "action": "list",
            "token": token,
            "client_id": client_id.strip(),
        },
        timeout=30,
        allow_redirects=True,
    )
    body = response.json()
    if not body.get("success"):
        raise RuntimeError(str(body.get("error", "Could not list assessments.")))
    return list(body.get("assessments", []) or [])


def load_assessment_webapp(
    webapp_url: str,
    token: str,
    assessment_id: str,
) -> dict[str, Any] | None:
    if not webapp_url or not token or not assessment_id.strip():
        return None

    response = requests.get(
        webapp_url,
        params={
            "action": "load",
            "token": token,
            "assessment_id": assessment_id.strip(),
        },
        timeout=30,
        allow_redirects=True,
    )
    body = response.json()
    if not body.get("success"):
        raise RuntimeError(str(body.get("error", "Could not load assessment.")))
    payload = body.get("payload")
    return payload if isinstance(payload, dict) else None
