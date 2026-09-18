from __future__ import annotations

from ergofit.models import Finding, Recommendation


def build_recommendations(ctx: dict, findings: list[Finding]) -> list[Recommendation]:
    recs: list[Recommendation] = []
    titles = {f.title for f in findings}
    regions = set(ctx.get("symptom_regions", []))

    if int(ctx.get("rosa_final", 0)) >= 5:
        recs.append(Recommendation(
            priority="now",
            title="Act on the ROSA drivers",
            action="Review the specific chair, monitor, phone, mouse and keyboard ROSA sub-items that generated the score and correct the highest-exposure items first.",
            rationale="ROSA ≥5 reaches the validated action level for further ergonomic investigation/intervention.",
        ))

    if any("Seat height differs" in t or "Work-surface height differs" in t or "Monitor" in t for t in titles):
        recs.append(Recommendation(
            priority="now",
            title="Correct workstation fit before adding accessories",
            action="Adjust seat height, work-surface relationship and monitor placement using direct body measurements and observed posture. Re-check after adjustment.",
            rationale="Workstation fit is an engineering exposure-control step. The app does not claim a specific disease-risk reduction from a centimetre change.",
        ))

    if ctx.get("glare") or ctx.get("digital_eye_strain"):
        recs.append(Recommendation(
            priority="now",
            title="Review the visual workstation",
            action="Reduce glare/reflections, confirm viewing distance and display position, and follow the organisation's eyesight/occupational-health pathway if visual symptoms persist.",
            rationale="A complete display-screen assessment includes visual symptoms and the visual environment, not only musculoskeletal geometry.",
        ))

    if any(ctx.get(k) is False for k in ("lighting_ok", "noise_ok", "thermal_ok", "software_ok")):
        recs.append(Recommendation(
            priority="soon",
            title="Correct flagged DSE environment factors",
            action="Address lighting, noise, thermal comfort and/or software-interface issues that were marked unsuitable for the task.",
            rationale="The display-screen workstation includes the immediate work environment and software, so these should be controlled as separate ergonomic domains.",
        ))

    if float(ctx.get("sitting_hours", 0)) >= 6 or ctx.get("active_breaks") is False or ctx.get("long_sitting_bout") in {"60–120 min", ">120 min"}:
        recs.append(Recommendation(
            priority="soon",
            title="Increase movement and postural variation",
            action="Use short active breaks and regular position changes that fit the workflow. Avoid presenting one fixed interval as a universal medical threshold.",
            rationale="Office intervention evidence is more supportive of active breaks/postural change than of a single prescribed break schedule.",
            evidence_ids=("waongenngarm_2018_breaks",),
        ))

    neck_terms = {"Neck", "Shoulder(s)", "Αυχένας", "Ώμος/ώμοι"}
    if regions & neck_terms:
        recs.append(Recommendation(
            priority="soon",
            title="Consider targeted neck/shoulder exercise",
            action="Where clinically appropriate, use progressive neck/shoulder/scapular strengthening or workplace micro-exercise rather than treating exercise as a numeric 'protective credit'.",
            rationale="Recent RCT meta-analysis in sedentary workers supports improvement in combined neck/shoulder pain and neck disability, with moderate certainty for selected outcomes.",
            evidence_ids=("yaghoubitajani_2026_microexercise",),
        ))

    back_terms = {"Low back", "Οσφύς / μέση"}
    if regions & back_terms:
        recs.append(Recommendation(
            priority="soon",
            title="Use a multicomponent low-back strategy",
            action="Combine workstation correction with appropriate physical activity/exercise and movement variation; do not rely on chair replacement alone.",
            rationale="Office-worker network meta-analysis suggests only modest/uncertain benefits across many interventions, with some support for physical activity plus ergonomics.",
            evidence_ids=("eisele_2023_back_multicomponent", "channak_2022_chairs"),
        ))

    upper_terms = {"Elbow / forearm / wrist / hand", "Αγκώνας / αντιβράχιο / καρπός / χέρι"}
    if regions & upper_terms and float(ctx.get("mouse_hours", 0)) > 4:
        recs.append(Recommendation(
            priority="soon",
            title="Review mouse reach and forearm support",
            action="Keep the mouse close, minimise unnecessary reach, and consider a suitable forearm-support/alternative-mouse combination when symptoms and task demands justify it.",
            rationale="Cochrane office-worker evidence supports a specific arm-support + alternative-mouse combination for some neck/shoulder outcomes; evidence does not support generic equipment claims.",
            evidence_ids=("hoe_2018_arm_support_mouse",),
        ))

    if ctx.get("high_repetition") or ctx.get("hand_force"):
        recs.append(Recommendation(
            priority="now",
            title="Quantify upper-limb mechanical exposure",
            action="If the job truly involves high repetition or force, use a task-appropriate method such as ACGIH HAL or Strain Index and redesign the task rather than using computer-hours as a proxy.",
            rationale="Prospective CTS evidence is strongest for repetition, force, HAL and Strain Index.",
            evidence_ids=("hassan_2022_cts_repetition", "hassan_2022_cts_force", "hassan_2022_cts_hal", "hassan_2022_cts_si"),
        ))

    if ctx.get("forearm_rotation"):
        recs.append(Recommendation(
            priority="now",
            title="Reduce sustained forearm rotation",
            action="Modify task orientation, tool/device position or work sequence so the forearm can remain closer to neutral and rotate less often/less intensely.",
            rationale="Prospective evidence supports forearm rotation and higher Strain Index as lateral-epicondylitis exposures in relevant occupational tasks.",
            evidence_ids=("bretschneider_2022_le_rotation", "bretschneider_2022_le_si"),
        ))

    if ctx.get("arm_elevation"):
        recs.append(Recommendation(
            priority="now",
            title="Reduce sustained arm elevation",
            action="Bring frequently used items into a lower, closer reach zone and reduce sustained shoulder elevation/loading.",
            rationale="Evidence for specific shoulder disorders comes mainly from manual/mixed occupations, so intervention is justified by the actual exposure, not by an office-worker disease score.",
            evidence_ids=("shoulder_arm_elevation",),
        ))

    if ctx.get("chair_failed"):
        recs.append(Recommendation(
            priority="soon",
            title="Optimise chair fit and adjustability",
            action="Correct the failed fit/adjustability items and trial the chair during real work. Replace the chair only when fit/adjustment cannot be achieved.",
            rationale="Chair-specific intervention evidence for pain prevention is very low/low and conflicting; fit remains a valid engineering objective.",
            evidence_ids=("channak_2022_chairs",),
        ))

    if ctx.get("sleep_problem"):
        recs.append(Recommendation(
            priority="maintain",
            title="Treat sleep as a health-context issue",
            action="If sleep problems are persistent or significant, encourage appropriate sleep-health assessment/support. Do not subtract or add disease-risk points based on sleep duration alone.",
            rationale="Prospective evidence shows a bidirectional association between sleep problems and chronic musculoskeletal pain, but it is not office-specific and does not validate a numeric ErgoFit coefficient.",
            evidence_ids=("runge_2024_sleep_msk",),
        ))

    if not recs:
        recs.append(Recommendation(
            priority="maintain",
            title="Maintain a well-fitted, variable workstation routine",
            action="Continue using the workstation with regular position changes and re-assess if symptoms or task demands change.",
            rationale="No priority ergonomic exposure was identified in this screen.",
        ))

    return recs
