from __future__ import annotations

import html
import streamlit as st

from ergofit.models import EvidenceItem, Finding, Recommendation


STATUS_LABELS = {
    "en": {"information": "Information", "attention": "Attention", "priority": "Priority"},
    "el": {"information": "Πληροφορία", "attention": "Χρειάζεται προσοχή", "priority": "Υψηλή προτεραιότητα"},
}

RECOMMENDATION_LABELS = {
    "en": {"now": "Act now", "soon": "Next step", "maintain": "Maintain / context"},
    "el": {"now": "Άμεση ενέργεια", "soon": "Επόμενο βήμα", "maintain": "Διατήρηση / πλαίσιο"},
}

EVIDENCE_LABELS = {
    "en": {
        "population": "Population",
        "design": "Design",
        "certainty": "Certainty",
        "applicability": "Applicability to office workers",
        "why": "Why",
        "no_effect": "No pooled effect estimate",
    },
    "el": {
        "population": "Πληθυσμός",
        "design": "Σχεδιασμός μελέτης",
        "certainty": "Βεβαιότητα τεκμηρίωσης",
        "applicability": "Εφαρμοσιμότητα σε εργαζομένους γραφείου",
        "why": "Γιατί",
        "no_effect": "Δεν υπάρχει συγκεντρωτική εκτίμηση επίδρασης",
    },
}

OUTCOME_LABELS_EL = {
    "complaints_of_arm_neck_shoulder": "Ενοχλήσεις άνω άκρου / αυχένα / ώμου",
    "low_back_pain": "Πόνος στη μέση",
    "neck_shoulder_pain": "Πόνος αυχένα / ώμου",
    "incident_non_specific_neck_pain": "Νέος μη ειδικός πόνος στον αυχένα",
    "carpal_tunnel_syndrome": "Σύνδρομο καρπιαίου σωλήνα",
    "lateral_epicondylitis": "Έξω επικονδυλίτιδα",
    "chronic_low_back_pain": "Χρόνιος πόνος στη μέση",
    "specific_shoulder_disorder": "Ειδική πάθηση ώμου",
}

EVIDENCE_TITLE_EL = {
    "Computer/mouse use >4 h/day and CANS": "Χρήση υπολογιστή/ποντικιού >4 ώρες/ημέρα και ενοχλήσεις άνω άκρου–αυχένα–ώμου",
    "Self-reported workplace sitting and low-back pain": "Καθιστική εργασία και πόνος στη μέση",
    "Workplace sitting and neck/shoulder pain": "Καθιστική εργασία και πόνος αυχένα/ώμου",
    "Prolonged sitting and low-back pain": "Παρατεταμένο κάθισμα και πόνος στη μέση",
    "Prospective risk factors for non-specific neck pain in office workers": "Προοπτικοί παράγοντες που σχετίζονται με μη ειδικό πόνο αυχένα σε εργαζομένους γραφείου",
    "High repetition and clinically assessed CTS": "Υψηλή επανάληψη και κλινικά αξιολογημένο σύνδρομο καρπιαίου σωλήνα",
    "Force intensity and clinically assessed CTS": "Ένταση δύναμης και κλινικά αξιολογημένο σύνδρομο καρπιαίου σωλήνα",
    "High ACGIH Hand Activity Level and CTS": "Υψηλό επίπεδο δραστηριότητας χεριού (ACGIH HAL) και σύνδρομο καρπιαίου σωλήνα",
    "High Strain Index and CTS": "Υψηλό Strain Index και σύνδρομο καρπιαίου σωλήνα",
    "Strain Index >5.1 and lateral epicondylitis": "Strain Index >5,1 και έξω επικονδυλίτιδα",
    "Forearm rotation exposure and lateral epicondylitis": "Έκθεση σε στροφή αντιβραχίου και έξω επικονδυλίτιδα",
    "Non-neutral posture and chronic low-back pain": "Μη ουδέτερη στάση και χρόνιος πόνος στη μέση",
    "Arm elevation and specific shoulder disorders": "Ανύψωση βραχίονα και ειδικές παθήσεις ώμου",
    "Overweight and carpal tunnel syndrome": "Αυξημένο σωματικό βάρος και σύνδρομο καρπιαίου σωλήνα",
    "Obesity and carpal tunnel syndrome": "Παχυσαρκία και σύνδρομο καρπιαίου σωλήνα",
    "Arm support plus alternative mouse for neck/shoulder disorders": "Στήριξη άνω άκρου και εναλλακτικό ποντίκι για ενοχλήσεις αυχένα/ώμου",
    "Active breaks / postural change in office workers": "Ενεργά διαλείμματα και αλλαγές στάσης σε εργαζομένους γραφείου",
    "Physical activity plus ergonomics and back-pain intensity": "Φυσική δραστηριότητα μαζί με εργονομική παρέμβαση για πόνο στη μέση",
    "Workplace micro-exercise for neck/shoulder pain": "Μικρές ασκήσεις στον χώρο εργασίας για πόνο αυχένα/ώμου",
    "Sleep problems and subsequent chronic musculoskeletal pain": "Προβλήματα ύπνου και μεταγενέστερος χρόνιος μυοσκελετικός πόνος",
    "Office-chair interventions and musculoskeletal outcomes": "Παρεμβάσεις με καρέκλα γραφείου και μυοσκελετικά συμπτώματα",
}

EVIDENCE_REGION_ORDER = [
    "low_back",
    "neck_shoulder",
    "shoulder",
    "elbow",
    "wrist_hand",
    "general",
]

EVIDENCE_REGION_LABELS = {
    "el": {
        "low_back": "Μέση / οσφυϊκή περιοχή",
        "neck_shoulder": "Αυχένας και ώμοι",
        "shoulder": "Ώμος",
        "elbow": "Αγκώνας",
        "wrist_hand": "Καρπός και χέρι",
        "general": "Γενικοί παράγοντες και παρεμβάσεις",
    },
    "en": {
        "low_back": "Low back",
        "neck_shoulder": "Neck and shoulders",
        "shoulder": "Shoulder",
        "elbow": "Elbow",
        "wrist_hand": "Wrist and hand",
        "general": "General factors and interventions",
    },
}

OUTCOME_REGION = {
    "low_back_pain": "low_back",
    "chronic_low_back_pain": "low_back",
    "back_pain_intensity": "low_back",
    "low_back_pain_discomfort": "low_back",
    "complaints_of_arm_neck_shoulder": "neck_shoulder",
    "neck_shoulder_pain": "neck_shoulder",
    "incident_non_specific_neck_pain": "neck_shoulder",
    "neck_shoulder_msd_incidence": "neck_shoulder",
    "combined_neck_shoulder_pain": "neck_shoulder",
    "specific_shoulder_disorder": "shoulder",
    "lateral_epicondylitis": "elbow",
    "carpal_tunnel_syndrome": "wrist_hand",
    "musculoskeletal_pain_discomfort": "general",
    "chronic_musculoskeletal_pain": "general",
}

EVIDENCE_SIMPLE_EL = {
    "rijal_2026_cans_4h": "Σε εργαζομένους που χρησιμοποιούν συστηματικά υπολογιστή, η χρήση υπολογιστή ή ποντικιού πάνω από 4 ώρες την ημέρα συνδέθηκε με περισσότερες ενοχλήσεις σε αυχένα, ώμους και άνω άκρα. Δεν σημαίνει ότι οι 4 ώρες είναι ένα απόλυτο όριο ούτε ότι προβλέπεται συγκεκριμένη πάθηση.",
    "dzakpasu_2021_lbp_sitting": "Η καθιστική εργασία σχετίστηκε με περισσότερες αναφορές πόνου στη μέση. Η σχέση όμως βασίζεται κυρίως σε μελέτες που δείχνουν συσχέτιση και όχι ότι το κάθισμα από μόνο του προκαλεί πόνο.",
    "dzakpasu_2021_neck_shoulder_sitting": "Η καθιστική εργασία σχετίστηκε με περισσότερες ενοχλήσεις σε αυχένα και ώμους. Αυτό δεν αποδεικνύει ότι το κάθισμα είναι η μοναδική αιτία του πόνου.",
    "mahdavi_2022_lbp_sitting": "Το παρατεταμένο κάθισμα συσχετίστηκε με πόνο στη μέση, αλλά τα περισσότερα δεδομένα ήταν παρατηρητικά. Στην πράξη έχει μεγαλύτερη αξία να αξιολογούμε διάρκεια, αλλαγές στάσης και συνολική εργασία παρά ένα μοναδικό όριο ωρών.",
    "jun_2017_neck_office": "Σε εργαζομένους γραφείου, ο πόνος στον αυχένα φαίνεται να επηρεάζεται από περισσότερους από έναν παράγοντες, όπως η μικρή ποικιλία στην εργασία και η χαμηλή ικανοποίηση από την εργασία. Δεν υπάρχει ένας μόνο παράγοντας που να εξηγεί τον αυχενικό πόνο.",
    "hassan_2022_cts_repetition": "Η πραγματικά υψηλή επανάληψη κινήσεων χεριού και καρπού σε επαγγελματικές εργασίες συνδέθηκε με μεγαλύτερη εμφάνιση συνδρόμου καρπιαίου σωλήνα. Αυτό δεν πρέπει να εφαρμόζεται αυτόματα στη συνηθισμένη χρήση πληκτρολογίου ή ποντικιού.",
    "hassan_2022_cts_force": "Η έντονη μηχανική δύναμη με το χέρι ή τα δάκτυλα συνδέθηκε με μεγαλύτερη εμφάνιση συνδρόμου καρπιαίου σωλήνα. Η συνηθισμένη εργασία γραφείου συνήθως έχει πολύ μικρότερη απαίτηση δύναμης.",
    "hassan_2022_cts_hal": "Υψηλό επίπεδο επαναληπτικής δραστηριότητας του χεριού, όταν μετριέται με ACGIH HAL, συνδέθηκε με μεγαλύτερη εμφάνιση συνδρόμου καρπιαίου σωλήνα. Είναι χρήσιμο μόνο όταν η εργασία πραγματικά μοιάζει με εργασίες υψηλής επανάληψης.",
    "hassan_2022_cts_si": "Υψηλό Strain Index συνδέθηκε με μεγαλύτερη εμφάνιση συνδρόμου καρπιαίου σωλήνα σε επαγγελματικές εργασίες. Δεν είναι κατάλληλο να μετατρέπουμε απλές ώρες υπολογιστή σε Strain Index.",
    "bretschneider_2022_le_si": "Υψηλή μηχανική επιβάρυνση του άνω άκρου, όπως αποτυπώνεται από Strain Index πάνω από 5,1, συνδέθηκε με έξω επικονδυλίτιδα. Η εφαρμογή του έχει νόημα μόνο σε εργασίες για τις οποίες το Strain Index είναι κατάλληλο.",
    "bretschneider_2022_le_rotation": "Η σημαντική και παρατεταμένη στροφή του αντιβραχίου συνδέθηκε με μεγαλύτερη εμφάνιση έξω επικονδυλίτιδας. Η συσχέτιση αφορά πραγματική μηχανική έκθεση και όχι απλή χρήση υπολογιστή.",
    "jahn_2023_lbp_posture": "Η παρατεταμένη εργασία σε μη ουδέτερες στάσεις συνδέθηκε με χρόνιο πόνο στη μέση σε μικτούς επαγγελματικούς πληθυσμούς. Δεν μπορούμε να μετατρέψουμε μία μεμονωμένη γωνία σώματος σε προσωπικό κίνδυνο πόνου.",
    "shoulder_arm_elevation": "Η παρατεταμένη εργασία με το χέρι ανυψωμένο συνδέθηκε με περισσότερες ειδικές παθήσεις του ώμου, κυρίως σε χειρωνακτικές ή μικτές εργασίες. Για τυπική εργασία γραφείου η εφαρμογή είναι περιορισμένη, εκτός αν υπάρχει πραγματική ανύψωση του βραχίονα.",
    "shiri_2015_cts_bmi_overweight": "Το αυξημένο σωματικό βάρος έχει συσχετιστεί με σύνδρομο καρπιαίου σωλήνα σε γενικούς πληθυσμούς. Είναι παράγοντας υγείας και όχι εργονομική έκθεση της θέσης εργασίας.",
    "shiri_2015_cts_bmi_obese": "Η παχυσαρκία έχει συσχετιστεί ισχυρότερα με σύνδρομο καρπιαίου σωλήνα σε γενικούς πληθυσμούς. Δεν αποτελεί εργονομικό εύρημα και δεν πρέπει να μετατρέπεται σε εργονομική βαθμολογία.",
    "hoe_2018_arm_support_mouse": "Σε εργαζομένους γραφείου, ο συνδυασμός στήριξης του άνω άκρου και εναλλακτικού ποντικιού έδειξε όφελος για ορισμένα προβλήματα αυχένα και ώμου. Αυτό δεν σημαίνει ότι κάθε εργονομικό αξεσουάρ έχει το ίδιο αποτέλεσμα.",
    "waongenngarm_2018_breaks": "Τα ενεργά διαλείμματα και οι συχνές αλλαγές στάσης φαίνεται να βοηθούν στη μείωση μυοσκελετικής ενόχλησης χωρίς σαφή αρνητική επίδραση στην παραγωγικότητα. Δεν υπάρχει ένα μοναδικό «μαγικό» διάστημα διαλείμματος για όλους.",
    "eisele_2023_back_multicomponent": "Για τον πόνο στη μέση, οι πολυπαραγοντικές παρεμβάσεις που συνδυάζουν εργονομία με φυσική δραστηριότητα φαίνεται να έχουν μικρό όφελος. Η αλλαγή καρέκλας ή μιας μόνο ρύθμισης από μόνη της δεν αρκεί ως θεραπεία.",
    "yaghoubitajani_2026_microexercise": "Μικρές ασκήσεις και προοδευτική ενδυνάμωση στον χώρο εργασίας μπορούν να μειώσουν τον συνδυασμένο πόνο αυχένα και ώμων σε καθιστικούς εργαζομένους. Το αποτέλεσμα δεν είναι ίδιο για κάθε άτομο ή κάθε τύπο αυχενικού πόνου.",
    "runge_2024_sleep_msk": "Τα προβλήματα ύπνου και ο χρόνιος μυοσκελετικός πόνος φαίνεται να συνδέονται αμφίδρομα. Ο ύπνος είναι σημαντικό στοιχείο του γενικού πλαισίου υγείας, αλλά δεν αποτελεί εργονομικό σκορ.",
    "channak_2022_chairs": "Η σωστή προσαρμογή της καρέκλας είναι σημαντική για την εργονομία, όμως οι μελέτες δεν δείχνουν με βεβαιότητα ότι η αντικατάσταση της καρέκλας από μόνη της προλαμβάνει ή θεραπεύει τον πόνο στη μέση.",
}

EVIDENCE_SIMPLE_EN = {
    "rijal_2026_cans_4h": "Among regular computer users, more than 4 hours/day of computer or mouse use was associated with more neck, shoulder and upper-limb complaints. This does not make 4 hours a universal threshold or predict a specific disorder.",
    "dzakpasu_2021_lbp_sitting": "Workplace sitting was associated with more reports of low-back pain, but the evidence is mainly associative rather than proof that sitting alone causes pain.",
    "dzakpasu_2021_neck_shoulder_sitting": "Workplace sitting was associated with more neck and shoulder complaints. This does not show that sitting is the sole cause of pain.",
    "mahdavi_2022_lbp_sitting": "Prolonged sitting was associated with low-back pain, although most evidence was observational. Duration, movement variation and the whole job matter more than one fixed hour threshold.",
    "jun_2017_neck_office": "In office workers, neck pain appears to be influenced by several factors, including low task variation and low workplace satisfaction. No single factor explains all neck pain.",
    "hassan_2022_cts_repetition": "Truly high repetitive hand/wrist work was associated with more clinically assessed carpal tunnel syndrome. This should not automatically be applied to ordinary keyboard or mouse use.",
    "hassan_2022_cts_force": "Forceful hand or finger exertion was associated with more clinically assessed carpal tunnel syndrome. Typical office work usually involves much lower force.",
    "hassan_2022_cts_hal": "High hand activity measured with ACGIH HAL was associated with more carpal tunnel syndrome. It is relevant only when the task genuinely resembles high-repetition work.",
    "hassan_2022_cts_si": "A high Strain Index was associated with more carpal tunnel syndrome in occupational tasks. Generic computer hours should not be converted into a Strain Index.",
    "bretschneider_2022_le_si": "Higher upper-limb mechanical exposure measured with a Strain Index above 5.1 was associated with lateral epicondylitis. It is relevant only for tasks suited to the Strain Index.",
    "bretschneider_2022_le_rotation": "Substantial and prolonged forearm rotation was associated with more lateral epicondylitis. This refers to real mechanical exposure, not generic computer use.",
    "jahn_2023_lbp_posture": "Sustained non-neutral work postures were associated with chronic low-back pain in mixed occupational populations. A single observed body angle cannot be converted into personal pain risk.",
    "shoulder_arm_elevation": "Sustained arm elevation was associated with more specific shoulder disorders, mainly in manual or mixed work. Applicability to typical office work is limited unless genuine arm elevation exists.",
    "shiri_2015_cts_bmi_overweight": "Higher body weight has been associated with carpal tunnel syndrome in general populations. It is a health-context factor, not a workstation exposure.",
    "shiri_2015_cts_bmi_obese": "Obesity has been more strongly associated with carpal tunnel syndrome in general populations. It is not an ergonomic finding and should not be converted into an ergonomic score.",
    "hoe_2018_arm_support_mouse": "In office workers, a specific combination of arm support and an alternative mouse showed benefit for some neck/shoulder outcomes. This does not mean every ergonomic accessory has the same effect.",
    "waongenngarm_2018_breaks": "Active breaks and regular postural changes may reduce musculoskeletal discomfort without clear productivity harm. There is no single universal break interval for everyone.",
    "eisele_2023_back_multicomponent": "For low-back pain, multicomponent approaches combining ergonomics with physical activity may provide a small benefit. Changing a chair or one workstation setting alone is not a treatment.",
    "yaghoubitajani_2026_microexercise": "Short workplace exercise and progressive strengthening can reduce combined neck/shoulder pain in sedentary workers. Effects are not identical for every person or every type of neck pain.",
    "runge_2024_sleep_msk": "Sleep problems and chronic musculoskeletal pain appear to have a bidirectional association. Sleep is important health context, but it is not an ergonomic score.",
    "channak_2022_chairs": "Chair fit matters ergonomically, but evidence does not clearly show that chair replacement alone prevents or treats low-back pain.",
}

POPULATION_EL = {
    "rijal_2026_cans_4h": "Εργαζόμενοι που χρησιμοποιούν συστηματικά υπολογιστή, με παρακολούθηση τουλάχιστον 1 έτους",
    "dzakpasu_2021_lbp_sitting": "Εργαζόμενοι και γενικός ενήλικος πληθυσμός· 79 μελέτες συνολικά",
    "dzakpasu_2021_neck_shoulder_sitting": "Εργαζόμενοι και γενικός ενήλικος πληθυσμός· ανάλυση επαγγελματικής υποομάδας",
    "mahdavi_2022_lbp_sitting": "Ενήλικες· 49 παρατηρητικές μελέτες στην ανασκόπηση και 27 στη μετα-ανάλυση",
    "jun_2017_neck_office": "Εργαζόμενοι γραφείου· προοπτικές μελέτες και τυχαιοποιημένες παρεμβάσεις",
    "hassan_2022_cts_repetition": "17 επαγγελματικές κοόρτες· 1.051.707 εργαζόμενοι και 9.270 περιστατικά συνδρόμου καρπιαίου σωλήνα",
    "hassan_2022_cts_force": "Επαγγελματικές κοόρτες με κλινικά αξιολογημένο σύνδρομο καρπιαίου σωλήνα",
    "hassan_2022_cts_hal": "Επαγγελματικές κοόρτες με κλινικά αξιολογημένο σύνδρομο καρπιαίου σωλήνα",
    "hassan_2022_cts_si": "Επαγγελματικές κοόρτες με κλινικά αξιολογημένο σύνδρομο καρπιαίου σωλήνα",
    "bretschneider_2022_le_si": "5 προοπτικές μελέτες· 5.036 εργαζόμενοι και 318 κλινικά αξιολογημένα περιστατικά έξω επικονδυλίτιδας",
    "bretschneider_2022_le_rotation": "5 προοπτικές μελέτες· 5.036 εργαζόμενοι και 318 κλινικά αξιολογημένα περιστατικά έξω επικονδυλίτιδας",
    "jahn_2023_lbp_posture": "Εργαζόμενοι από μικτά επαγγέλματα· μελέτες κοόρτης και ασθενών-μαρτύρων",
    "shoulder_arm_elevation": "Ευρωπαϊκοί επαγγελματικοί πληθυσμοί, κυρίως χειρωνακτικές ή μικτές εργασίες",
    "shiri_2015_cts_bmi_overweight": "1.379.372 άτομα, κυρίως από δυτικούς/ευρωπαϊκούς γενικούς πληθυσμούς",
    "shiri_2015_cts_bmi_obese": "1.379.372 άτομα, κυρίως από δυτικούς/ευρωπαϊκούς γενικούς πληθυσμούς",
    "hoe_2018_arm_support_mouse": "15 τυχαιοποιημένες μελέτες, συνολικά 2.165 εργαζόμενοι γραφείου",
    "waongenngarm_2018_breaks": "8 τυχαιοποιημένες και 3 μη τυχαιοποιημένες μελέτες σε εργαζομένους γραφείου",
    "eisele_2023_back_multicomponent": "24 τυχαιοποιημένες/ομαδικά τυχαιοποιημένες μελέτες, 7.080 εργαζόμενοι γραφείου",
    "yaghoubitajani_2026_microexercise": "19 τυχαιοποιημένες μελέτες, 2.732 καθιστικοί εργαζόμενοι",
    "runge_2024_sleep_msk": "16 δημοσιεύσεις από 11 πληθυσμούς, 116.746 ενήλικες· όχι ειδικά εργαζόμενοι γραφείου",
    "channak_2022_chairs": "14 μελέτες, κυρίως σε καθιστική εργασία, με διαφορετικούς σχεδιασμούς",
}

STUDY_TYPE_EL = {
    "Systematic review and meta-analysis of prospective cohorts": "Συστηματική ανασκόπηση και μετα-ανάλυση προοπτικών μελετών κοόρτης",
    "Systematic review and meta-analysis": "Συστηματική ανασκόπηση και μετα-ανάλυση",
    "Systematic review of prospective office-worker evidence": "Συστηματική ανασκόπηση προοπτικών δεδομένων σε εργαζομένους γραφείου",
    "Systematic review/meta-analysis of prospective cohorts": "Συστηματική ανασκόπηση και μετα-ανάλυση προοπτικών μελετών κοόρτης",
    "Systematic review of prospective studies": "Συστηματική ανασκόπηση προοπτικών μελετών",
    "Systematic review and meta-analysis of occupational studies": "Συστηματική ανασκόπηση και μετα-ανάλυση επαγγελματικών μελετών",
    "Meta-analysis of 58 studies": "Μετα-ανάλυση 58 μελετών",
    "Cochrane review of office-worker RCTs": "Ανασκόπηση Cochrane τυχαιοποιημένων μελετών σε εργαζομένους γραφείου",
    "Systematic review of controlled office-worker trials": "Συστηματική ανασκόπηση ελεγχόμενων μελετών σε εργαζομένους γραφείου",
    "Systematic review and network meta-analysis of office-worker RCTs": "Συστηματική ανασκόπηση και δικτυωτή μετα-ανάλυση τυχαιοποιημένων μελετών σε εργαζομένους γραφείου",
    "Systematic review/meta-analysis of RCTs": "Συστηματική ανασκόπηση και μετα-ανάλυση τυχαιοποιημένων μελετών",
    "Systematic review/meta-analysis of prospective adult cohorts": "Συστηματική ανασκόπηση και μετα-ανάλυση προοπτικών μελετών ενηλίκων",
    "Systematic review": "Συστηματική ανασκόπηση",
}

TEMPORAL_EL = {
    "Prospective": "Προοπτικός σχεδιασμός",
    "Predominantly cross-sectional for this pooled estimate": "Κυρίως διατομεακά δεδομένα για αυτή την εκτίμηση",
    "Mostly cross-sectional": "Κυρίως διατομεακός σχεδιασμός",
    "Longitudinal/case-control synthesis": "Σύνθεση διαχρονικών μελετών και μελετών ασθενών-μαρτύρων",
    "Prospective/case-control": "Προοπτικές μελέτες και μελέτες ασθενών-μαρτύρων",
    "Mixed designs": "Μικτοί σχεδιασμοί",
    "Randomized intervention": "Τυχαιοποιημένη παρέμβαση",
    "Intervention": "Μελέτες παρέμβασης",
    "Mixed intervention/observational": "Μικτές μελέτες παρέμβασης και παρατήρησης",
}

CERTAINTY_EL = {
    "Moderate": "Μέτρια",
    "Low for causal inference": "Χαμηλή για συμπεράσματα αιτιότητας",
    "Mixed / factor-specific": "Μικτή· διαφέρει ανά παράγοντα",
    "High GRADE": "Υψηλή σύμφωνα με GRADE",
    "High-quality evidence": "Υψηλής ποιότητας τεκμηρίωση",
    "Moderate-quality evidence": "Μέτριας ποιότητας τεκμηρίωση",
    "Moderate GRADE": "Μέτρια σύμφωνα με GRADE",
    "Strong association; not office-specific": "Ισχυρή συσχέτιση, αλλά όχι ειδική για εργαζομένους γραφείου",
    "Moderate for selected comparison; overall evidence limitations": "Μέτρια για τη συγκεκριμένη σύγκριση, με περιορισμούς στη συνολική τεκμηρίωση",
    "Moderate for active breaks/postural change and no productivity harm": "Μέτρια για ενεργά διαλείμματα/αλλαγές στάσης και χωρίς σαφή βλάβη στην παραγωγικότητα",
    "Mostly low/very low": "Κυρίως χαμηλή ή πολύ χαμηλή",
    "Moderate GRADE for combined neck/shoulder pain": "Μέτρια σύμφωνα με GRADE για τον συνδυασμένο πόνο αυχένα/ώμου",
    "Variable by analysis": "Μεταβλητή ανά ανάλυση",
    "Very low to low GRADE": "Πολύ χαμηλή έως χαμηλή σύμφωνα με GRADE",
}

APPLICABILITY_EL = {
    "Direct for computer-worker CANS; not specific for CTS or isolated neck pain": "Άμεση για γενικές ενοχλήσεις αυχένα/ώμου/άνω άκρου σε χρήστες υπολογιστή· όχι ειδική για σύνδρομο καρπιαίου σωλήνα ή απομονωμένο αυχενικό πόνο",
    "Partially direct; occupational pooled estimate is mainly cross-sectional": "Μερικώς άμεση· η επαγγελματική εκτίμηση βασίζεται κυρίως σε διατομεακά δεδομένα",
    "Partially direct; pooled occupational association is mainly cross-sectional": "Μερικώς άμεση· η επαγγελματική συσχέτιση βασίζεται κυρίως σε διατομεακά δεδομένα",
    "Partially direct; office-worker subgroup effect was smaller": "Μερικώς άμεση· στους εργαζομένους γραφείου η συσχέτιση ήταν μικρότερη",
    "Direct": "Άμεση",
    "Indirect for ordinary desk work unless true high-repetition exposure is present": "Έμμεση για συνήθη εργασία γραφείου, εκτός αν υπάρχει πραγματικά υψηλή επανάληψη",
    "Indirect for ordinary desk work; relevant only if meaningful force exposure exists": "Έμμεση για συνήθη εργασία γραφείου· σχετική μόνο όταν υπάρχει ουσιαστική απαίτηση δύναμης",
    "Indirect unless task exposure matches high HAL": "Έμμεση, εκτός αν η εργασία αντιστοιχεί σε υψηλό Hand Activity Level",
    "Indirect unless task is appropriate for Strain Index assessment": "Έμμεση, εκτός αν η εργασία είναι κατάλληλη για αξιολόγηση με Strain Index",
    "Indirect unless task exposure is appropriate for Strain Index": "Έμμεση, εκτός αν η έκθεση είναι κατάλληλη για αξιολόγηση με Strain Index",
    "Indirect; only if substantial forearm-rotation exposure is actually present": "Έμμεση· σχετική μόνο αν υπάρχει πραγματικά σημαντική έκθεση σε στροφή αντιβραχίου",
    "Indirect; mostly not office-specific": "Έμμεση· οι περισσότερες μελέτες δεν αφορούν ειδικά εργασία γραφείου",
    "Indirect for typical office work": "Έμμεση για την τυπική εργασία γραφείου",
    "Indirect/general susceptibility factor": "Έμμεση· αφορά γενικό παράγοντα ευαισθησίας και όχι τη θέση εργασίας",
    "High; sedentary-worker population, though not exclusively office workers": "Υψηλή· αφορά καθιστικούς εργαζομένους, όχι αποκλειστικά εργαζομένους γραφείου",
    "Indirect contextual/prognostic evidence": "Έμμεση· αφορά γενικό πλαίσιο υγείας/πρόγνωσης",
    "Direct/mostly seated-work context": "Άμεση ή κυρίως σχετική με καθιστική εργασία",
}

NOTES_EL = {
    "rijal_2026_cans_4h": "Χρησιμοποιείται ως γενικός δείκτης έκθεσης για αυχένα και άνω άκρο, όχι ως συντελεστής πρόβλεψης συνδρόμου καρπιαίου σωλήνα.",
    "dzakpasu_2021_lbp_sitting": "Η συγκεντρωτική εκτίμηση δεν τεκμηριώνει ένα καθολικό αιτιώδες όριο ≥6 ωρών καθιστικής εργασίας.",
    "dzakpasu_2021_neck_shoulder_sitting": "Πρόκειται για συσχέτιση και όχι για προσωπική πρόβλεψη νόσου.",
    "mahdavi_2022_lbp_sitting": "Η καθιστική έκθεση χρησιμοποιείται ως τροποποιήσιμο πλαίσιο και όχι ως επικυρωμένο όριο νόσου.",
    "jun_2017_neck_office": "Αναφέρθηκαν συσχετίσεις με χαμηλή ικανοποίηση από την εργασία, μικρή ποικιλία εργασιών και ορισμένες θέσεις πληκτρολογίου, ενώ για πολλούς άλλους παράγοντες τα αποτελέσματα ήταν περιορισμένα ή αντικρουόμενα.",
    "hassan_2022_cts_repetition": "Χρειάζεται πραγματική εκτίμηση της μηχανικής έκθεσης και όχι αντικατάστασή της από τις ώρες χρήσης υπολογιστή.",
    "hassan_2022_cts_force": "Η ετερογένεια της συγκεκριμένης ανάλυσης ήταν πολύ χαμηλή.",
    "hassan_2022_cts_hal": "Η ετερογένεια της συγκεκριμένης ανάλυσης ήταν πολύ χαμηλή.",
    "hassan_2022_cts_si": "Η ετερογένεια της συγκεκριμένης ανάλυσης ήταν χαμηλή.",
    "bretschneider_2022_le_si": "Είναι πιο κατάλληλο να αξιολογείται η πραγματική μηχανική έκθεση παρά να χρησιμοποιούνται απλώς οι ώρες ποντικιού ως δείκτης.",
    "bretschneider_2022_le_rotation": "Η ανασκόπηση περιέγραψε σημαντική έκθεση, όπως πολλές ώρες στροφής αντιβραχίου ή μεγάλες γωνίες για σημαντικό μέρος του χρόνου εργασίας.",
    "jahn_2023_lbp_posture": "Δεν πρέπει να μετατρέπεται μία μεμονωμένη παρατηρούμενη γωνία σώματος στον συγκεκριμένο δείκτη συσχέτισης.",
    "shoulder_arm_elevation": "Χρησιμοποιείται μόνο όταν υπάρχει πραγματική έκθεση σε ανύψωση του βραχίονα.",
    "shiri_2015_cts_bmi_overweight": "Πρόκειται για παράγοντα γενικής ευαισθησίας και όχι για εργονομική έκθεση.",
    "shiri_2015_cts_bmi_obese": "Πρόκειται για παράγοντα γενικής ευαισθησίας και όχι για εργονομική έκθεση.",
    "hoe_2018_arm_support_mouse": "Το αποτέλεσμα αφορά συγκεκριμένο συνδυασμό παρέμβασης και δεν γενικεύεται σε κάθε εργονομικό εξοπλισμό.",
    "waongenngarm_2018_breaks": "Τα δεδομένα δεν καθορίζουν ένα μοναδικό ιδανικό διάστημα διαλείμματος για όλους.",
    "eisele_2023_back_multicomponent": "Υποστηρίζει μικρό όφελος από πολυπαραγοντικές προσεγγίσεις· πολλές επιμέρους συγκρίσεις έδειξαν μικρό ή μη σαφές αποτέλεσμα.",
    "yaghoubitajani_2026_microexercise": "Για τον απομονωμένο αυχενικό πόνο υπήρχε μεγάλη διακύμανση μεταξύ των μελετών.",
    "runge_2024_sleep_msk": "Η σχέση φαίνεται αμφίδρομη και δεν επικυρώνει αριθμητική «προστατευτική» βαθμολογία για συγκεκριμένες ώρες ύπνου.",
    "channak_2022_chairs": "Η σωστή προσαρμογή της καρέκλας παραμένει εργονομικός στόχος, αλλά η αντικατάσταση καρέκλας από μόνη της δεν αποτελεί τεκμηριωμένη θεραπεία πόνου.",
}

def group_evidence_by_region(items: list[EvidenceItem], lang: str = "en") -> list[tuple[str, list[EvidenceItem]]]:
    grouped: dict[str, list[EvidenceItem]] = {key: [] for key in EVIDENCE_REGION_ORDER}
    for item in items:
        group = OUTCOME_REGION.get(item.outcome, "general")
        grouped.setdefault(group, []).append(item)

    labels = EVIDENCE_REGION_LABELS.get(lang, EVIDENCE_REGION_LABELS["en"])
    result: list[tuple[str, list[EvidenceItem]]] = []
    for key in EVIDENCE_REGION_ORDER:
        values = grouped.get(key, [])
        if values:
            values = sorted(values, key=lambda x: x.year, reverse=True)
            result.append((labels[key], values))
    return result


def _technical_effect(e: EvidenceItem, lang: str) -> str:
    if e.estimate is None:
        return "Δεν δίνεται ένας ενιαίος συγκεντρωτικός αριθμός." if lang == "el" else "No single pooled numerical estimate was reported."

    if lang == "el":
        measure = {
            "RR": "Σχετικός κίνδυνος (RR)",
            "OR": "Λόγος πιθανοτήτων (OR)",
            "HR": "Λόγος κινδύνων (HR)",
            "SMD": "Τυποποιημένη μέση διαφορά (SMD)",
            "Hedges g": "Hedges g",
        }.get(e.effect_measure, e.effect_measure)
        estimate = f"{e.estimate:.2f}".replace(".", ",")
        value = f"{measure}: {estimate}"
        if e.ci_low is not None and e.ci_high is not None:
            low = f"{e.ci_low:.2f}".replace(".", ",")
            high = f"{e.ci_high:.2f}".replace(".", ",")
            value += f" · 95% διάστημα εμπιστοσύνης: {low}–{high}"
        return value

    value = f"{e.effect_measure} {e.estimate:.2f}"
    if e.ci_low is not None and e.ci_high is not None:
        value += f" (95% CI {e.ci_low:.2f}–{e.ci_high:.2f})"
    return value



def finding_card(f: Finding, lang: str = "en") -> None:
    cls = {"information": "ef-info", "attention": "ef-attention", "priority": "ef-priority"}.get(f.status, "ef-info")
    labels = STATUS_LABELS.get(lang, STATUS_LABELS["en"])
    st.markdown(
        f"""<div class="ef-card"><span class="ef-pill {cls}">{labels.get(f.status, f.status)}</span>
        <h4>{html.escape(f.title)}</h4><div>{html.escape(f.detail)}</div></div>""",
        unsafe_allow_html=True,
    )


def evidence_card(e: EvidenceItem, lang: str = "en") -> None:
    labels = EVIDENCE_LABELS.get(lang, EVIDENCE_LABELS["en"])
    title = e.title if lang == "en" else EVIDENCE_TITLE_EL.get(e.title, e.title)
    simple = (EVIDENCE_SIMPLE_EN if lang == "en" else EVIDENCE_SIMPLE_EL).get(
        e.id,
        "This study is relevant to the selected exposure and outcome."
        if lang == "en"
        else "Η συγκεκριμένη μελέτη είναι σχετική με την έκθεση και την περιοχή που αξιολογείται.",
    )

    st.markdown(
        f"""
        <div class="ef-card">
          <div class="ef-kicker">{"WHAT THE RESEARCH SAYS" if lang == "en" else "ΤΙ ΔΕΙΧΝΕΙ Η ΕΡΕΥΝΑ"}</div>
          <h4>{html.escape(title)}</h4>
          <div style="font-size:1.02rem;line-height:1.58;margin-top:8px">{html.escape(simple)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Technical study details" if lang == "en" else "Τεχνικές λεπτομέρειες της μελέτης", expanded=False):
        if lang == "el":
            population = POPULATION_EL.get(e.id, e.population)
            study_type = STUDY_TYPE_EL.get(e.study_type, e.study_type)
            temporal = TEMPORAL_EL.get(e.temporal_design, e.temporal_design)
            certainty = CERTAINTY_EL.get(e.certainty, e.certainty)
            applicability = APPLICABILITY_EL.get(e.office_applicability, e.office_applicability)
            notes = NOTES_EL.get(e.id, e.notes)

            st.markdown(f"**Στατιστικό αποτέλεσμα:** {_technical_effect(e, lang)}")
            st.caption("Ο αριθμός περιγράφει το αποτέλεσμα σε ομάδες ανθρώπων και δεν αποτελεί προσωπικό ποσοστό κινδύνου για τον συγκεκριμένο εργαζόμενο.")
            st.markdown(f"**Πληθυσμός μελέτης:** {population}")
            st.markdown(f"**Τύπος μελέτης:** {study_type}")
            st.markdown(f"**Χρονικός σχεδιασμός:** {temporal}")
            st.markdown(f"**Βεβαιότητα τεκμηρίωσης:** {certainty}")
            st.markdown(f"**Πόσο εφαρμόζεται σε εργαζομένους γραφείου:** {applicability}")
            if notes:
                st.markdown(f"**Σημαντική διευκρίνιση:** {notes}")
            st.markdown(f"**Πηγή:** [{e.source_label}]({e.source_url})")
        else:
            st.markdown(f"**Statistical result:** {_technical_effect(e, lang)}")
            st.caption("This is a group-level research estimate, not an individual probability for this worker.")
            st.markdown(f"**Population:** {e.population}")
            st.markdown(f"**Study design:** {e.study_type}")
            st.markdown(f"**Temporal design:** {e.temporal_design}")
            st.markdown(f"**Certainty:** {e.certainty}")
            st.markdown(f"**Applicability to office workers:** {e.office_applicability}")
            if e.notes:
                st.markdown(f"**Important note:** {e.notes}")
            st.markdown(f"**Source:** [{e.source_label}]({e.source_url})")


def recommendation_card(r: Recommendation, lang: str = "en") -> None:
    cls = "ef-priority" if r.priority == "now" else ("ef-attention" if r.priority == "soon" else "ef-info")
    labels = RECOMMENDATION_LABELS.get(lang, RECOMMENDATION_LABELS["en"])
    ev_labels = EVIDENCE_LABELS.get(lang, EVIDENCE_LABELS["en"])
    label = labels.get(r.priority, r.priority)
    st.markdown(
        f"""
        <div class="ef-card"><span class="ef-pill {cls}">{label}</span>
          <h4>{html.escape(r.title)}</h4>
          <div>{html.escape(r.action)}</div>
          <div style="margin-top:8px;color:#5b6475"><b>{ev_labels["why"]}:</b> {html.escape(r.rationale)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
