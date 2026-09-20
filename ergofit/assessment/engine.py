from __future__ import annotations

from ergofit.models import Finding
from ergofit.science.anthropometry import bmi_band
from ergofit.science.standards import MONITOR_DISTANCE_REFERENCE_CM


def build_findings(ctx: dict, lang: str = "en") -> list[Finding]:
    findings: list[Finding] = []
    tr = lambda en, el: en if lang == "en" else el

    # Symptoms are recorded separately by body region; they are findings, not diagnoses.
    regions = ctx.get("symptom_regions", [])
    symptom_details = ctx.get("symptom_details", {}) or {}
    if symptom_details:
        for region in regions:
            item = symptom_details.get(region, {})
            label = item.get("label", region)
            severity = int(item.get("severity", 0))
            if severity <= 0:
                continue
            interference = bool(item.get("interference", False))
            duration = str(item.get("duration", "not_recorded") or "not_recorded")
            frequency = str(item.get("frequency", "not_recorded") or "not_recorded")
            previous_episode = item.get("previous_episode")
            work_modification = item.get("work_modification")
            absence_days = int(item.get("absence_days_4w", 0) or 0)
            functional_impact = interference or work_modification is True or absence_days > 0
            persistent_or_recurrent = duration == ">12_weeks" or previous_episode is True or frequency == "daily"
            status = "attention" if functional_impact or persistent_or_recurrent else "information"
            findings.append(Finding(
                domain="Symptoms",
                title=tr(f"Symptom: {label}", f"Σύμπτωμα: {label}"),
                status=status,
                detail=tr(
                    f"Intensity {severity}/10; duration {duration}; frequency {frequency}; work interference: {'yes' if interference else 'no/unknown'}; work absence (last 4 weeks): {absence_days} day(s). No single pain-intensity cutoff is used as a validated prognostic threshold.",
                    f"Ένταση {severity}/10· διάρκεια {duration}· συχνότητα {frequency}· επίδραση στην εργασία: {'ναι' if interference else 'όχι/δεν καταγράφηκε'}· απουσία από την εργασία τις τελευταίες 4 εβδομάδες: {absence_days} ημέρα/ημέρες. Δεν χρησιμοποιείται κανένα μεμονωμένο όριο έντασης πόνου ως επικυρωμένο προγνωστικό threshold."
                ),
                modifiable=False,
            ))
    elif regions:
        severity = int(ctx.get("symptom_severity", 0))
        status = "attention" if ctx.get("symptom_interference") else "information"
        findings.append(Finding(
            domain="Symptoms",
            title=tr("Current/recent musculoskeletal symptoms", "Τρέχοντα/πρόσφατα μυοσκελετικά συμπτώματα"),
            status=status,
            detail=tr(
                f"Reported regions: {', '.join(regions)}; intensity {severity}/10. This is symptom information, not a diagnosis.",
                f"Αναφερόμενες περιοχές: {', '.join(regions)}· ένταση {severity}/10. Πρόκειται για πληροφορία συμπτωμάτων και όχι για διάγνωση."
            ),
            modifiable=False,
        ))

    # Computer exposure is linked to broad CANS, not CTS specifically.
    if max(float(ctx.get("computer_hours", 0)), float(ctx.get("mouse_hours", 0))) > 4:
        findings.append(Finding(
            domain="Computer exposure",
            title=tr("Computer/mouse exposure >4 h/day", "Έκθεση σε υπολογιστή/ποντίκι >4 ώρες/ημέρα"),
            status="attention",
            detail=tr(
                "Prospective computer-worker evidence supports a small increase in broad arm/neck/shoulder complaints (CANS). This does not validate CTS prediction from computer hours.",
                "Προοπτικά δεδομένα σε εργαζομένους που χρησιμοποιούν υπολογιστή υποστηρίζουν μικρή αύξηση ευρύτερων ενοχλήσεων άνω άκρου/αυχένα/ώμου. Αυτό δεν επικυρώνει πρόβλεψη συνδρόμου καρπιαίου σωλήνα από τις ώρες χρήσης υπολογιστή."
            ),
            evidence_ids=("rijal_2026_cans_4h",),
        ))

    sitting = float(ctx.get("sitting_hours", 0))
    if sitting >= 6:
        findings.append(Finding(
            domain="Sedentary exposure",
            title=tr("High occupational sitting exposure", "Υψηλή έκθεση σε καθιστική εργασία"),
            status="attention",
            detail=tr(
                "≥6 h/day is used here as an operational exposure flag, not as a study-derived causal threshold. Sitting–pain associations are mainly cross-sectional.",
                "Οι ≥6 ώρες/ημέρα χρησιμοποιούνται εδώ ως λειτουργική ένδειξη υψηλής έκθεσης και όχι ως αιτιώδες όριο που προέκυψε από μελέτη. Οι συσχετίσεις μεταξύ καθιστικής εργασίας και πόνου προέρχονται κυρίως από διατομεακά δεδομένα."
            ),
            evidence_ids=("dzakpasu_2021_lbp_sitting", "dzakpasu_2021_neck_shoulder_sitting", "mahdavi_2022_lbp_sitting"),
        ))

    if ctx.get("long_sitting_bout") in {"60–120 min", ">120 min"}:
        findings.append(Finding(
            domain="Sedentary exposure",
            title=tr("Long uninterrupted sitting bouts", "Μεγάλα συνεχόμενα διαστήματα καθιστικής εργασίας"),
            status="attention",
            detail=tr(
                "Long static bouts reduce postural variation. The app does not treat any single break interval as a medical threshold.",
                "Τα μεγάλα στατικά διαστήματα μειώνουν τη μεταβλητότητα της στάσης. Το εργαλείο δεν θεωρεί κανένα συγκεκριμένο διάστημα διαλείμματος ως ιατρικό όριο."
            ),
            evidence_ids=("waongenngarm_2018_breaks",),
        ))

    if ctx.get("active_breaks") is False:
        findings.append(Finding(
            domain="Movement variation",
            title=tr("Limited active breaks / postural variation", "Περιορισμένα ενεργά διαλείμματα / περιορισμένη εναλλαγή στάσης"),
            status="attention",
            detail=tr(
                "Office-worker intervention evidence supports active breaks and postural change more consistently than passive rest or a fixed universal interval.",
                "Τα δεδομένα παρεμβάσεων σε εργαζομένους γραφείου υποστηρίζουν πιο σταθερά τα ενεργά διαλείμματα και τις αλλαγές στάσης σε σχέση με την παθητική ανάπαυση ή ένα ενιαίο καθολικό διάστημα."
            ),
            evidence_ids=("waongenngarm_2018_breaks",),
        ))

    if ctx.get("high_repetition"):
        findings.append(Finding(
            domain="Upper-limb mechanical exposure",
            title=tr("High hand/wrist repetition", "Υψηλή επανάληψη κινήσεων χεριού/καρπού"),
            status="priority",
            detail=tr(
                "This exposure has prospective evidence for clinically assessed CTS in occupational cohorts. Applicability depends on whether the task resembles the studied high-repetition work.",
                "Υπάρχουν προοπτικά δεδομένα που συνδέουν αυτή την έκθεση με κλινικά αξιολογημένο σύνδρομο καρπιαίου σωλήνα σε επαγγελματικούς πληθυσμούς. Η εφαρμοσιμότητα εξαρτάται από το αν η εργασία μοιάζει με τις εργασίες υψηλής επανάληψης που μελετήθηκαν."
            ),
            evidence_ids=("hassan_2022_cts_repetition",),
        ))
    if ctx.get("hand_force"):
        findings.append(Finding(
            domain="Upper-limb mechanical exposure",
            title=tr("Meaningful hand/finger force", "Σημαντική δύναμη χεριού/δακτύλων"),
            status="priority",
            detail=tr(
                "Prospective occupational evidence links force intensity with clinically assessed CTS; typical office tasks often have much lower force.",
                "Προοπτικά επαγγελματικά δεδομένα συνδέουν την ένταση δύναμης με κλινικά αξιολογημένο σύνδρομο καρπιαίου σωλήνα· οι συνήθεις εργασίες γραφείου έχουν συχνά πολύ χαμηλότερη απαίτηση δύναμης."
            ),
            evidence_ids=("hassan_2022_cts_force",),
        ))
    if ctx.get("forearm_rotation"):
        findings.append(Finding(
            domain="Upper-limb mechanical exposure",
            title=tr("Substantial forearm rotation exposure", "Σημαντική έκθεση σε στροφή αντιβραχίου"),
            status="priority",
            detail=tr(
                "Prospective evidence supports an association with lateral epicondylitis when exposure is substantial.",
                "Προοπτικά δεδομένα υποστηρίζουν συσχέτιση με έξω επικονδυλίτιδα όταν η έκθεση σε στροφή αντιβραχίου είναι σημαντική."
            ),
            evidence_ids=("bretschneider_2022_le_rotation",),
        ))
    if ctx.get("arm_elevation"):
        findings.append(Finding(
            domain="Shoulder exposure",
            title=tr("Sustained arm elevation / shoulder load", "Παρατεταμένη ανύψωση βραχίονα / φόρτιση ώμου"),
            status="priority",
            detail=tr(
                "Evidence is mainly from manual/mixed occupations and is indirect for standard office work; use only because actual exposure was reported.",
                "Η τεκμηρίωση προέρχεται κυρίως από χειρωνακτικά/μικτά επαγγέλματα και είναι έμμεση για τη συνήθη εργασία γραφείου. Το εύρημα χρησιμοποιείται μόνο επειδή δηλώθηκε πραγματική έκθεση."
            ),
            evidence_ids=("shoulder_arm_elevation",),
        ))

    # Workstation fit: operational screening, not a validated disease score.
    seat_actual = float(ctx.get("seat_height", 0))
    seat_ref = float(ctx.get("seat_reference", 0))
    if seat_actual > 0 and seat_ref > 0 and abs(seat_actual - seat_ref) > 2.5:
        findings.append(Finding(
            domain="Workstation fit",
            title=tr("Seat height differs from body-fit reference", "Το ύψος της έδρας διαφέρει από τη σωματομετρική τιμή αναφοράς"),
            status="attention",
            detail=tr(
                f"Measured {seat_actual:.1f} cm vs reference {seat_ref:.1f} cm. The ±2.5 cm flag is an operational fitting tolerance, not a disease threshold.",
                f"Μετρήθηκαν {seat_actual:.1f} cm έναντι τιμής αναφοράς {seat_ref:.1f} cm. Η απόκλιση ±2,5 cm είναι λειτουργικό όριο προσαρμογής και όχι όριο κινδύνου νόσου."
            ),
        ))

    desk_actual = float(ctx.get("desk_height", 0))
    desk_ref = float(ctx.get("desk_reference", 0))
    if desk_actual > 0 and desk_ref > 0 and abs(desk_actual - desk_ref) > 3.0:
        findings.append(Finding(
            domain="Workstation fit",
            title=tr("Work-surface height differs from elbow-height reference", "Το ύψος της επιφάνειας εργασίας διαφέρει από την αναφορά ύψους αγκώνα"),
            status="attention",
            detail=tr(
                f"Measured {desk_actual:.1f} cm vs reference {desk_ref:.1f} cm. Treat this as a fit prompt and confirm shoulder/elbow posture directly.",
                f"Μετρήθηκαν {desk_actual:.1f} cm έναντι τιμής αναφοράς {desk_ref:.1f} cm. Χρησιμοποίησέ το ως ένδειξη προσαρμογής και επιβεβαίωσε άμεσα τη στάση ώμου και αγκώνα."
            ),
        ))

    distance = float(ctx.get("monitor_distance", 0))
    lo, hi = MONITOR_DISTANCE_REFERENCE_CM
    if distance > 0 and not (lo <= distance <= hi):
        findings.append(Finding(
            domain="Visual workstation",
            title=tr("Monitor viewing distance outside reference range", "Η απόσταση θέασης της οθόνης βρίσκεται εκτός του εύρους αναφοράς"),
            status="attention",
            detail=tr(
                f"Measured {distance:.0f} cm. Reference guidance commonly places the display roughly {lo}–{hi} cm away, adjusted for display size, visual needs and task.",
                f"Μετρήθηκαν {distance:.0f} cm. Οι οδηγίες αναφοράς τοποθετούν συνήθως την οθόνη περίπου στα {lo}–{hi} cm, με προσαρμογή ανάλογα με το μέγεθος οθόνης, τις οπτικές ανάγκες και την εργασία."
            ),
        ))

    if ctx.get("monitor_top") in {"above", "well_below"}:
        findings.append(Finding(
            domain="Visual workstation",
            title=tr("Monitor vertical position needs review", "Η κατακόρυφη θέση της οθόνης χρειάζεται έλεγχο"),
            status="attention",
            detail=tr(
                "Use eye level, screen centre, viewing distance and corrective-lens needs together. v2 does not convert monitor height into a neck-disease coefficient.",
                "Αξιολόγησε μαζί το ύψος των ματιών, το κέντρο της οθόνης, την απόσταση θέασης και τυχόν ανάγκες διορθωτικών φακών. Η v2 δεν μετατρέπει το ύψος της οθόνης σε συντελεστή κινδύνου πάθησης του αυχένα."
            ),
        ))

    if ctx.get("keyboard_close") is False:
        findings.append(Finding(
            domain="Input devices",
            title=tr("Keyboard/mouse positioned away from the body", "Πληκτρολόγιο/ποντίκι τοποθετημένα μακριά από το σώμα"),
            status="attention",
            detail=tr(
                "Reaching can increase static shoulder/upper-limb demand; assess actual posture and task variation.",
                "Το τέντωμα του χεριού μπορεί να αυξήσει τη στατική επιβάρυνση ώμου/άνω άκρου. Αξιολόγησε την πραγματική στάση και τη μεταβλητότητα της εργασίας."
            ),
            evidence_ids=("jun_2017_neck_office",),
        ))
    if ctx.get("forearm_support") is False:
        findings.append(Finding(
            domain="Input devices",
            title=tr("Limited forearm support", "Περιορισμένη στήριξη αντιβραχίων"),
            status="attention",
            detail=tr(
                "Where symptoms/exposure justify it, arm support combined with an alternative mouse has some office-RCT evidence for neck/shoulder outcomes.",
                "Όταν τα συμπτώματα και η έκθεση το δικαιολογούν, ο συνδυασμός στήριξης αντιβραχίων και εναλλακτικού ποντικιού έχει ορισμένη τεκμηρίωση από τυχαιοποιημένες μελέτες γραφείου για αποτελέσματα αυχένα/ώμου."
            ),
            evidence_ids=("hoe_2018_arm_support_mouse",),
        ))
    if ctx.get("glare"):
        findings.append(Finding(
            domain="Environment",
            title=tr("Glare / reflections reported", "Αναφέρθηκε θάμβωση / ενοχλητικές αντανακλάσεις"),
            status="attention",
            detail=tr(
                "Visual-environment factors belong in a complete DSE assessment and should be corrected independently of musculoskeletal disease scoring.",
                "Οι παράγοντες του οπτικού περιβάλλοντος αποτελούν μέρος μιας πλήρους αξιολόγησης εργασίας με οθόνη και πρέπει να διορθώνονται ανεξάρτητα από οποιαδήποτε βαθμολόγηση μυοσκελετικής νόσου."
            ),
        ))

    if ctx.get("digital_eye_strain"):
        findings.append(Finding(
            domain="Visual symptoms",
            title=tr("Digital eye strain / visual fatigue reported", "Αναφέρθηκε ψηφιακή κόπωση ματιών / οπτική κόπωση"),
            status="attention",
            detail=tr(
                "Treat this as a visual/DSE symptom finding. It is not combined with the musculoskeletal evidence profile or a disease score.",
                "Αντιμετώπισέ το ως οπτικό σύμπτωμα σχετιζόμενο με εργασία σε οθόνη. Δεν συνδυάζεται με το μυοσκελετικό προφίλ τεκμηρίωσης ή με βαθμολογία νόσου."
            ),
            modifiable=False,
        ))

    env_flags = []
    for key, label in [
        ("lighting_ok", tr("lighting", "φωτισμός")),
        ("noise_ok", tr("noise", "θόρυβος")),
        ("thermal_ok", tr("thermal comfort", "θερμική άνεση")),
        ("software_ok", tr("software/interface ergonomics", "εργονομία λογισμικού/διεπαφής")),
    ]:
        if ctx.get(key) is False:
            env_flags.append(label)
    if env_flags:
        findings.append(Finding(
            domain="DSE environment",
            title=tr("Work-environment factors need review", "Παράγοντες του εργασιακού περιβάλλοντος χρειάζονται έλεγχο"),
            status="attention",
            detail=tr(
                "Flagged: " + ", ".join(env_flags) + ". These belong in a complete display-screen assessment and are not converted into MSD probability points.",
                "Εντοπίστηκαν: " + ", ".join(env_flags) + ". Οι παράγοντες αυτοί ανήκουν σε μια πλήρη αξιολόγηση εργασίας με οθόνη και δεν μετατρέπονται σε πόντους πιθανότητας μυοσκελετικής πάθησης."
            ),
        ))

    chair_failed = ctx.get("chair_failed", [])
    if chair_failed:
        findings.append(Finding(
            domain="Chair fit",
            title=tr(
                f"{len(chair_failed)} chair fit/adjustability issue(s)",
                f"{len(chair_failed)} ζήτημα/ζητήματα προσαρμογής ή ρύθμισης καρέκλας"
            ),
            status="attention",
            detail=tr(
                "Chair findings are engineering/fit findings. The number of failed items is not treated as a validated clinical-priority threshold, and chair replacement alone should not be presented as a validated treatment for back pain.",
                "Τα ευρήματα της καρέκλας αφορούν σχεδιασμό και προσαρμογή. Ο αριθμός των σημείων που δεν πληρούνται δεν αντιμετωπίζεται ως επικυρωμένο κλινικό όριο προτεραιότητας και η αντικατάσταση της καρέκλας από μόνη της δεν πρέπει να παρουσιάζεται ως επικυρωμένη θεραπεία για πόνο στη μέση."
            ),
            evidence_ids=("channak_2022_chairs",),
        ))

    posture_out = ctx.get("posture_out", [])
    if posture_out:
        findings.append(Finding(
            domain="Posture & movement",
            title=tr(
                f"{len(posture_out)} posture criterion finding(s)",
                f"{len(posture_out)} εύρημα/ευρήματα κριτηρίων στάσης"
            ),
            status="attention",
            detail=tr(
                "These are posture-screening observations. v2 deliberately does not aggregate them into an overall posture percentage or disease-risk category.",
                "Πρόκειται για παρατηρήσεις εργονομικής στάσης. Η v2 σκόπιμα δεν τις συγκεντρώνει σε συνολικό ποσοστό στάσης ή σε κατηγορία κινδύνου νόσου."
            ),
            evidence_ids=("jahn_2023_lbp_posture",),
        ))

    rosa_final = int(ctx.get("rosa_final", 0))
    if rosa_final >= 5:
        findings.append(Finding(
            domain="ROSA",
            title=tr(f"ROSA action level reached ({rosa_final}/10)", f"Επιτεύχθηκε το επίπεδο δράσης ROSA ({rosa_final}/10)"),
            status="priority",
            detail=tr(
                "The original ROSA validation supports score 5 as an action level for further ergonomic investigation/intervention.",
                "Η αρχική επικύρωση του ROSA υποστηρίζει τη βαθμολογία 5 ως επίπεδο δράσης για περαιτέρω εργονομική διερεύνηση/παρέμβαση."
            ),
        ))
    elif rosa_final > 0:
        findings.append(Finding(
            domain="ROSA",
            title=tr(f"ROSA below action level ({rosa_final}/10)", f"ROSA κάτω από το επίπεδο δράσης ({rosa_final}/10)"),
            status="information",
            detail=tr(
                "Below the validated action level of 5. This is not interpreted as a clinical low-risk disease category.",
                "Η βαθμολογία είναι κάτω από το τεκμηριωμένο επίπεδο δράσης 5. Δεν ερμηνεύεται ως κλινική κατηγορία χαμηλού κινδύνου νόσου."
            ),
        ))

    # Contextual health factors: shown, never subtracted from disease risk.
    band = bmi_band(float(ctx.get("bmi", 0)))
    if band in {"overweight", "obese"}:
        evidence_id = "shiri_2015_cts_bmi_obese" if band == "obese" else "shiri_2015_cts_bmi_overweight"
        findings.append(Finding(
            domain="Health context",
            title=tr(f"BMI category: {band}", f"Κατηγορία ΔΜΣ: {band}"),
            status="information",
            detail=tr(
                "BMI can be associated with some musculoskeletal/neuropathic outcomes, but it is not an ergonomic exposure and is not converted into an ErgoFit disease score.",
                "Ο ΔΜΣ μπορεί να σχετίζεται με ορισμένες μυοσκελετικές/νευροπαθητικές εκβάσεις, αλλά δεν αποτελεί εργονομική έκθεση και δεν μετατρέπεται σε βαθμολογία νόσου του ErgoFit."
            ),
            evidence_ids=(evidence_id,),
            modifiable=False,
        ))

    if ctx.get("sleep_problem"):
        findings.append(Finding(
            domain="Health context",
            title=tr("Sleep concern", "Ζήτημα ύπνου"),
            status="information",
            detail=tr(
                "Sleep problems and chronic musculoskeletal pain are prospectively associated and bidirectional. v2 treats sleep as context, not as a numeric protective/risk credit.",
                "Τα προβλήματα ύπνου και ο χρόνιος μυοσκελετικός πόνος παρουσιάζουν προοπτική και αμφίδρομη συσχέτιση. Η v2 αντιμετωπίζει τον ύπνο ως πλαίσιο υγείας και όχι ως αριθμητική προστατευτική/επιβαρυντική πίστωση."
            ),
            evidence_ids=("runge_2024_sleep_msk",),
            modifiable=False,
        ))

    if ctx.get("job_demand") or ctx.get("low_control") or ctx.get("low_support"):
        findings.append(Finding(
            domain="Psychosocial context",
            title=tr("Psychosocial work factors flagged", "Εντοπίστηκαν ψυχοκοινωνικοί παράγοντες εργασίας"),
            status="attention",
            detail=tr(
                "Psychosocial and organisational factors can contribute to symptom development/persistence. They are kept separate from workstation geometry and disease prediction.",
                "Οι ψυχοκοινωνικοί και οργανωτικοί παράγοντες μπορούν να συμβάλλουν στην εμφάνιση ή επιμονή συμπτωμάτων. Διατηρούνται ξεχωριστά από τη γεωμετρία της θέσης εργασίας και από οποιαδήποτε πρόβλεψη νόσου."
            ),
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
