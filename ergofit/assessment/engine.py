from __future__ import annotations

from ergofit.models import Finding
from ergofit.science.anthropometry import bmi_band
from ergofit.science.standards import MONITOR_DISTANCE_REFERENCE_CM


def build_findings(ctx: dict) -> list[Finding]:
    findings: list[Finding] = []

    # Symptoms are findings, not diagnoses.
    regions = ctx.get("symptom_regions", [])
    severity = int(ctx.get("symptom_severity", 0))
    if regions:
        status = "priority" if severity >= 7 or ctx.get("symptom_interference") else "attention"
        findings.append(Finding(
            domain="Symptoms",
            title="Current/recent musculoskeletal symptoms",
            status=status,
            detail=f"Reported regions: {', '.join(regions)}; intensity {severity}/10. This is symptom information, not a diagnosis.",
            modifiable=False,
        ))

    # Computer exposure is linked to broad CANS, not CTS specifically.
    if max(float(ctx.get("computer_hours", 0)), float(ctx.get("mouse_hours", 0))) > 4:
        findings.append(Finding(
            domain="Computer exposure",
            title="Computer/mouse exposure >4 h/day",
            status="attention",
            detail="Prospective computer-worker evidence supports a small increase in broad arm/neck/shoulder complaints (CANS). This does not validate CTS prediction from computer hours.",
            evidence_ids=("rijal_2026_cans_4h",),
        ))

    sitting = float(ctx.get("sitting_hours", 0))
    if sitting >= 6:
        findings.append(Finding(
            domain="Sedentary exposure",
            title="High occupational sitting exposure",
            status="attention",
            detail="≥6 h/day is used here as an operational exposure flag, not as a study-derived causal threshold. Sitting–pain associations are mainly cross-sectional.",
            evidence_ids=("dzakpasu_2021_lbp_sitting", "dzakpasu_2021_neck_shoulder_sitting", "mahdavi_2022_lbp_sitting"),
        ))

    if ctx.get("long_sitting_bout") in {"60–120 min", ">120 min"}:
        findings.append(Finding(
            domain="Sedentary exposure",
            title="Long uninterrupted sitting bouts",
            status="attention",
            detail="Long static bouts reduce postural variation. The app does not treat any single break interval as a medical threshold.",
            evidence_ids=("waongenngarm_2018_breaks",),
        ))

    if ctx.get("active_breaks") is False:
        findings.append(Finding(
            domain="Movement variation",
            title="Limited active breaks / postural variation",
            status="attention",
            detail="Office-worker intervention evidence supports active breaks and postural change more consistently than passive rest or a fixed universal interval.",
            evidence_ids=("waongenngarm_2018_breaks",),
        ))

    if ctx.get("high_repetition"):
        findings.append(Finding(
            domain="Upper-limb mechanical exposure",
            title="High hand/wrist repetition",
            status="priority",
            detail="This exposure has prospective evidence for clinically assessed CTS in occupational cohorts. Applicability depends on whether the task resembles the studied high-repetition work.",
            evidence_ids=("hassan_2022_cts_repetition",),
        ))
    if ctx.get("hand_force"):
        findings.append(Finding(
            domain="Upper-limb mechanical exposure",
            title="Meaningful hand/finger force",
            status="priority",
            detail="Prospective occupational evidence links force intensity with clinically assessed CTS; typical office tasks often have much lower force.",
            evidence_ids=("hassan_2022_cts_force",),
        ))
    if ctx.get("forearm_rotation"):
        findings.append(Finding(
            domain="Upper-limb mechanical exposure",
            title="Substantial forearm rotation exposure",
            status="priority",
            detail="Prospective evidence supports an association with lateral epicondylitis when exposure is substantial.",
            evidence_ids=("bretschneider_2022_le_rotation",),
        ))
    if ctx.get("arm_elevation"):
        findings.append(Finding(
            domain="Shoulder exposure",
            title="Sustained arm elevation / shoulder load",
            status="priority",
            detail="Evidence is mainly from manual/mixed occupations and is indirect for standard office work; use only because actual exposure was reported.",
            evidence_ids=("shoulder_arm_elevation",),
        ))

    # Workstation fit: operational screening, not a validated disease score.
    seat_actual = float(ctx.get("seat_height", 0))
    seat_ref = float(ctx.get("seat_reference", 0))
    if seat_actual > 0 and seat_ref > 0 and abs(seat_actual - seat_ref) > 2.5:
        findings.append(Finding(
            domain="Workstation fit",
            title="Seat height differs from body-fit reference",
            status="attention",
            detail=f"Measured {seat_actual:.1f} cm vs reference {seat_ref:.1f} cm. The ±2.5 cm flag is an operational fitting tolerance, not a disease threshold.",
        ))

    desk_actual = float(ctx.get("desk_height", 0))
    desk_ref = float(ctx.get("desk_reference", 0))
    if desk_actual > 0 and desk_ref > 0 and abs(desk_actual - desk_ref) > 3.0:
        findings.append(Finding(
            domain="Workstation fit",
            title="Work-surface height differs from elbow-height reference",
            status="attention",
            detail=f"Measured {desk_actual:.1f} cm vs reference {desk_ref:.1f} cm. Treat this as a fit prompt and confirm shoulder/elbow posture directly.",
        ))

    distance = float(ctx.get("monitor_distance", 0))
    lo, hi = MONITOR_DISTANCE_REFERENCE_CM
    if distance > 0 and not (lo <= distance <= hi):
        findings.append(Finding(
            domain="Visual workstation",
            title="Monitor viewing distance outside reference range",
            status="attention",
            detail=f"Measured {distance:.0f} cm. Reference guidance commonly places the display roughly {lo}–{hi} cm away, adjusted for display size, visual needs and task.",
        ))

    if ctx.get("monitor_top") in {"above", "well_below"}:
        findings.append(Finding(
            domain="Visual workstation",
            title="Monitor vertical position needs review",
            status="attention",
            detail="Use eye level, screen centre, viewing distance and corrective-lens needs together. v2 does not convert monitor height into a neck-disease coefficient.",
        ))

    if ctx.get("keyboard_close") is False:
        findings.append(Finding(
            domain="Input devices",
            title="Keyboard/mouse positioned away from the body",
            status="attention",
            detail="Reaching can increase static shoulder/upper-limb demand; assess actual posture and task variation.",
            evidence_ids=("jun_2017_neck_office",),
        ))
    if ctx.get("forearm_support") is False:
        findings.append(Finding(
            domain="Input devices",
            title="Limited forearm support",
            status="attention",
            detail="Where symptoms/exposure justify it, arm support combined with an alternative mouse has some office-RCT evidence for neck/shoulder outcomes.",
            evidence_ids=("hoe_2018_arm_support_mouse",),
        ))
    if ctx.get("glare"):
        findings.append(Finding(
            domain="Environment",
            title="Glare / reflections reported",
            status="attention",
            detail="Visual-environment factors belong in a complete DSE assessment and should be corrected independently of musculoskeletal disease scoring.",
        ))

    if ctx.get("digital_eye_strain"):
        findings.append(Finding(
            domain="Visual symptoms",
            title="Digital eye strain / visual fatigue reported",
            status="attention",
            detail="Treat this as a visual/DSE symptom finding. It is not combined with the musculoskeletal evidence profile or a disease score.",
            modifiable=False,
        ))

    env_flags = []
    for key, label in [("lighting_ok", "lighting"), ("noise_ok", "noise"), ("thermal_ok", "thermal comfort"), ("software_ok", "software/interface ergonomics")]:
        if ctx.get(key) is False:
            env_flags.append(label)
    if env_flags:
        findings.append(Finding(
            domain="DSE environment",
            title="Work-environment factors need review",
            status="attention",
            detail="Flagged: " + ", ".join(env_flags) + ". These belong in a complete display-screen assessment and are not converted into MSD probability points.",
        ))

    chair_failed = ctx.get("chair_failed", [])
    if chair_failed:
        findings.append(Finding(
            domain="Chair fit",
            title=f"{len(chair_failed)} chair fit/adjustability issue(s)",
            status="attention" if len(chair_failed) < 4 else "priority",
            detail="Chair findings are engineering/fit findings. Chair replacement alone should not be presented as a validated treatment for back pain.",
            evidence_ids=("channak_2022_chairs",),
        ))

    posture_out = ctx.get("posture_out", [])
    if posture_out:
        findings.append(Finding(
            domain="Posture & movement",
            title=f"{len(posture_out)} joint-specific posture reference finding(s)",
            status="attention",
            detail="These are reference observations. v2 deliberately does not aggregate them into an overall posture percentage or disease-risk category.",
            evidence_ids=("jahn_2023_lbp_posture",),
        ))

    rosa_final = int(ctx.get("rosa_final", 0))
    if rosa_final >= 5:
        findings.append(Finding(
            domain="ROSA",
            title=f"ROSA action level reached ({rosa_final}/10)",
            status="priority",
            detail="The original ROSA validation supports score 5 as an action level for further ergonomic investigation/intervention.",
        ))
    elif rosa_final > 0:
        findings.append(Finding(
            domain="ROSA",
            title=f"ROSA below action level ({rosa_final}/10)",
            status="information",
            detail="Below the validated action level of 5. This is not interpreted as a clinical low-risk disease category.",
        ))

    # Contextual health factors: shown, never subtracted from disease risk.
    band = bmi_band(float(ctx.get("bmi", 0)))
    if band in {"overweight", "obese"}:
        evidence_id = "shiri_2015_cts_bmi_obese" if band == "obese" else "shiri_2015_cts_bmi_overweight"
        findings.append(Finding(
            domain="Health context",
            title=f"BMI category: {band}",
            status="information",
            detail="BMI can be associated with some musculoskeletal/neuropathic outcomes, but it is not an ergonomic exposure and is not converted into an ErgoFit disease score.",
            evidence_ids=(evidence_id,),
            modifiable=False,
        ))

    if ctx.get("sleep_problem"):
        findings.append(Finding(
            domain="Health context",
            title="Sleep concern",
            status="information",
            detail="Sleep problems and chronic musculoskeletal pain are prospectively associated and bidirectional. v2 treats sleep as context, not as a numeric protective/risk credit.",
            evidence_ids=("runge_2024_sleep_msk",),
            modifiable=False,
        ))

    if ctx.get("job_demand") or ctx.get("low_control") or ctx.get("low_support"):
        findings.append(Finding(
            domain="Psychosocial context",
            title="Psychosocial work factors flagged",
            status="attention",
            detail="Psychosocial and organisational factors can contribute to symptom development/persistence. They are kept separate from workstation geometry and disease prediction.",
            evidence_ids=("jun_2017_neck_office",),
        ))

    return findings


def evidence_ids_for_context(ctx: dict, findings: list[Finding]) -> list[str]:
    ids: list[str] = []
    for f in findings:
        ids.extend(f.evidence_ids)

    regions = set(ctx.get("symptom_regions", []))
    if "Neck" in regions or "Shoulder(s)" in regions or "Αυχένας" in regions or "Ώμος/ώμοι" in regions:
        ids.append("yaghoubitajani_2026_microexercise")
    if "Low back" in regions or "Οσφύς / μέση" in regions:
        ids.append("eisele_2023_back_multicomponent")
    if ctx.get("exercise"):
        # Exercise is not a credit; no extra disease evidence card is required here.
        pass
    return list(dict.fromkeys(ids))
