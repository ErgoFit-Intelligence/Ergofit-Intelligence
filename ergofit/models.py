from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional


@dataclass(frozen=True)
class EvidenceItem:
    id: str
    title: str
    exposure: str
    outcome: str
    effect_measure: str
    estimate: Optional[float]
    ci_low: Optional[float]
    ci_high: Optional[float]
    year: int
    study_type: str
    population: str
    n_studies: Optional[int]
    sample_size: Optional[int]
    certainty: str
    office_applicability: str
    temporal_design: str
    source_label: str
    source_url: str
    notes: str = ""
    predictive_use: bool = False

    def effect_text(self) -> str:
        if self.estimate is None:
            return "No pooled effect estimate"
        value = f"{self.effect_measure} {self.estimate:.2f}"
        if self.ci_low is not None and self.ci_high is not None:
            value += f" (95% CI {self.ci_low:.2f}–{self.ci_high:.2f})"
        return value

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Finding:
    domain: str
    title: str
    status: str  # information | attention | priority
    detail: str
    evidence_ids: tuple[str, ...] = ()
    modifiable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Recommendation:
    priority: str  # now | soon | maintain
    title: str
    action: str
    rationale: str
    evidence_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
