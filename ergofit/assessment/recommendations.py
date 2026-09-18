from __future__ import annotations

from ergofit.models import Finding, Recommendation


def build_recommendations(ctx: dict, findings: list[Finding], lang: str = "en") -> list[Recommendation]:
    recs: list[Recommendation] = []
    tr = lambda en, el: en if lang == "en" else el
    titles = {f.title for f in findings}
    regions = set(ctx.get("symptom_regions", []))

    if int(ctx.get("rosa_final", 0)) >= 5:
        recs.append(Recommendation(
            priority="now",
            title=tr("Act on the ROSA drivers", "Παρέμβαση στους παράγοντες που αυξάνουν το ROSA"),
            action=tr(
                "Review the specific chair, monitor, phone, mouse and keyboard ROSA sub-items that generated the score and correct the highest-exposure items first.",
                "Έλεγξε τα επιμέρους στοιχεία ROSA για καρέκλα, οθόνη, τηλέφωνο, ποντίκι και πληκτρολόγιο που διαμόρφωσαν τη βαθμολογία και διόρθωσε πρώτα όσα έχουν τη μεγαλύτερη επιβάρυνση."
            ),
            rationale=tr(
                "ROSA ≥5 reaches the validated action level for further ergonomic investigation/intervention.",
                "ROSA ≥5 αντιστοιχεί στο τεκμηριωμένο επίπεδο δράσης για περαιτέρω εργονομική διερεύνηση/παρέμβαση."
            ),
        ))

    if any(
        "Seat height differs" in t
        or "Work-surface height differs" in t
        or "Monitor" in t
        or "ύψος της έδρας" in t
        or "επιφάνειας εργασίας" in t
        or "οθόνης" in t
        for t in titles
    ):
        recs.append(Recommendation(
            priority="now",
            title=tr("Correct workstation fit before adding accessories", "Διόρθωσε πρώτα την προσαρμογή της θέσης εργασίας"),
            action=tr(
                "Adjust seat height, work-surface relationship and monitor placement using direct body measurements and observed posture. Re-check after adjustment.",
                "Ρύθμισε το ύψος της έδρας, τη σχέση με την επιφάνεια εργασίας και τη θέση της οθόνης χρησιμοποιώντας άμεσες σωματομετρικές μετρήσεις και παρατήρηση της στάσης. Επανέλεγξε μετά τη ρύθμιση."
            ),
            rationale=tr(
                "Workstation fit is an engineering exposure-control step. The app does not claim a specific disease-risk reduction from a centimetre change.",
                "Η σωστή προσαρμογή της θέσης εργασίας αποτελεί μέτρο ελέγχου της έκθεσης. Το εργαλείο δεν ισχυρίζεται συγκεκριμένη μείωση κινδύνου νόσου από μια αλλαγή λίγων εκατοστών."
            ),
        ))

    if ctx.get("glare") or ctx.get("digital_eye_strain"):
        recs.append(Recommendation(
            priority="now",
            title=tr("Review the visual workstation", "Έλεγξε το οπτικό περιβάλλον εργασίας"),
            action=tr(
                "Reduce glare/reflections, confirm viewing distance and display position, and follow the organisation's eyesight/occupational-health pathway if visual symptoms persist.",
                "Μείωσε τη θάμβωση και τις αντανακλάσεις, επιβεβαίωσε την απόσταση θέασης και τη θέση της οθόνης και, αν τα οπτικά συμπτώματα επιμένουν, ακολούθησε τη διαδικασία οφθαλμολογικού/ιατρικού ελέγχου του οργανισμού."
            ),
            rationale=tr(
                "A complete display-screen assessment includes visual symptoms and the visual environment, not only musculoskeletal geometry.",
                "Μια ολοκληρωμένη αξιολόγηση εργασίας με οθόνη περιλαμβάνει τα οπτικά συμπτώματα και το οπτικό περιβάλλον και όχι μόνο τη μυοσκελετική γεωμετρία."
            ),
        ))

    if any(ctx.get(k) is False for k in ("lighting_ok", "noise_ok", "thermal_ok", "software_ok")):
        recs.append(Recommendation(
            priority="soon",
            title=tr("Correct flagged DSE environment factors", "Διόρθωσε τους παράγοντες του περιβάλλοντος εργασίας με οθόνη"),
            action=tr(
                "Address lighting, noise, thermal comfort and/or software-interface issues that were marked unsuitable for the task.",
                "Αντιμετώπισε τα ζητήματα φωτισμού, θορύβου, θερμικής άνεσης και/ή λογισμικού/διεπαφής που σημειώθηκαν ως ακατάλληλα για την εργασία."
            ),
            rationale=tr(
                "The display-screen workstation includes the immediate work environment and software, so these should be controlled as separate ergonomic domains.",
                "Η θέση εργασίας με οθόνη περιλαμβάνει το άμεσο εργασιακό περιβάλλον και το λογισμικό, επομένως αυτά πρέπει να ελέγχονται ως ξεχωριστοί εργονομικοί τομείς."
            ),
        ))

    if float(ctx.get("sitting_hours", 0)) >= 6 or ctx.get("active_breaks") is False or ctx.get("long_sitting_bout") in {"60–120 min", ">120 min"}:
        recs.append(Recommendation(
            priority="soon",
            title=tr("Increase movement and postural variation", "Αύξησε την κίνηση και την εναλλαγή στάσης"),
            action=tr(
                "Use short active breaks and regular position changes that fit the workflow. Avoid presenting one fixed interval as a universal medical threshold.",
                "Χρησιμοποίησε σύντομα ενεργά διαλείμματα και τακτικές αλλαγές θέσης που ταιριάζουν στη ροή εργασίας. Απόφυγε να παρουσιάζεις ένα συγκεκριμένο διάστημα ως καθολικό ιατρικό όριο."
            ),
            rationale=tr(
                "Office intervention evidence is more supportive of active breaks/postural change than of a single prescribed break schedule.",
                "Η τεκμηρίωση παρεμβάσεων σε εργαζομένους γραφείου υποστηρίζει περισσότερο τα ενεργά διαλείμματα και τις αλλαγές στάσης παρά ένα ενιαίο προκαθορισμένο πρόγραμμα διαλειμμάτων."
            ),
            evidence_ids=("waongenngarm_2018_breaks",),
        ))

    neck_terms = {"Neck", "Shoulder(s)", "Αυχένας", "Ώμος/ώμοι"}
    if regions & neck_terms:
        recs.append(Recommendation(
            priority="soon",
            title=tr("Consider targeted neck/shoulder exercise", "Εξέτασε στοχευμένη άσκηση αυχένα/ώμων"),
            action=tr(
                "Where clinically appropriate, use progressive neck/shoulder/scapular strengthening or workplace micro-exercise rather than treating exercise as a numeric 'protective credit'.",
                "Όπου είναι κλινικά κατάλληλο, χρησιμοποίησε προοδευτική ενδυνάμωση αυχένα/ώμων/ωμοπλάτης ή μικρές ασκήσεις στον χώρο εργασίας, αντί να αντιμετωπίζεται η άσκηση ως αριθμητική «προστατευτική πίστωση»."
            ),
            rationale=tr(
                "Recent RCT meta-analysis in sedentary workers supports improvement in combined neck/shoulder pain and neck disability, with moderate certainty for selected outcomes.",
                "Πρόσφατη μετα-ανάλυση τυχαιοποιημένων μελετών σε καθιστικούς εργαζομένους υποστηρίζει βελτίωση στον συνδυασμένο πόνο αυχένα/ώμου και στη λειτουργική επιβάρυνση του αυχένα, με μέτρια βεβαιότητα για ορισμένες εκβάσεις."
            ),
            evidence_ids=("yaghoubitajani_2026_microexercise",),
        ))

    back_terms = {"Low back", "Οσφύς / μέση"}
    if regions & back_terms:
        recs.append(Recommendation(
            priority="soon",
            title=tr("Use a multicomponent low-back strategy", "Χρησιμοποίησε πολυπαραγοντική στρατηγική για τη μέση"),
            action=tr(
                "Combine workstation correction with appropriate physical activity/exercise and movement variation; do not rely on chair replacement alone.",
                "Συνδύασε τη διόρθωση της θέσης εργασίας με κατάλληλη φυσική δραστηριότητα/άσκηση και εναλλαγή στάσης. Μην βασίζεσαι μόνο στην αντικατάσταση της καρέκλας."
            ),
            rationale=tr(
                "Office-worker network meta-analysis suggests only modest/uncertain benefits across many interventions, with some support for physical activity plus ergonomics.",
                "Δικτυωτή μετα-ανάλυση σε εργαζομένους γραφείου δείχνει μικρά ή αβέβαια οφέλη για πολλές παρεμβάσεις, με κάποια υποστήριξη για τον συνδυασμό φυσικής δραστηριότητας και εργονομίας."
            ),
            evidence_ids=("eisele_2023_back_multicomponent", "channak_2022_chairs"),
        ))

    upper_terms = {"Elbow / forearm / wrist / hand", "Αγκώνας / αντιβράχιο / καρπός / χέρι"}
    if regions & upper_terms and float(ctx.get("mouse_hours", 0)) > 4:
        recs.append(Recommendation(
            priority="soon",
            title=tr("Review mouse reach and forearm support", "Έλεγξε την απόσταση του ποντικιού και τη στήριξη αντιβραχίων"),
            action=tr(
                "Keep the mouse close, minimise unnecessary reach, and consider a suitable forearm-support/alternative-mouse combination when symptoms and task demands justify it.",
                "Κράτησε το ποντίκι κοντά στο σώμα, περιόρισε το περιττό τέντωμα του χεριού και εξέτασε κατάλληλο συνδυασμό στήριξης αντιβραχίου/εναλλακτικού ποντικιού όταν το δικαιολογούν τα συμπτώματα και οι απαιτήσεις της εργασίας."
            ),
            rationale=tr(
                "Cochrane office-worker evidence supports a specific arm-support + alternative-mouse combination for some neck/shoulder outcomes; evidence does not support generic equipment claims.",
                "Η τεκμηρίωση Cochrane σε εργαζομένους γραφείου υποστηρίζει συγκεκριμένο συνδυασμό στήριξης άνω άκρου και εναλλακτικού ποντικιού για ορισμένες εκβάσεις αυχένα/ώμου· δεν υποστηρίζει γενικούς ισχυρισμούς για οποιονδήποτε εξοπλισμό."
            ),
            evidence_ids=("hoe_2018_arm_support_mouse",),
        ))

    if ctx.get("high_repetition") or ctx.get("hand_force"):
        recs.append(Recommendation(
            priority="now",
            title=tr("Quantify upper-limb mechanical exposure", "Ποσοτικοποίησε τη μηχανική έκθεση του άνω άκρου"),
            action=tr(
                "If the job truly involves high repetition or force, use a task-appropriate method such as ACGIH HAL or Strain Index and redesign the task rather than using computer-hours as a proxy.",
                "Αν η εργασία περιλαμβάνει πραγματικά υψηλή επανάληψη ή δύναμη, χρησιμοποίησε κατάλληλη μέθοδο όπως ACGIH HAL ή Strain Index και επανασχεδίασε την εργασία αντί να χρησιμοποιείς τις ώρες υπολογιστή ως υποκατάστατο."
            ),
            rationale=tr(
                "Prospective CTS evidence is strongest for repetition, force, HAL and Strain Index.",
                "Τα ισχυρότερα προοπτικά δεδομένα για σύνδρομο καρπιαίου σωλήνα αφορούν την επανάληψη, τη δύναμη, το HAL και το Strain Index."
            ),
            evidence_ids=("hassan_2022_cts_repetition", "hassan_2022_cts_force", "hassan_2022_cts_hal", "hassan_2022_cts_si"),
        ))

    if ctx.get("forearm_rotation"):
        recs.append(Recommendation(
            priority="now",
            title=tr("Reduce sustained forearm rotation", "Μείωσε την παρατεταμένη στροφή του αντιβραχίου"),
            action=tr(
                "Modify task orientation, tool/device position or work sequence so the forearm can remain closer to neutral and rotate less often/less intensely.",
                "Τροποποίησε τον προσανατολισμό της εργασίας, τη θέση εργαλείων/συσκευών ή τη σειρά των ενεργειών ώστε το αντιβράχιο να παραμένει πιο κοντά στην ουδέτερη θέση και να περιστρέφεται λιγότερο συχνά ή λιγότερο έντονα."
            ),
            rationale=tr(
                "Prospective evidence supports forearm rotation and higher Strain Index as lateral-epicondylitis exposures in relevant occupational tasks.",
                "Προοπτικά δεδομένα υποστηρίζουν τη στροφή αντιβραχίου και υψηλότερο Strain Index ως εκθέσεις που σχετίζονται με έξω επικονδυλίτιδα σε κατάλληλες επαγγελματικές εργασίες."
            ),
            evidence_ids=("bretschneider_2022_le_rotation", "bretschneider_2022_le_si"),
        ))

    if ctx.get("arm_elevation"):
        recs.append(Recommendation(
            priority="now",
            title=tr("Reduce sustained arm elevation", "Μείωσε την παρατεταμένη ανύψωση του βραχίονα"),
            action=tr(
                "Bring frequently used items into a lower, closer reach zone and reduce sustained shoulder elevation/loading.",
                "Μετέφερε τα συχνά χρησιμοποιούμενα αντικείμενα σε χαμηλότερη και κοντινότερη ζώνη προσέγγισης και μείωσε την παρατεταμένη ανύψωση/φόρτιση του ώμου."
            ),
            rationale=tr(
                "Evidence for specific shoulder disorders comes mainly from manual/mixed occupations, so intervention is justified by the actual exposure, not by an office-worker disease score.",
                "Η τεκμηρίωση για συγκεκριμένες παθήσεις ώμου προέρχεται κυρίως από χειρωνακτικά/μικτά επαγγέλματα. Η παρέμβαση δικαιολογείται από την πραγματική έκθεση και όχι από βαθμολογία νόσου για εργαζόμενο γραφείου."
            ),
            evidence_ids=("shoulder_arm_elevation",),
        ))

    if ctx.get("chair_failed"):
        recs.append(Recommendation(
            priority="soon",
            title=tr("Optimise chair fit and adjustability", "Βελτιστοποίησε την προσαρμογή και τις ρυθμίσεις της καρέκλας"),
            action=tr(
                "Correct the failed fit/adjustability items and trial the chair during real work. Replace the chair only when fit/adjustment cannot be achieved.",
                "Διόρθωσε τα σημεία προσαρμογής/ρύθμισης που δεν πληρούνται και δοκίμασε την καρέκλα κατά την πραγματική εργασία. Αντικατάστησέ την μόνο όταν δεν μπορεί να επιτευχθεί κατάλληλη προσαρμογή."
            ),
            rationale=tr(
                "Chair-specific intervention evidence for pain prevention is very low/low and conflicting; fit remains a valid engineering objective.",
                "Η τεκμηρίωση για παρεμβάσεις αποκλειστικά με καρέκλα στην πρόληψη πόνου είναι χαμηλής/πολύ χαμηλής βεβαιότητας και αντικρουόμενη· η σωστή προσαρμογή παραμένει έγκυρος εργονομικός στόχος."
            ),
            evidence_ids=("channak_2022_chairs",),
        ))

    if ctx.get("sleep_problem"):
        recs.append(Recommendation(
            priority="maintain",
            title=tr("Treat sleep as a health-context issue", "Αντιμετώπισε τον ύπνο ως παράγοντα του γενικού πλαισίου υγείας"),
            action=tr(
                "If sleep problems are persistent or significant, encourage appropriate sleep-health assessment/support. Do not subtract or add disease-risk points based on sleep duration alone.",
                "Αν τα προβλήματα ύπνου είναι επίμονα ή σημαντικά, πρότεινε κατάλληλη αξιολόγηση/υποστήριξη για τον ύπνο. Μην αφαιρείς ή προσθέτεις πόντους κινδύνου νόσου μόνο με βάση τη διάρκεια ύπνου."
            ),
            rationale=tr(
                "Prospective evidence shows a bidirectional association between sleep problems and chronic musculoskeletal pain, but it is not office-specific and does not validate a numeric ErgoFit coefficient.",
                "Προοπτικά δεδομένα δείχνουν αμφίδρομη συσχέτιση μεταξύ προβλημάτων ύπνου και χρόνιου μυοσκελετικού πόνου, αλλά δεν είναι ειδικά για εργαζομένους γραφείου και δεν επικυρώνουν αριθμητικό συντελεστή του ErgoFit."
            ),
            evidence_ids=("runge_2024_sleep_msk",),
        ))

    if not recs:
        recs.append(Recommendation(
            priority="maintain",
            title=tr("Maintain a well-fitted, variable workstation routine", "Διατήρησε σωστή προσαρμογή και εναλλαγή στάσης"),
            action=tr(
                "Continue using the workstation with regular position changes and re-assess if symptoms or task demands change.",
                "Συνέχισε να χρησιμοποιείς τη θέση εργασίας με τακτικές αλλαγές θέσης και επανεκτίμησε αν αλλάξουν τα συμπτώματα ή οι απαιτήσεις της εργασίας."
            ),
            rationale=tr(
                "No priority ergonomic exposure was identified in this screen.",
                "Δεν εντοπίστηκε εργονομική έκθεση υψηλής προτεραιότητας σε αυτή την αξιολόγηση."
            ),
        ))

    return recs
