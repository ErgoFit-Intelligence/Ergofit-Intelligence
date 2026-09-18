from __future__ import annotations

from dataclasses import dataclass


# Stature-derived seated ratios retained only as fallback estimates.
# The v2 architecture deliberately labels these as estimates, not exact targets.
RATIOS = {
    "female": {"popliteal": 0.239, "elbow": 0.135, "eye": 0.453},
    "male": {"popliteal": 0.247, "elbow": 0.131, "eye": 0.451},
    "other": {"popliteal": 0.243, "elbow": 0.133, "eye": 0.452},
}


@dataclass(frozen=True)
class AnthropometryReference:
    popliteal_cm: float
    seated_elbow_cm: float
    seated_eye_cm: float
    source_popliteal: str
    source_elbow: str
    source_eye: str

    @property
    def desk_reference_cm(self) -> float:
        return round(self.popliteal_cm + self.seated_elbow_cm, 1)


def reference_from_stature(
    stature_cm: float,
    sex: str,
    popliteal_direct: float = 0.0,
    elbow_direct: float = 0.0,
    eye_direct: float = 0.0,
) -> AnthropometryReference:
    ratios = RATIOS.get(sex, RATIOS["other"])

    pop = float(popliteal_direct) if popliteal_direct > 0 else stature_cm * ratios["popliteal"]
    elbow = float(elbow_direct) if elbow_direct > 0 else stature_cm * ratios["elbow"]
    eye = float(eye_direct) if eye_direct > 0 else stature_cm * ratios["eye"]

    return AnthropometryReference(
        popliteal_cm=round(pop, 1),
        seated_elbow_cm=round(elbow, 1),
        seated_eye_cm=round(eye, 1),
        source_popliteal="direct" if popliteal_direct > 0 else "estimated",
        source_elbow="direct" if elbow_direct > 0 else "estimated",
        source_eye="direct" if eye_direct > 0 else "estimated",
    )


def bmi(weight_kg: float, stature_cm: float) -> float:
    if stature_cm <= 0:
        return 0.0
    return round(weight_kg / ((stature_cm / 100.0) ** 2), 1)


def bmi_band(value: float) -> str:
    if value <= 0:
        return "unknown"
    if value < 18.5:
        return "underweight"
    if value < 25:
        return "normal"
    if value < 30:
        return "overweight"
    return "obese"
