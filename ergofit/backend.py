from __future__ import annotations

import json
from typing import Any

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
