from __future__ import annotations

import json
from pathlib import Path

from ergofit.models import EvidenceItem

_DATA = Path(__file__).resolve().parents[1] / "data" / "evidence.json"


def _load() -> dict[str, EvidenceItem]:
    raw = json.loads(_DATA.read_text(encoding="utf-8"))
    return {item["id"]: EvidenceItem(**item) for item in raw}


EVIDENCE: dict[str, EvidenceItem] = _load()


def get_evidence(evidence_id: str) -> EvidenceItem:
    return EVIDENCE[evidence_id]


def get_many(ids: tuple[str, ...] | list[str]) -> list[EvidenceItem]:
    return [EVIDENCE[i] for i in ids if i in EVIDENCE]
