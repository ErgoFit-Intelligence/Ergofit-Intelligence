"""
Ergonomic Assessment Tool — Professional version.

Internal note: data combines ANSUR I anthropometry, OSHA/ILO equipment specs,
joint comfort angles, BMI biomechanical multipliers, and population prevalence
data for work-related musculoskeletal disorders. Sources are not surfaced in
the UI.

To enable the background logo, drop a file named  logo.png  (or .jpg / .jpeg / .svg)
into the same folder as this script.
"""

import base64
import json
from datetime import date, datetime
from pathlib import Path

import requests
import streamlit as st


# ====================================================================
# Backend (Google Sheets via Apps Script webhook)
# ====================================================================
WEBHOOK_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbyuPAK8E8fNt2OwetJixOVm_h8fCO6zMX7Mz3lp5Wepp1YTaDw0vMqw6u3Y636-NG1owA/exec"
)

def submit_to_backend(payload: dict) -> tuple[bool, str]:
    """POST an assessment payload to the Google Apps Script webhook.

    Sends the body as text/plain to avoid the Apps Script CORS/preflight
    quirk that returns Google's login HTML for application/json POSTs.
    Apps Script reads the raw body from e.postData.contents regardless
    of Content-Type.
    """
    try:
        r = requests.post(
            WEBHOOK_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "text/plain;charset=utf-8"},
            timeout=30,
            allow_redirects=True,
        )
        try:
            data = r.json()
        except Exception:
            snippet = r.text[:250].replace("\n", " ")
            return False, f"Non-JSON response ({r.status_code}): {snippet}"
        if data.get("success"):
            return True, f"Row #{data.get('row', '?')} added."
        return False, str(data.get("error", "Unknown error"))
    except requests.exceptions.RequestException as e:
        return False, f"Network error: {e}"


# ====================================================================
# Internationalisation (EL / EN)
# ====================================================================
# All user-visible strings live here in plain, everyday language —
# no jargon, no academic framing. Both languages should be equally
# readable by a non-specialist (an employee, not just an ergonomist).
I18N = {
    "el": {
        # ---- Language selector label ----
        "lang_label":  "🌐 Γλώσσα / Language",

        # ---- Hero ----
        "hero_brand":  "ERGOFIT · INTELLIGENCE",
        "hero_title":  "Εργαλείο εργονομικής αξιολόγησης",
        "hero_sub":    "Το εργαλείο που σας βοηθά να δουλεύετε χωρίς πόνο.",

        # ---- Intended purpose expander ----
        "ip_expander": "ℹ️ Σε τι χρησιμεύει αυτό το εργαλείο · Προστασία δεδομένων",
        "ip_body": """
**Σε τι χρησιμεύει.** Το ErgoFit βοηθά τον εργονόμο να αξιολογήσει τη θέση εργασίας ενός εργαζομένου. Εντοπίζει τι δεν πάει καλά (καρέκλα, γραφείο, οθόνη, στάση σώματος) και δείχνει ποιοι παράγοντες κινδύνου υπάρχουν για μυοσκελετικά προβλήματα.

**Τι δεν είναι.**

- Δεν είναι **ιατρικό μηχάνημα** — δεν κάνει διάγνωση.
- Δεν είναι **προγνωστικό εργαλείο** — δεν σας λέει την πιθανότητα να πάθετε κάτι.
- Δεν αντικαθιστά **εξέταση από γιατρό**.

**Πάνω σε τι βασίζεται.** Ευρωπαϊκά πρότυπα για καρέκλες γραφείου (EN 1335-1:2020), σχεδιασμό θέσης εργασίας (ISO 9241-5:2024), και την Ευρωπαϊκή Οδηγία 90/270/ΕΟΚ για οθόνες. Οι εκτιμήσεις σωματομετρικών διαστάσεων προέρχονται από ανθρωπομετρικά δεδομένα (Panero & Zelnik, NASA STD-3000), αλλά υπερισχύουν οι **άμεσες** μετρήσεις όταν καταχωρηθούν.

**Προστασία δεδομένων.** Το εργαλείο συλλέγει και δεδομένα υγείας (τραυματισμοί, διαβήτης κ.λπ.). Πριν στείλετε οτιδήποτε, πρέπει να πάρετε ρητή συγκατάθεση από τον εργαζόμενο. Τα δεδομένα διαγράφονται όποτε τα ζητήσετε.
""",

        # ---- Subject profile block ----
        "sp_head":         "Στοιχεία του εργαζομένου",
        "sp_identity":     "Ταυτότητα",
        "sp_demographics": "Δημογραφικά",
        "sp_occup":        "Επαγγελματική έκθεση",
        "sp_health":       "Υγεία & τρόπος ζωής",
        "sp_injuries":     "Προηγούμενοι τραυματισμοί (ανά περιοχή σώματος)",
        "sp_injuries_hint":"Επιλέξτε κάθε περιοχή όπου υπάρχει προηγούμενος τραυματισμός, διάστρεμμα ή χρόνιος πόνος. Ο κίνδυνος επανεμφάνισης είναι υψηλότερος στη συγκεκριμένη περιοχή.",
        "sp_female":       "Ειδικά για γυναίκες",
        "sp_female_hint":  "Τα πεδία απενεργοποιούνται αυτόματα για άντρες.",
        "sp_anthro":       "Άμεσες μετρήσεις σώματος (προαιρετικά)",
        "sp_anthro_hint":  "Οι πραγματικές μετρήσεις είναι πιο ακριβείς από τις εκτιμήσεις με βάση το ύψος. Αφήστε 0 για να χρησιμοποιηθεί η εκτίμηση.",
        "sp_psy":          "Ψυχοκοινωνικοί παράγοντες",
        "sp_psy_hint":     "Το άγχος στη δουλειά και ο έλεγχος πάνω στην εργασία επηρεάζουν τον κίνδυνο μυοσκελετικών προβλημάτων.",
        "sp_lifestyle":    "Τρόπος ζωής (γυμναστική, ύπνος, διατροφή)",
        "sp_lifestyle_hint":"Οι παράγοντες αυτοί επηρεάζουν σημαντικά τον κίνδυνο μυοσκελετικών προβλημάτων. Καλή γυμναστική, επαρκής ύπνος και μεσογειακή διατροφή προστατεύουν.",

        # ---- Fields ----
        "f_subject_id":    "Όνομα ή κωδικός εργαζομένου (προαιρετικό)",
        "f_date":          "Ημερομηνία αξιολόγησης",
        "f_age":           "Ηλικία (χρόνια)",
        "f_sex":           "Φύλο",
        "f_stature":       "Ύψος (cm)",
        "f_weight":        "Βάρος (kg)",
        "f_hrs_comp":      "Ώρες υπολογιστή / ημέρα",
        "f_hrs_mouse":     "Ώρες ποντικιού / ημέρα",
        "f_hrs_sit":       "Ώρες καθιστός στη δουλειά / ημέρα",
        "f_diabetes":      "Σακχαρώδης διαβήτης",
        "f_smoking":       "Κάπνισμα",
        "f_pregnant":      "Εγκυμοσύνη τώρα",
        "f_oral_contra":   "Χρήση αντισυλληπτικών",
        "f_inj_neck":      "Αυχένας",
        "f_inj_shoulder":  "Ώμος",
        "f_inj_elbow":     "Αγκώνας",
        "f_inj_wrist":     "Καρπός / χέρι",
        "f_inj_back":      "Μέση / οσφύς",
        "f_inj_leg":       "Πόδι / κάτω άκρα",
        "f_popliteal":     "Ύψος πίσω γόνατο σε καθιστή θέση (cm)",
        "f_elbow_h":       "Ύψος αγκώνα από την έδρα (cm)",
        "f_eye_h":         "Ύψος ματιών από την έδρα (cm)",
        "f_psy_demand":    "Πίεση εργασίας (φόρτος, deadlines)",
        "f_psy_control":   "Έλεγχος στη δουλειά σας (αυτονομία)",
        "f_psy_support":   "Υποστήριξη από συναδέλφους/προϊστάμενο",
        "f_exercise":      "Συχνότητα γυμναστικής",
        "f_hypertrophy":   "Ασχολείται με προπόνηση δύναμης με μυϊκή υπερτροφία",
        "f_hypertrophy_h": "Αν ναι, το αυξημένο BMI αντικατοπτρίζει κυρίως άλιπη μάζα. Για μυοσκελετικές παθήσεις που οδηγούνται από μεταβολική φλεγμονή (CTS, τενοντίτιδα ώμου/αγκώνα), ο κίνδυνος BMI μειώνεται. Για παθήσεις μηχανικού φόρτου (οσφυαλγία, φλεβική ανεπάρκεια), το BMI εξακολουθεί να μετράει πλήρως γιατί ο μηχανικός φόρτος στη σπονδυλική/άρθρωση δεν εξαρτάται από τη σύνθεση σώματος.",
        "f_sleep":         "Ώρες ύπνου / νύχτα",
        "f_non_work_pa":   "Λεπτά μέτριας φυσικής δραστηριότητας / εβδομάδα (εκτός δουλειάς)",
        "f_non_work_pa_h": "Ο ΠΟΥ συνιστά ≥150 λεπτά/εβδομάδα μέτριας ή ≥75 λεπτά έντονης δραστηριότητας.",
        "f_diet_med":      "Τήρηση Μεσογειακής διατροφής",
        "f_diet_med_h":    "Υψηλή τήρηση = τακτική κατανάλωση ελαιολάδου, φρούτων, λαχανικών, ψαριού, δημητριακών ολικής άλεσης. Χαμηλή = επεξεργασμένα, ζάχαρη, κόκκινο κρέας.",

        # ---- Select options ----
        "opt_female":      "Γυναίκα",
        "opt_male":        "Άντρας",
        "opt_avg":         "Μέσος όρος",
        "opt_never":       "Ποτέ",
        "opt_former":      "Πρώην καπνιστής",
        "opt_current":     "Ενεργός καπνιστής",
        "opt_low":         "Χαμηλή",
        "opt_moderate":    "Μέτρια",
        "opt_high":        "Υψηλή",
        "opt_ex_never":    "Ποτέ",
        "opt_ex_1_2":      "1-2 φορές/εβδομάδα",
        "opt_ex_3_5":      "3-5 φορές/εβδομάδα",
        "opt_ex_6plus":    "6+ φορές/εβδομάδα",
        "opt_sleep_lt6":   "< 6 ώρες",
        "opt_sleep_6_7":   "6-7 ώρες",
        "opt_sleep_7_8":   "7-8 ώρες",
        "opt_sleep_8_9":   "8-9 ώρες",
        "opt_sleep_gt9":   "> 9 ώρες",

        # ---- Tabs ----
        "tab_1":           "🪑 Ιδανική θέση εργασίας",
        "tab_2":           "📐 Πραγματικές μετρήσεις",
        "tab_3":           "✅ Έλεγχος καρέκλας (EN 1335 / ISO 9241-5)",
        "tab_4":           "📏 Γωνίες αρθρώσεων",
        "tab_rosa":        "🎯 ROSA Assessment",
        "tab_5":           "📋 Σύνοψη",

        # ROSA labels
        "rosa_title":      "ROSA — Rapid Office Strain Assessment",
        "rosa_intro":      "Validated instrument (Sonne, Villalta & Andrews 2012, *Applied Ergonomics* 43:98-108). Ο εργονόμος παρατηρεί τη θέση εργασίας και επιλέγει τι ισχύει. Το εργαλείο υπολογίζει σκορ 1-10 και επίπεδο κινδύνου.",
        "rosa_sec_a":      "Ενότητα A — Καρέκλα",
        "rosa_a1":         "A.1 Ύψος καρέκλας",
        "rosa_a2":         "A.2 Βάθος έδρας",
        "rosa_a3":         "A.3 Υποβραχιόνια",
        "rosa_a4":         "A.4 Στήριξη πλάτης",
        "rosa_sec_b":      "Ενότητα B — Οθόνη & Τηλέφωνο",
        "rosa_b1":         "B.1 Οθόνη",
        "rosa_b2":         "B.2 Τηλέφωνο",
        "rosa_sec_c":      "Ενότητα C — Ποντίκι & Πληκτρολόγιο",
        "rosa_c1":         "C.1 Ποντίκι",
        "rosa_c2":         "C.2 Πληκτρολόγιο",
        "rosa_duration":   "Διάρκεια χρήσης",
        "rosa_dur_low":    "< 30 min συνεχόμενα ή < 1h/ημέρα (−1)",
        "rosa_dur_mid":    "30 min – 1h συνεχόμενα ή 1–4h/ημέρα (0)",
        "rosa_dur_high":   "> 1h συνεχόμενα ή > 4h/ημέρα (+1)",
        "rosa_chair_score":"Chair ROSA Score",
        "rosa_monperi":    "Monitor & Peripherals ROSA",
        "rosa_final":      "ROSA FINAL SCORE",
        "rosa_action":     "Επίπεδο κινδύνου",
        "rosa_check_all":  "Επιλέξτε ό,τι ισχύει (base = 1 πάντα, οι επιλογές προσθέτουν πόντους)",

        # ---- Assessment sections divider ----
        "sections_label":  "Ενότητες αξιολόγησης",

        # ---- Summary tab ----
        "sum_report_title":"Αναφορά εργονομικής αξιολόγησης",
        "sum_intended":    "**Σε τι χρησιμεύει.** Αυτό είναι εργαλείο υποστήριξης αποφάσεων για εργονόμους. **Δεν είναι ιατρικό μηχάνημα**, δεν κάνει διάγνωση, και δεν σας λέει την πιθανότητα να πάθετε κάποια πάθηση. Δείχνει ποιοι παράγοντες κινδύνου υπάρχουν, για να ξέρετε πού να επέμβετε.",
        "sum_card_ws":     "Θέση εργασίας",
        "sum_card_chair":  "Καρέκλα (EN 1335 / ISO 9241-5)",
        "sum_card_angles": "Γωνίες σώματος",
        "sum_ws_sub":      "Καρέκλα · Γραφείο · Οθόνη",

        # ---- Domain labels ----
        "dl_all_met":      "Όλα τα βασικά κριτήρια καλύπτονται",
        "dl_some_not":     "Κάποια κριτήρια δεν καλύπτονται",
        "dl_many_not":     "Πολλά κριτήρια δεν καλύπτονται",

        # ---- Risk profile section ----
        "risk_head":       "🩺 Παράγοντες κινδύνου — τι μπορεί να επηρεάσει την υγεία",
        "risk_no_factors": "✓ Δεν βρέθηκαν σημαντικοί παράγοντες κινδύνου που να σχετίζονται με συγκεκριμένες μυοσκελετικές παθήσεις.",
        "risk_how_read":   """**Πώς να διαβάσετε αυτή την ενότητα.** Για κάθε πάθηση που σχετίζεται με τους παράγοντες κινδύνου που βρήκαμε, το εργαλείο σας λέει **πόσοι από τους γνωστούς παράγοντες κινδύνου είναι παρόντες** σε αυτόν τον άνθρωπο. Αυτό **δεν** είναι πρόβλεψη ότι θα πάθει την πάθηση. Είναι απλά ένας τρόπος να δούμε πού πρέπει να δώσουμε προσοχή.""",
        "risk_summary_line": "Βρέθηκαν **{n_risks}** παράγοντες κινδύνου, που στη βιβλιογραφία συνδέονται με **{n_conds}** μυοσκελετικές παθήσεις.",
        "risk_status_none":  "Καμία επιβαρυντική συνθήκη",
        "risk_status_some":  "Κάποιες επιβαρυντικές συνθήκες",
        "risk_status_many":  "Πολλές επιβαρυντικές συνθήκες",
        "risk_factors_present": "Παράγοντες που ισχύουν για αυτό το άτομο:",
        "risk_summary_head":    "Σύνοψη ανά πάθηση",
        "risk_summary_caption": "Για κάθε πάθηση, βλέπετε πόσοι παράγοντες κινδύνου είναι παρόντες. **Δεν** είναι πιθανότητα να πάθει κανείς την πάθηση.",
        "risk_factors_count":   "παράγοντες",

        # ---- Findings & recommendations ----
        "findings_head":       "Ευρήματα",
        "findings_none":       "✓ Δεν βρέθηκαν σημαντικά προβλήματα εργονομίας. Η θέση εργασίας ταιριάζει καλά στον εργαζόμενο.",
        "recs_head":           "Συστάσεις",
        "ws_measurements":     "📐 Μετρήσεις θέσης εργασίας — λεπτομέρειες",
        "bmi_head":            "⚖️ Θέματα εργονομίας που σχετίζονται με το BMI",
        "bmi_normal":          "✓ Το BMI είναι στα φυσιολογικά όρια ({bmi} kg/m² — {cat}). Δεν χρειάζονται ιδιαίτερες προσαρμογές λόγω βάρους.",

        # ---- Submit section ----
        "submit_head":         "📤 Υποβολή αποτελεσμάτων",
        "submit_notice":       """**Ενημέρωση για τα δεδομένα (GDPR, Άρθρο 9).** Πατώντας υποβολή, στέλνετε τα στοιχεία της αξιολόγησης — **συμπεριλαμβανομένων δεδομένων υγείας** (διαβήτη, τραυματισμών, εγκυμοσύνης) — στη βάση δεδομένων του ErgoFit. Χρησιμοποιούνται μόνο για ανάλυση ποιότητας και σύνδεση με την αξιολόγηση Ergolite (αν υπάρχει). Ο εργαζόμενος μπορεί να ανακαλέσει τη συγκατάθεση και να ζητήσει διαγραφή οποτεδήποτε.""",
        "submit_consent":      "☑ Επιβεβαιώνω ότι ο εργαζόμενος ενημερώθηκε και έδωσε **ρητή, ενημερωμένη συγκατάθεση** (GDPR Άρθρο 9(2)(a)) για την αποστολή των δεδομένων.",
        "submit_btn":          "📤 Υποβολή αξιολόγησης",
        "submit_ok":           "✅ Επιτυχής υποβολή. {msg}",
        "submit_fail":         "❌ Αποτυχία υποβολής: {msg}",

        # ---- Footer ----
        "footer_report":       "Η αναφορά δημιουργήθηκε {date} · Για αποθήκευση ως PDF: Ctrl+P → 'Αποθήκευση ως PDF'.",
        "footer_legal":        "**Σε τι χρησιμεύει το εργαλείο.** Το ErgoFit είναι λογισμικό υποστήριξης αποφάσεων για εργονόμους. **Δεν είναι ιατρικό μηχάνημα** κατά τον Κανονισμό (ΕΕ) 2017/745 — δεν κάνει διάγνωση, δεν προβλέπει νόσους, δεν αντικαθιστά γιατρό. Οι αξιολογήσεις γίνονται με βάση τα πρότυπα **EN 1335-1** (καρέκλες γραφείου), **ISO 9241-5** (θέση εργασίας) και την **Οδηγία 90/270/ΕΟΚ** (οθόνες).",
    },
    "en": {
        "lang_label":  "🌐 Γλώσσα / Language",
        "hero_brand":  "ERGOFIT · INTELLIGENCE",
        "hero_title":  "Ergonomic Assessment Tool",
        "hero_sub":    "A tool that helps you work without pain.",
        "ip_expander": "ℹ️ What this tool does · Data protection",
        "ip_body": """
**What this tool does.** ErgoFit helps the ergonomist check how well someone's workstation fits them. It finds what's wrong (chair, desk, monitor, posture) and shows which risk factors for muscle/joint problems are present.

**What it is NOT.**

- Not a **medical device** — it does not diagnose.
- Not a **prediction tool** — it does not tell you the chance of getting a condition.
- Not a **substitute for seeing a doctor**.

**What it is based on.** European standards for office chairs (EN 1335-1:2020), workstation layout (ISO 9241-5:2024), and EU Directive 90/270/EEC for screens. Estimated body dimensions come from anthropometric datasets (Panero & Zelnik, NASA STD-3000); direct measurements — when entered — take priority.

**Data protection.** The tool collects some health data (past injuries, diabetes, etc.). Before you submit anything, you need explicit consent from the person. The data can be deleted whenever they ask.
""",
        "sp_head":         "About the person",
        "sp_identity":     "Identity",
        "sp_demographics": "Basic info",
        "sp_occup":        "Work exposure",
        "sp_health":       "Health & lifestyle",
        "sp_injuries":     "Past injuries (by body region)",
        "sp_injuries_hint":"Tick every region where the person has had a past injury, sprain, or chronic pain. Risk of recurrence is higher in that specific region.",
        "sp_female":       "For women only",
        "sp_female_hint":  "These fields are disabled automatically for men.",
        "sp_anthro":       "Direct body measurements (optional)",
        "sp_anthro_hint":  "Actual measurements are more accurate than height-based estimates. Leave at 0 to use the estimate.",
        "sp_psy":          "Work stress and control",
        "sp_psy_hint":     "Work stress and how much control you have over your job affect the risk of muscle/joint problems.",
        "sp_lifestyle":    "Lifestyle (exercise, sleep, diet)",
        "sp_lifestyle_hint":"These factors substantially modify MSK risk. Regular exercise, adequate sleep, and Mediterranean-style diet are protective.",

        "f_subject_id":    "Person's name or ID (optional)",
        "f_date":          "Assessment date",
        "f_age":           "Age (years)",
        "f_sex":           "Sex",
        "f_stature":       "Height (cm)",
        "f_weight":        "Weight (kg)",
        "f_hrs_comp":      "Computer hours / day",
        "f_hrs_mouse":     "Mouse hours / day",
        "f_hrs_sit":       "Workplace sitting hours / day",
        "f_diabetes":      "Diabetes",
        "f_smoking":       "Smoking",
        "f_pregnant":      "Currently pregnant",
        "f_oral_contra":   "Uses oral contraceptives",
        "f_inj_neck":      "Neck",
        "f_inj_shoulder":  "Shoulder",
        "f_inj_elbow":     "Elbow",
        "f_inj_wrist":     "Wrist / hand",
        "f_inj_back":      "Lower back",
        "f_inj_leg":       "Leg / lower body",
        "f_popliteal":     "Behind-knee height when seated (cm)",
        "f_elbow_h":       "Elbow height from seat (cm)",
        "f_eye_h":         "Eye height from seat (cm)",
        "f_psy_demand":    "Job demand (workload, deadlines)",
        "f_psy_control":   "Control over your work (autonomy)",
        "f_psy_support":   "Support from colleagues/supervisor",
        "f_exercise":      "Exercise frequency",
        "f_hypertrophy":   "Does resistance training with muscle hypertrophy",
        "f_hypertrophy_h": "If yes, an elevated BMI mostly reflects lean mass. For conditions driven by metabolic inflammation (CTS, rotator cuff/tennis-elbow tendinopathy), BMI risk is reduced. For mechanical-load conditions (lower back pain, venous insufficiency), BMI still counts in full because spinal/joint compression depends on total body mass regardless of composition.",
        "f_sleep":         "Sleep hours per night",
        "f_non_work_pa":   "Minutes of moderate physical activity per week (outside work)",
        "f_non_work_pa_h": "WHO recommends ≥150 min/week of moderate or ≥75 min of vigorous activity.",
        "f_diet_med":      "Adherence to Mediterranean diet",
        "f_diet_med_h":    "High = regular olive oil, fruits, vegetables, fish, whole grains. Low = processed foods, sugar, red meat.",

        "opt_female":      "Female",
        "opt_male":        "Male",
        "opt_avg":         "Combined average",
        "opt_never":       "Never",
        "opt_former":      "Former smoker",
        "opt_current":     "Current smoker",
        "opt_low":         "Low",
        "opt_moderate":    "Moderate",
        "opt_high":        "High",
        "opt_ex_never":    "Never",
        "opt_ex_1_2":      "1-2 times/week",
        "opt_ex_3_5":      "3-5 times/week",
        "opt_ex_6plus":    "6+ times/week",
        "opt_sleep_lt6":   "< 6 hours",
        "opt_sleep_6_7":   "6-7 hours",
        "opt_sleep_7_8":   "7-8 hours",
        "opt_sleep_8_9":   "8-9 hours",
        "opt_sleep_gt9":   "> 9 hours",

        "tab_1":           "🪑 Ideal Workstation Setup",
        "tab_2":           "📐 Workstation Assessment",
        "tab_3":           "✅ Chair Check (EN 1335 / ISO 9241-5)",
        "tab_4":           "📏 Joint Angles",
        "tab_rosa":        "🎯 ROSA Assessment",
        "tab_5":           "📋 Summary",

        # ROSA labels
        "rosa_title":      "ROSA — Rapid Office Strain Assessment",
        "rosa_intro":      "Validated instrument (Sonne, Villalta & Andrews 2012, *Applied Ergonomics* 43:98-108). The ergonomist observes the workstation and ticks what applies. The tool computes a 1-10 score and risk action level.",
        "rosa_sec_a":      "Section A — Chair",
        "rosa_a1":         "A.1 Chair height",
        "rosa_a2":         "A.2 Pan depth",
        "rosa_a3":         "A.3 Armrests",
        "rosa_a4":         "A.4 Back support",
        "rosa_sec_b":      "Section B — Monitor & Telephone",
        "rosa_b1":         "B.1 Monitor",
        "rosa_b2":         "B.2 Telephone",
        "rosa_sec_c":      "Section C — Mouse & Keyboard",
        "rosa_c1":         "C.1 Mouse",
        "rosa_c2":         "C.2 Keyboard",
        "rosa_duration":   "Duration of use",
        "rosa_dur_low":    "< 30 min continuous or < 1h/day (−1)",
        "rosa_dur_mid":    "30 min – 1h continuous or 1–4h/day (0)",
        "rosa_dur_high":   "> 1h continuous or > 4h/day (+1)",
        "rosa_chair_score":"Chair ROSA Score",
        "rosa_monperi":    "Monitor & Peripherals ROSA",
        "rosa_final":      "ROSA FINAL SCORE",
        "rosa_action":     "Risk level",
        "rosa_check_all":  "Tick what applies (base = 1 always; each option adds points)",

        "sections_label":  "Assessment Sections",

        "sum_report_title":"Ergonomic Assessment Report",
        "sum_intended":    "**What this tool does.** This is a decision-support tool for ergonomists. **It is not a medical device**, it does not diagnose, and it does not tell you the chance of getting any specific condition. It shows which risk factors are present, so you know where to act.",
        "sum_card_ws":     "Workstation fit",
        "sum_card_chair":  "Chair (EN 1335 / ISO 9241-5)",
        "sum_card_angles": "Body angles",
        "sum_ws_sub":      "Chair · Desk · Monitor",

        "dl_all_met":      "All key criteria met",
        "dl_some_not":     "Some criteria not met",
        "dl_many_not":     "Many criteria not met",

        "risk_head":       "🩺 Risk factors — what might affect health",
        "risk_no_factors": "✓ No significant risk factors were found that are linked to specific muscle/joint conditions.",
        "risk_how_read":   """**How to read this section.** For each condition linked to the risk factors we found, the tool tells you **how many of the known risk factors are present** in this person. This is **not** a prediction that they will get the condition. It's simply a way to see where to focus attention.""",
        "risk_summary_line": "Found **{n_risks}** risk factors, which the literature links to **{n_conds}** muscle/joint conditions.",
        "risk_status_none":  "No aggravating factors",
        "risk_status_some":  "Some aggravating factors",
        "risk_status_many":  "Many aggravating factors",
        "risk_factors_present": "Factors present for this person:",
        "risk_summary_head":    "Summary by condition",
        "risk_summary_caption": "For each condition, you see how many risk factors are present. This is **not** a probability of getting the condition.",
        "risk_factors_count":   "factor(s)",

        "findings_head":       "Findings",
        "findings_none":       "✓ No significant ergonomic problems found. The workstation fits this person well.",
        "recs_head":           "Recommendations",
        "ws_measurements":     "📐 Workstation measurements — details",
        "bmi_head":            "⚖️ BMI-related ergonomic considerations",
        "bmi_normal":          "✓ BMI is in the normal range ({bmi} kg/m² — {cat}). No BMI-related considerations flagged.",

        "submit_head":         "📤 Submit results",
        "submit_notice":       """**Data protection notice (GDPR, Article 9).** By submitting, you send the assessment data — **including health data** (diabetes, injuries, pregnancy) — to the ErgoFit database. Used only for quality analysis and for linking with the Ergolite assessment (if any). The person can withdraw consent and request deletion at any time.""",
        "submit_consent":      "☑ I confirm that the person has been informed and has given **explicit, informed consent** (GDPR Article 9(2)(a)) for the data to be sent.",
        "submit_btn":          "📤 Submit assessment",
        "submit_ok":           "✅ Submitted successfully. {msg}",
        "submit_fail":         "❌ Submission failed: {msg}",

        "footer_report":       "Report generated {date} · Save as PDF: Ctrl+P → 'Save as PDF'.",
        "footer_legal":        "**What this tool does.** ErgoFit is decision-support software for ergonomists. **It is not a medical device** under Regulation (EU) 2017/745 — it does not diagnose, does not predict disease, does not replace a doctor. Assessments use **EN 1335-1** (office chairs), **ISO 9241-5** (workstation layout), and **Directive 90/270/EEC** (display screens).",

        # Tab-specific extras (EN)
        "chair_tab_head":  "Chair check",
        "chair_tab_cap":   "Based on **EN 1335-1:2020+A1:2022** (office chair dimensions & safety) and **ISO 9241-5:2024** (workstation layout & postural requirements). Tick every item the chair satisfies.",
        "chair_score":     "Compliance score",
        "angles_tab_head": "Joint comfort angles (sitting / driving posture)",
        "angles_tab_cap":  "Enter the observed angles; the comfort range is shown next to each.",
        "angles_score":    "Joints in comfort range",
        "angles_out":      "Joints out of range",
        "ideal_head":      "Ideal workstation setup",
        "ideal_cap":       "Target values calculated from body measurements. Direct measurements — if provided — take priority over height-based estimates.",
        "assess_head":     "Workstation assessment — enter the actual measurements",
        "assess_cap":      "Compare the measured values with the ideal values from the previous tab.",
    },
}

# --- Add matching Greek strings to complete the pair ---
I18N["el"].update({
    "chair_tab_head":  "Έλεγχος καρέκλας",
    "chair_tab_cap":   "Βασίζεται στα πρότυπα **EN 1335-1:2020+A1:2022** (διαστάσεις & ασφάλεια καρέκλας γραφείου) και **ISO 9241-5:2024** (σχεδιασμός θέσης εργασίας). Επιλέξτε κάθε στοιχείο που πληροί η καρέκλα.",
    "chair_score":     "Βαθμολογία συμμόρφωσης",
    "angles_tab_head": "Γωνίες αρθρώσεων (καθιστή / στάση οδήγησης)",
    "angles_tab_cap":  "Καταχωρίστε τις γωνίες που παρατηρήθηκαν· δίπλα σε κάθε μία εμφανίζεται το εύρος άνεσης.",
    "angles_score":    "Αρθρώσεις εντός εύρους άνεσης",
    "angles_out":      "Αρθρώσεις εκτός εύρους",
    "ideal_head":      "Ιδανική θέση εργασίας",
    "ideal_cap":       "Τα ιδανικά μεγέθη υπολογίζονται από τις σωματικές διαστάσεις. Οι άμεσες μετρήσεις — αν συμπληρωθούν — υπερισχύουν των εκτιμήσεων.",
    "assess_head":     "Πραγματικές μετρήσεις θέσης εργασίας",
    "assess_cap":      "Συγκρίνετε τις πραγματικές τιμές με τις ιδανικές τιμές από την προηγούμενη καρτέλα.",
})
# (re-cache local t after update — safe since t was set before this block executed as literal;
#  no-op at runtime because t is re-read at every rerun.)


# ====================================================================
# Page setup
# ====================================================================
st.set_page_config(
    page_title="ErgoFit Intelligence",
    page_icon="🪑",
    layout="wide",
)


# ====================================================================
# Language selector — top of sidebar, persists across reruns
# ====================================================================
if "lang" not in st.session_state:
    st.session_state["lang"] = "el"   # default: Greek

with st.sidebar:
    st.session_state["lang"] = st.radio(
        I18N[st.session_state["lang"]]["lang_label"],
        options=["el", "en"],
        format_func=lambda x: "🇬🇷 Ελληνικά" if x == "el" else "🇬🇧 English",
        horizontal=True,
        index=0 if st.session_state["lang"] == "el" else 1,
    )

    # ---- Quick Mode toggle ---------------------------------------
    # Ενεργοποιεί σύντομη αξιολόγηση (~15 min αντί 45 min):
    # κρύβει τα προαιρετικά sub-sections που δεν είναι απαραίτητα
    # για τα core outputs. Ο εργονόμος τα ενεργοποιεί αν χρειαστεί.
    _quick_label = ("⚡ Quick Mode (γρήγορη αξιολόγηση)"
                    if st.session_state["lang"] == "el"
                    else "⚡ Quick Mode (fast assessment)")
    quick_mode = st.checkbox(
        _quick_label,
        value=False,
        key="quick_mode",
        help=(
            "Κρύβει προαιρετικές ενότητες (άμεση σωματομετρία, ψυχοκοινωνικοί "
            "παράγοντες, τρόπος ζωής) για γρήγορη αξιολόγηση 15-20 λεπτών "
            "αντί 45. Μπορείτε να ξανα-ενεργοποιήσετε τις πλήρεις ενότητες "
            "οποτεδήποτε."
            if st.session_state["lang"] == "el" else
            "Hides optional sections (direct anthropometry, psychosocial "
            "factors, lifestyle) for a fast 15-20 min assessment instead "
            "of 45 min. You can re-enable full sections at any time."
        ),
    )

lang = st.session_state["lang"]
t = I18N[lang]


# ====================================================================
# Background logo (auto-loads if  logo.png|jpg|jpeg|svg  is in folder)
# ====================================================================
def _load_logo_b64():
    here = Path(__file__).parent
    for ext in ("png", "jpg", "jpeg", "svg"):
        p = here / f"logo.{ext}"
        if p.exists():
            return base64.b64encode(p.read_bytes()).decode("ascii"), ext
    return None, None


_logo_b64, _logo_ext = _load_logo_b64()
if _logo_b64:
    _ext_to_mime = {"svg": "image/svg+xml", "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}
    _mime = _ext_to_mime.get(_logo_ext, f"image/{_logo_ext}")
    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"]::before {{
            content: "";
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background-image: url("data:{_mime};base64,{_logo_b64}");
            background-repeat: no-repeat;
            background-position: center center;
            background-size: 55% auto;
            filter: blur(6px);
            opacity: 0.07;
            z-index: 0;
            pointer-events: none;
        }}
        [data-testid="stAppViewContainer"] > .main {{
            position: relative;
            z-index: 1;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ====================================================================
# Global styling tweaks
# ====================================================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* ───────────────────── Foundation ───────────────────── */
    html, body, [class*="css"], .stApp, [data-testid="stMarkdownContainer"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        color: #0f172a;
    }
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, #f8fafc 0%, #eef2f6 100%);
    }
    .block-container {
        padding-top: 2.5rem;
        padding-bottom: 4rem;
        max-width: 1280px;
    }

    /* ───────────────────── Typography ───────────────────── */
    h1, h2, h3, h4, h5, h6 {
        color: #0f172a !important;
    }
    h1 {
        font-weight: 800 !important;
        letter-spacing: -0.03em !important;
        font-size: 38px !important;
        line-height: 1.15 !important;
    }
    h2 {
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        font-size: 24px !important;
    }
    h3 {
        font-weight: 600 !important;
        letter-spacing: -0.01em !important;
    }
    p, span, label, li, div {
        color: #0f172a;
    }
    [data-testid="stCaptionContainer"], .stCaption {
        color: #475569 !important;
        font-size: 14px !important;
    }
    .stMarkdown p {
        color: #0f172a !important;
    }

    /* ───────────────────── Hero header ───────────────────── */
    .ergo-hero {
        padding: 32px 36px;
        background: linear-gradient(135deg, #134e4a 0%, #0d9488 60%, #14b8a6 100%);
        border-radius: 18px;
        margin-bottom: 28px;
        box-shadow: 0 10px 30px rgba(13, 148, 136, 0.18);
        position: relative;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 32px;
    }
    /* Force ALL text inside the hero to be white */
    .ergo-hero, .ergo-hero * {
        color: #ffffff !important;
    }
    .ergo-hero::after {
        content: "";
        position: absolute;
        top: -40%; right: -10%;
        width: 380px; height: 380px;
        background: radial-gradient(circle, rgba(255,255,255,0.10) 0%, transparent 60%);
        border-radius: 50%;
        pointer-events: none;
        z-index: 0;
    }
    .ergo-hero .hero-content { position: relative; z-index: 1; flex: 1; min-width: 0; }
    .ergo-hero .hero-illustration {
        position: relative; z-index: 1;
        flex: 0 0 200px;
        height: 180px;
        opacity: 0.92;
    }
    .ergo-hero .brand-row {
        display: flex; align-items: center; gap: 12px;
        font-size: 11px; font-weight: 600; letter-spacing: 0.18em;
        text-transform: uppercase; opacity: 0.85; margin-bottom: 12px;
    }
    .ergo-hero .brand-dot {
        width: 8px; height: 8px; border-radius: 50%;
        background: #5eead4; box-shadow: 0 0 0 4px rgba(94, 234, 212, 0.25);
        flex-shrink: 0;
    }
    .ergo-hero h1 {
        font-size: 36px !important;
        font-weight: 800 !important;
        margin: 0 !important;
        letter-spacing: -0.03em !important;
        line-height: 1.1;
    }
    .ergo-hero .subtitle {
        margin-top: 12px;
        font-size: 16px;
        opacity: 0.92;
        font-weight: 400;
        max-width: 560px;
        line-height: 1.5;
    }
    /* Logo on right side of hero (transparent PNG over teal) */
    .ergo-hero .hero-logo {
        position: relative; z-index: 1;
        flex: 0 0 auto;
        height: 130px;
        width: auto;
        max-width: 260px;
        object-fit: contain;
        filter: drop-shadow(0 4px 12px rgba(0,0,0,0.25));
    }
    /* Hide illustration & shrink logo on narrow screens */
    @media (max-width: 768px) {
        .ergo-hero { flex-direction: column; align-items: flex-start; }
        .ergo-hero .hero-illustration { display: none; }
        .ergo-hero .hero-logo { height: 60px; margin-top: 12px; }
    }

    /* ───────────────────── Vibrant section divider above tabs ───────────────────── */
    .tabs-divider {
        margin: 28px 0 0;
        padding: 18px 26px;
        background: linear-gradient(135deg, #0d9488 0%, #14b8a6 60%, #2dd4bf 100%);
        border: 1.5px solid #0d9488;
        border-bottom: none;
        border-radius: 16px 16px 0 0;
        color: #ffffff !important;
        font-weight: 800;
        font-size: 13px;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        display: flex;
        align-items: center;
        gap: 14px;
        box-shadow: 0 6px 20px rgba(13, 148, 136, 0.30);
        position: relative;
        overflow: hidden;
    }
    .tabs-divider * { color: #ffffff !important; }
    .tabs-divider::after {
        content: "";
        position: absolute;
        top: -50%; right: -10%;
        width: 200px; height: 200px;
        background: radial-gradient(circle, rgba(255,255,255,0.20) 0%, transparent 60%);
        border-radius: 50%;
        pointer-events: none;
    }
    .tabs-divider .brand-dot {
        width: 10px; height: 10px; border-radius: 50%;
        background: #fef3c7;
        box-shadow: 0 0 0 5px rgba(254, 243, 199, 0.30);
        flex-shrink: 0;
        position: relative; z-index: 1;
    }
    .tabs-divider + div .stTabs [data-baseweb="tab-list"] {
        border-radius: 0 0 16px 16px !important;
        background: linear-gradient(180deg, #ccfbf1 0%, #99f6e4 100%) !important;
        border: 1.5px solid #0d9488 !important;
        border-top: 0 !important;
        margin-top: 0;
        padding: 8px !important;
    }
    .tabs-divider + div .stTabs [data-baseweb="tab"] {
        color: #064e3b !important;
        font-weight: 600;
    }
    .tabs-divider + div .stTabs [aria-selected="true"] {
        background: #ffffff !important;
        color: #0d9488 !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 8px rgba(13, 148, 136, 0.25) !important;
    }

    /* ─────────────────── Long checkbox labels: prevent truncation ────
       Streamlit truncates checkbox labels by default. This forces full
       text wrapping so long chair-checklist items are fully readable. */
    [data-testid="stCheckbox"] label > div[data-testid="stMarkdownContainer"] p,
    [data-testid="stCheckbox"] label p,
    .stCheckbox label p {
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
        line-height: 1.45 !important;
    }
    [data-testid="stCheckbox"] label {
        align-items: flex-start !important;
    }

    /* ───────────────────── Section header ───────────────────── */
    .section-head {
        display: flex; align-items: center; gap: 10px;
        margin: 8px 0 14px;
        padding-bottom: 10px;
        border-bottom: 1px solid #e2e8f0;
    }
    .section-head .icon-pill {
        width: 32px; height: 32px;
        background: linear-gradient(135deg, #ccfbf1 0%, #99f6e4 100%);
        color: #0d9488;
        border-radius: 9px;
        display: flex; align-items: center; justify-content: center;
        font-size: 16px;
    }
    .section-head .label {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: #0d9488;
    }

    /* ───────────────────── Tabs (pill style) ───────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #f1f5f9;
        padding: 5px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 9px;
        padding: 10px 18px;
        font-weight: 500;
        font-size: 14px;
        color: #475569;
        border: none;
        transition: all 0.18s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #0f172a;
        background: rgba(255,255,255,0.6);
    }
    .stTabs [aria-selected="true"] {
        background: white !important;
        color: #0d9488 !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
        font-weight: 600;
    }
    .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {
        display: none;
    }

    /* ───────────────────── Inputs ───────────────────── */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input,
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        border-radius: 10px !important;
        border: 1px solid #e2e8f0 !important;
        background: white !important;
        color: #0f172a !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    /* Make ALL text inside inputs dark, regardless of nesting */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input,
    [data-testid="stTextInput"] *,
    [data-testid="stNumberInput"] *,
    [data-testid="stDateInput"] * {
        color: #0f172a !important;
    }
    /* Selectbox displayed value (closed state) */
    .stSelectbox div[data-baseweb="select"],
    .stSelectbox div[data-baseweb="select"] *,
    .stMultiSelect div[data-baseweb="select"],
    .stMultiSelect div[data-baseweb="select"] * {
        color: #0f172a !important;
        background-color: white !important;
    }
    /* Selectbox arrow icon — keep teal */
    .stSelectbox svg, .stMultiSelect svg {
        color: #0d9488 !important;
        fill: #0d9488 !important;
    }
    /* Dropdown popup (open state) — Streamlit uses baseweb popover/menu.
       Note: popups render in a portal at body level, so the rules must be global
       and aggressive enough to beat baseweb's inline styles. */
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] *,
    div[data-baseweb="menu"],
    div[data-baseweb="menu"] *,
    div[data-baseweb="select-dropdown"],
    div[data-baseweb="select-dropdown"] *,
    ul[role="listbox"],
    ul[role="listbox"] *,
    div[role="listbox"],
    div[role="listbox"] * {
        background-color: #ffffff !important;
        color: #0f172a !important;
    }
    div[data-baseweb="popover"] {
        border-radius: 10px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12) !important;
    }
    li[role="option"], div[role="option"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        padding: 8px 14px !important;
    }
    li[role="option"]:hover, div[role="option"]:hover,
    li[role="option"][aria-selected="true"], div[role="option"][aria-selected="true"] {
        background-color: #ecfdf5 !important;
        color: #0d9488 !important;
    }
    /* DateInput popup calendar */
    div[data-baseweb="calendar"],
    div[data-baseweb="calendar"] * {
        background: white !important;
        color: #0f172a !important;
    }
    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus,
    [data-testid="stDateInput"] input:focus {
        border-color: #0d9488 !important;
        box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.12) !important;
        outline: none !important;
    }
    /* Number-input +/- buttons */
    [data-testid="stNumberInput"] button {
        background: white !important;
        color: #0d9488 !important;
        border: 1px solid #e2e8f0 !important;
    }
    [data-testid="stNumberInput"] button:hover {
        background: #ecfdf5 !important;
    }
    label[data-testid="stWidgetLabel"],
    label[data-testid="stWidgetLabel"] * {
        font-weight: 500 !important;
        color: #334155 !important;
        font-size: 13px !important;
    }

    /* ───────────────────── Summary banner ───────────────────── */
    .summary-banner {
        padding: 28px 32px;
        background: linear-gradient(135deg, #134e4a 0%, #0d9488 100%);
        border-radius: 16px;
        color: white;
        margin-bottom: 26px;
        box-shadow: 0 10px 30px rgba(13, 148, 136, 0.18);
    }
    .summary-banner h2 {
        margin: 0;
        color: white !important;
        font-weight: 800;
        letter-spacing: -0.02em;
        font-size: 26px !important;
    }
    .summary-banner .meta {
        margin: 8px 0 0;
        opacity: 0.88;
        font-size: 14px;
        font-weight: 400;
    }

    /* ───────────────────── Score card ───────────────────── */
    .score-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 36px 40px;
        background: white;
        border-radius: 16px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06), 0 8px 24px rgba(15, 23, 42, 0.04);
        margin-bottom: 22px;
        border: 1px solid #e2e8f0;
    }
    .score-number {
        font-size: 76px;
        font-weight: 800;
        line-height: 1;
        letter-spacing: -0.04em;
        font-family: 'Inter', sans-serif;
    }
    .score-label {
        font-size: 12px;
        color: #64748b;
        margin-top: 8px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    .score-band {
        padding: 8px 18px;
        border-radius: 999px;
        color: white;
        font-weight: 600;
        font-size: 13px;
        letter-spacing: 0.3px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    /* ───────────────────── Quad cards ───────────────────── */
    .quad-card {
        padding: 22px 20px;
        background: white;
        border-radius: 14px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
        border: 1px solid #e2e8f0;
        text-align: center;
        height: 100%;
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }
    .quad-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
    }
    .quad-card .quad-title {
        font-size: 10px;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-weight: 700;
    }
    .quad-card .quad-value {
        font-size: 42px;
        font-weight: 800;
        margin: 8px 0 4px;
        letter-spacing: -0.03em;
        line-height: 1;
    }
    .quad-card .quad-sub {
        font-size: 12px;
        color: #64748b;
        margin-top: 4px;
    }

    /* ───────────────────── Findings ───────────────────── */
    .finding-row {
        padding: 13px 16px; margin: 7px 0;
        background: #fefce8; border-left: 4px solid #eab308;
        border-radius: 10px; color: #713f12; font-size: 14px;
    }
    .finding-ok {
        padding: 14px 18px; background: #ecfdf5;
        border-left: 4px solid #10b981; border-radius: 10px; color: #064e3b;
    }

    /* ───────────────────── Streamlit alerts ───────────────────── */
    div[data-baseweb="notification"], .stAlert {
        border-radius: 10px !important;
        border: none !important;
    }

    /* ───────────────────── Metric widget ───────────────────── */
    [data-testid="stMetric"] {
        background: white;
        padding: 18px 22px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    [data-testid="stMetricValue"] > div {
        color: #0d9488 !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em !important;
    }
    [data-testid="stMetricLabel"] {
        color: #64748b !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 11px !important;
    }

    /* ───────────────────── Buttons ───────────────────── */
    .stButton > button {
        background: #0d9488;
        color: white;
        border-radius: 10px;
        border: none;
        font-weight: 600;
        padding: 10px 20px;
        transition: background 0.15s ease, transform 0.15s ease;
        box-shadow: 0 2px 6px rgba(13, 148, 136, 0.2);
    }
    .stButton > button:hover {
        background: #0f766e;
        transform: translateY(-1px);
    }

    /* ───────────────────── Dividers ───────────────────── */
    hr {
        border: none !important;
        border-top: 1px solid #e2e8f0 !important;
        margin: 28px 0 !important;
    }

    /* ───────────────────── Expanders ───────────────────── */
    [data-testid="stExpander"] {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
    }
    [data-testid="stExpander"] summary {
        font-weight: 500;
        color: #1e293b;
    }

    /* ───────────────────── Checkboxes ───────────────────── */
    .stCheckbox {
        padding: 6px 0;
    }
    .stCheckbox label {
        font-size: 14px !important;
        color: #1e293b !important;
    }

    /* ───────────────────── Hide Streamlit anchor links on headings ───────────────────── */
    h1 > a, h2 > a, h3 > a, h4 > a, h5 > a, h6 > a,
    .stMarkdown h1 > a, .stMarkdown h2 > a, .stMarkdown h3 > a,
    .stMarkdown h4 > a, .stMarkdown h5 > a, .stMarkdown h6 > a,
    [data-testid="stHeaderActionElements"],
    [data-testid="stHeadingWithActionElements"] a,
    .stHeadingAction,
    a.anchor-link {
        display: none !important;
    }

    /* ───────────────────── Intake panel ───────────────────── */
    .subgroup-head {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: #0d9488;
        margin: 22px 0 6px;
        padding-top: 10px;
        border-top: 1px dashed #e2e8f0;
    }
    .subgroup-head:first-child { border-top: none; padding-top: 0; }
    .female-only-hint {
        font-size: 12px;
        color: #94a3b8;
        font-style: italic;
        margin: 4px 0 8px;
    }
    /* Source list in summary */
    .source-list {
        margin-top: 10px;
        padding: 14px 18px;
        background: #f8fafc;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
    }
    .source-list .src-title {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #0d9488;
        margin-bottom: 8px;
    }
    .source-list a {
        color: #0d9488;
        text-decoration: none;
        font-size: 13px;
    }
    .source-list a:hover { text-decoration: underline; }
    /* Disabled-look reinforcement */
    [aria-disabled="true"], [disabled] {
        opacity: 0.45 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ====================================================================
# Hero header
# ====================================================================
_logo_img_html = ""
if _logo_b64:
    _logo_img_html = (
        f'<img src="data:{_mime};base64,{_logo_b64}" alt="logo" class="hero-logo"/>'
    )

st.markdown(
    f"""
    <div class="ergo-hero">
        <div class="hero-content">
            <div class="brand-row">
                <span class="brand-dot"></span>
                <span>{t["hero_brand"]}</span>
            </div>
            <h1>{t["hero_title"]}</h1>
            <div class="subtitle">
                {t["hero_sub"]}
            </div>
        </div>
        {_logo_img_html}
    </div>
    """,
    unsafe_allow_html=True,
)


# ====================================================================
# Intended purpose & GDPR notice (top of app, before intake)
# ====================================================================
with st.expander(t["ip_expander"], expanded=False):
    st.markdown(t["ip_body"])

# ====================================================================
# Subject — comprehensive intake panel (above tabs, always visible)
# ====================================================================
st.markdown(
    f"""
    <div class="section-head">
        <div class="icon-pill">👤</div>
        <div class="label">{t["sp_head"]}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Options that must map to the same internal keys regardless of language
_SEX_OPTS      = ["Female", "Male", "Combined average"]
_SMOKING_OPTS  = ["Never", "Former", "Current"]
_PSY_OPTS      = ["Low", "Moderate", "High"]

def _sex_label(x):
    return {"Female": t["opt_female"], "Male": t["opt_male"],
            "Combined average": t["opt_avg"]}[x]

def _smoke_label(x):
    return {"Never": t["opt_never"], "Former": t["opt_former"],
            "Current": t["opt_current"]}[x]

def _psy_label(x):
    return {"Low": t["opt_low"], "Moderate": t["opt_moderate"],
            "High": t["opt_high"]}[x]

with st.container(border=True):

    # ---- Identity ----
    st.markdown(f'<div class="subgroup-head">{t["sp_identity"]}</div>', unsafe_allow_html=True)
    row1_id, row1_date = st.columns([3, 1])
    with row1_id:
        subject_id = st.text_input(t["f_subject_id"], value="")
    with row1_date:
        assess_date = st.date_input(t["f_date"], value=date.today())

    # ---- Demographics ----
    st.markdown(f'<div class="subgroup-head">{t["sp_demographics"]}</div>', unsafe_allow_html=True)
    row2_age, row2_sex, row2_h, row2_w = st.columns(4)
    with row2_age:
        age = st.number_input(
            t["f_age"], min_value=18, max_value=100, value=35, step=1,
        )
    with row2_sex:
        sex = st.selectbox(t["f_sex"], _SEX_OPTS, format_func=_sex_label)
    with row2_h:
        height = st.selectbox(
            t["f_stature"], options=list(range(140, 211)), index=30,
        )
    with row2_w:
        weight = st.selectbox(
            t["f_weight"], options=list(range(40, 181)), index=30,
        )

    is_male   = (sex == "Male")
    is_female = (sex == "Female")

    # ---- Occupational exposure ----
    st.markdown(f'<div class="subgroup-head">{t["sp_occup"]}</div>', unsafe_allow_html=True)
    row3_c, row3_m, row3_s = st.columns(3)
    with row3_c:
        hours_computer = st.number_input(
            t["f_hrs_comp"], min_value=0.0, max_value=16.0, value=8.0, step=0.5,
        )
    with row3_m:
        hours_mouse = st.number_input(
            t["f_hrs_mouse"], min_value=0.0, max_value=16.0, value=4.0, step=0.5,
        )
    with row3_s:
        _sit_help = (
            "Μόνο οι ώρες που κάθεται στη δουλειά — όχι το σύνολο της ημέρας. "
            "Ο πολλαπλασιαστής κινδύνου βασίζεται σε meta-analysis "
            "εργασιακού καθίσματος (Dzakpasu 2021)."
            if lang == "el" else
            "Only workplace sitting hours — not total daily sitting. "
            "The risk multiplier is based on a workplace-sitting "
            "meta-analysis (Dzakpasu 2021)."
        )
        hours_sitting = st.number_input(
            t["f_hrs_sit"], min_value=0.0, max_value=16.0, value=8.0, step=0.5,
            help=_sit_help,
        )

    # ---- Health & lifestyle ----
    st.markdown(f'<div class="subgroup-head">{t["sp_health"]}</div>', unsafe_allow_html=True)
    row4_db, row4_sm = st.columns(2)
    with row4_db:
        diabetes = st.checkbox(t["f_diabetes"])
    with row4_sm:
        smoking = st.selectbox(t["f_smoking"], _SMOKING_OPTS, format_func=_smoke_label)

    # ---- Prior musculoskeletal injuries by region ----
    st.markdown(
        f'<div class="subgroup-head">{t["sp_injuries"]}</div>'
        f'<div class="female-only-hint">{t["sp_injuries_hint"]}</div>',
        unsafe_allow_html=True,
    )
    inj_row1 = st.columns(3)
    with inj_row1[0]:
        inj_neck     = st.checkbox(t["f_inj_neck"])
    with inj_row1[1]:
        inj_shoulder = st.checkbox(t["f_inj_shoulder"])
    with inj_row1[2]:
        inj_elbow    = st.checkbox(t["f_inj_elbow"])
    inj_row2 = st.columns(3)
    with inj_row2[0]:
        inj_wrist    = st.checkbox(t["f_inj_wrist"])
    with inj_row2[1]:
        inj_back     = st.checkbox(t["f_inj_back"])
    with inj_row2[2]:
        inj_leg      = st.checkbox(t["f_inj_leg"])

    injury_regions = {
        "neck":     inj_neck,
        "shoulder": inj_shoulder,
        "elbow":    inj_elbow,
        "wrist":    inj_wrist,
        "back":     inj_back,
        "leg":      inj_leg,
    }

    # ---- Female-only ----
    st.markdown(
        f'<div class="subgroup-head">{t["sp_female"]}</div>'
        f'<div class="female-only-hint">{t["sp_female_hint"]}</div>',
        unsafe_allow_html=True,
    )
    row5_p, row5_oc = st.columns(2)
    with row5_p:
        pregnant = st.checkbox(t["f_pregnant"], disabled=is_male)
    with row5_oc:
        oral_contra = st.checkbox(t["f_oral_contra"], disabled=is_male)

    # ---- Direct anthropometry (skipped in Quick Mode) ----
    if quick_mode:
        popliteal_h_direct = seated_elbow_h_direct = seated_eye_h_direct = 0.0
    else:
        st.markdown(
            f'<div class="subgroup-head">{t["sp_anthro"]}</div>',
            unsafe_allow_html=True,
        )
        st.caption(t["sp_anthro_hint"])
        row_a1, row_a2, row_a3 = st.columns(3)
        with row_a1:
            popliteal_h_direct = st.number_input(
                t["f_popliteal"], min_value=0.0, max_value=70.0,
                value=0.0, step=0.5,
            )
        with row_a2:
            seated_elbow_h_direct = st.number_input(
                t["f_elbow_h"], min_value=0.0, max_value=40.0,
                value=0.0, step=0.5,
            )
        with row_a3:
            seated_eye_h_direct = st.number_input(
                t["f_eye_h"], min_value=0.0, max_value=90.0,
                value=0.0, step=0.5,
            )

    # ---- Psychosocial workload (skipped in Quick Mode) ----
    if quick_mode:
        psy_demand = psy_control = psy_support = "Moderate"
    else:
        st.markdown(
            f'<div class="subgroup-head">{t["sp_psy"]}</div>',
            unsafe_allow_html=True,
        )
        st.caption(t["sp_psy_hint"])
        row_ps1, row_ps2, row_ps3 = st.columns(3)
        with row_ps1:
            psy_demand = st.select_slider(
                t["f_psy_demand"],
                options=_PSY_OPTS, value="Moderate", format_func=_psy_label,
            )
        with row_ps2:
            psy_control = st.select_slider(
                t["f_psy_control"],
                options=_PSY_OPTS, value="Moderate", format_func=_psy_label,
            )
        with row_ps3:
            psy_support = st.select_slider(
                t["f_psy_support"],
                options=_PSY_OPTS, value="Moderate", format_func=_psy_label,
            )

    # ---- Lifestyle: exercise, hypertrophy, sleep, non-work PA, diet ----
    # Rationale: strong confounders/protective factors for MSK outcomes
    # that are missing from most ergonomic tools. Added Sept 2026 following
    # adversarial peer review. Muscle-mass adjustment for BMI addresses the
    # well-known BMI misclassification of resistance-trained individuals
    # (Prentice 2001; Rothman 2008).
    if quick_mode:
        exercise_freq      = "1-2x/week"
        muscle_hypertrophy = False
        sleep_hours        = "6-7h"
        non_work_pa_min    = 0
        diet_med           = "Moderate"
    else:
        st.markdown(
            f'<div class="subgroup-head">{t["sp_lifestyle"]}</div>',
            unsafe_allow_html=True,
        )
        st.caption(t["sp_lifestyle_hint"])

        _EX_OPTS    = ["Never", "1-2x/week", "3-5x/week", "6+/week"]
        _SLEEP_OPTS = ["<6h", "6-7h", "7-8h", "8-9h", ">9h"]

        def _ex_label(x):
            return {"Never": t["opt_ex_never"], "1-2x/week": t["opt_ex_1_2"],
                    "3-5x/week": t["opt_ex_3_5"], "6+/week": t["opt_ex_6plus"]}[x]

        def _sleep_label(x):
            return {"<6h": t["opt_sleep_lt6"], "6-7h": t["opt_sleep_6_7"],
                    "7-8h": t["opt_sleep_7_8"], "8-9h": t["opt_sleep_8_9"],
                    ">9h": t["opt_sleep_gt9"]}[x]

        row_ls1, row_ls2, row_ls3 = st.columns(3)
        with row_ls1:
            exercise_freq = st.select_slider(
                t["f_exercise"], options=_EX_OPTS, value="1-2x/week",
                format_func=_ex_label,
            )
        with row_ls2:
            sleep_hours = st.select_slider(
                t["f_sleep"], options=_SLEEP_OPTS, value="6-7h",
                format_func=_sleep_label,
            )
        with row_ls3:
            non_work_pa_min = st.number_input(
                t["f_non_work_pa"], min_value=0, max_value=1000, value=0, step=15,
                help=t["f_non_work_pa_h"],
            )

        row_ls4, row_ls5 = st.columns(2)
        with row_ls4:
            muscle_hypertrophy = st.checkbox(
                t["f_hypertrophy"], value=False,
                help=t["f_hypertrophy_h"],
            )
        with row_ls5:
            diet_med = st.select_slider(
                t["f_diet_med"], options=_PSY_OPTS, value="Moderate",
                format_func=_psy_label,
                help=t["f_diet_med_h"],
            )

# ---- Backwards-compat alias used by ANSUR ratios block below ----
# The ANSUR block expects "Female-typical" / "Male-typical" / "Combined average".
if   sex == "Female":           sex_anthro = "Female-typical"
elif sex == "Male":             sex_anthro = "Male-typical"
else:                           sex_anthro = "Combined average"

# ---- BMI computation + WHO category + load multipliers ---------
bmi = round(weight / ((height / 100) ** 2), 1)

if   bmi < 18.5: bmi_cat, bmi_color, bmi_band = "Underweight",     "#3b82f6", "normal"
elif bmi < 25.0: bmi_cat, bmi_color, bmi_band = "Normal",          "#10b981", "normal"
elif bmi < 30.0: bmi_cat, bmi_color, bmi_band = "Overweight",      "#f59e0b", "overweight"
elif bmi < 35.0: bmi_cat, bmi_color, bmi_band = "Obese class I",   "#ef4444", "obese"
elif bmi < 40.0: bmi_cat, bmi_color, bmi_band = "Obese class II",  "#dc2626", "obese"
else:            bmi_cat, bmi_color, bmi_band = "Obese class III", "#991b1b", "obese"

# Biomechanical load factors per BMI band
# Sources: WHO; NIOSH; Biomechanics meta-analyses (2020-2024).
LOAD_FACTORS = {
    "normal": {
        "spine_l4l5":      1.00, "neck_fatigue":   1.00,
        "seat_pressure":   1.00, "shoulder_load":  1.00,
        "edema_risk":      1.00,
        "reach_extra_cm":  0,
        "break_minutes":   60,
    },
    "overweight": {
        "spine_l4l5":      1.09, "neck_fatigue":   1.05,
        "seat_pressure":   1.11, "shoulder_load":  1.04,
        "edema_risk":      1.20,
        "reach_extra_cm":  3,    # midpoint of 2-4 cm
        "break_minutes":   47,   # midpoint of 45-50 min
    },
    "obese": {
        "spine_l4l5":      1.18, "neck_fatigue":   1.12,
        "seat_pressure":   1.25, "shoulder_load":  1.10,
        "edema_risk":      1.50,
        "reach_extra_cm":  7,    # midpoint of 5-10 cm
        "break_minutes":   35,   # midpoint of 30-40 min
        "com_forward_pct": 4,    # midpoint of 3-5 % trunk height shift
    },
}
load = LOAD_FACTORS[bmi_band]

# ---- BMI-adjusted equipment specifications --------------------
# Sources: OSHA Workstation eTool; ILO Ergonomic Checkpoints; PubMed.
EQUIPMENT_SPECS = {
    "normal": {
        "chair": [
            ("Seat width",          "≥ 45 cm (standard)"),
            ("Mechanism strength",  "Standard rating"),
            ("Seat depth",          "Standard adjustable (38–45 cm)"),
        ],
        "desk": [
            ("Surface height",      "72–76 cm (standard)"),
            ("Leg-space width",     "Standard (60–80 cm)"),
            ("Reach distance",      "Standard arm reach"),
        ],
    },
    "overweight": {
        "chair": [
            ("Seat width",          "45–50 cm"),
            ("Mechanism strength",  "Up to 120 kg"),
            ("Seat depth",          "Adjustable 40–45 cm"),
        ],
        "desk": [
            ("Surface height",      "72–76 cm (standard)"),
            ("Leg-space width",     "Standard (60–80 cm)"),
            ("Reach distance",      "+2–4 cm extra clearance"),
        ],
    },
    "obese": {
        "chair": [
            ("Seat width",          "> 55 cm (Bariatric)"),
            ("Mechanism strength",  "150–250 kg (Heavy Duty)"),
            ("Seat depth",          "Adjustable with slider"),
        ],
        "desk": [
            ("Surface height",      "Adjustable (Sit-Stand recommended)"),
            ("Leg-space width",     "Widened > 90 cm"),
            ("Reach distance",      "+6–10 cm (Belly-cut desk recommended)"),
        ],
    },
}
equip = EQUIPMENT_SPECS[bmi_band]


# ====================================================================
# Dynamic posture visualization (side-view SVG of worker at workstation)
# ====================================================================
def render_posture_svg(stature_cm, weight_kg,
                       chair_h, desk_h, monitor_h,
                       chair_diff, desk_diff, monitor_diff):
    """Professional editorial-style side-view of the seated worker.

    All elements parametric to subject's body and workstation measurements.
    Body silhouette uses smooth bezier paths; chair is a modern ergonomic
    office chair with curves and pedestal; monitor has bezel and stand.
    Status colours: green = within tolerance, amber = mild, red = significant.
    """
    # ── Palette ──────────────────────────────────────────────────
    OK    = "#10b981"
    WARN  = "#f59e0b"
    BAD   = "#dc2626"
    BODY  = "#334155"      # slate-700 — body silhouette
    BODY2 = "#475569"      # slate-600 — shading
    SKIN  = "#fde6c8"      # warm beige
    SKIN_SHADE = "#e8c8a0"
    HAIR  = "#1e293b"      # slate-900
    DESK_TONE = "#a8a29e"  # warm stone
    FLOOR = "#cbd5e1"
    BG_TOP = "#f0fdfa"
    BG_BOT = "#e6fffa"
    SHADOW = "#0f172a"

    def col(diff, tol):
        a = abs(diff)
        if a <= tol:        return OK
        if a <= tol * 2:    return WARN
        return BAD

    chair_c   = col(chair_diff,   2)
    desk_c    = col(desk_diff,    2)
    monitor_c = col(monitor_diff, 4)

    # ── Body segment proportions (Drillis & Contini 1966 — body segment
    # PARAMETERS for kinematics; head/trunk/limb length fractions of stature).
    # These are correctly attributed here: they concern segment lengths for
    # drawing the silhouette, not seated ergonomic dimensions. ───────
    head_d    = 0.130 * stature_cm
    trunk     = 0.288 * stature_cm
    upper_arm = 0.186 * stature_cm
    forearm   = 0.146 * stature_cm
    thigh     = 0.245 * stature_cm

    # Body girth (light visual hint of BMI / weight)
    girth = max(10, min(22, 11 + (weight_kg - 60) * 0.11))

    # ── Layout ───────────────────────────────────────────────────
    scale   = 1.7
    floor_y = 470
    def y(cm): return floor_y - cm * scale

    pelvis_x = 175
    pelvis_y = y(chair_h)
    shoulder_x = pelvis_x
    shoulder_y = pelvis_y - trunk * scale

    head_r  = (head_d * scale) / 2
    head_cx = shoulder_x + 2
    head_cy = shoulder_y - head_r - 6

    # Head tilt from monitor misalignment
    # Stronger tilt so the visual clearly matches the recommendation text.
    head_tilt = 0
    if   monitor_diff >  8: head_tilt = -22
    elif monitor_diff >  4: head_tilt = -14
    elif monitor_diff < -8: head_tilt =  24
    elif monitor_diff < -4: head_tilt =  16

    # Thigh + knee + shin
    knee_x = pelvis_x + thigh * scale
    knee_y = pelvis_y
    foot_x = knee_x + 8
    foot_y = floor_y
    feet_dangle = False
    if chair_diff > 4:
        feet_dangle = True
        foot_y = pelvis_y + 0.246 * stature_cm * scale

    # Arms reach forward to desk
    desk_y_svg = y(desk_h)
    elbow_x = shoulder_x + upper_arm * scale * 0.50
    elbow_y = shoulder_y + upper_arm * scale * 0.82
    hand_x  = elbow_x + forearm * scale * 0.95
    hand_y  = desk_y_svg

    # Desk geometry
    desk_x_start = knee_x + 22
    desk_w = 210
    desk_thickness = 8

    # Monitor geometry
    mon_top_y = y(monitor_h)
    mon_h_svg = max(45, (monitor_h - desk_h) * scale * 0.58)
    mon_w     = 110
    mon_x     = desk_x_start + 55
    mon_bot_y = mon_top_y + mon_h_svg
    bezel = 3
    stand_top_y = mon_bot_y
    stand_bot_y = desk_y_svg

    # ── Seated eye height + ideal monitor top marker ──────────────
    # Anthropometric ratio: seated eye height ≈ 0.452 × stature.
    # Ergonomic best practice: monitor TOP should sit at or slightly
    # BELOW eye level (ANSI/HFES 100, ISO 9241-5). We visualise both:
    #   • Eye level line  = actual eye height
    #   • Ideal monitor top = eye level minus a 5 cm safety margin
    EYE_MARGIN_CM = 5
    seated_eye_above_chair = 0.452 * stature_cm
    eye_actual_cm    = chair_h + seated_eye_above_chair
    eye_y_svg        = y(eye_actual_cm)
    ideal_mon_top_cm = eye_actual_cm - EYE_MARGIN_CM
    ideal_mon_top_y  = y(ideal_mon_top_cm)
    show_ideal_mon   = abs(monitor_h - ideal_mon_top_cm) > 4

    # Extra warning: monitor top ABOVE eye level is always bad, no matter
    # how small the difference — forces sustained neck extension.
    above_eye = monitor_h > eye_actual_cm

    # Downward-gaze indicator when monitor is too low
    gaze_note = ""
    if monitor_diff < -4:
        gaze_note = "GAZE FORCED DOWN — head tilts forward"
    elif monitor_diff > 4:
        gaze_note = "GAZE FORCED UP — neck extended"

    # Coordinates for body silhouette path (torso)
    # Trapezoid-ish: wider at shoulder, narrower at pelvis, slight curve
    tw_top = girth * 0.95          # shoulder width (lateral, but here visual width)
    tw_bot = girth * 0.85          # waist
    sh_lx = shoulder_x - tw_top * 0.45
    sh_rx = shoulder_x + tw_top * 0.55
    pv_lx = pelvis_x   - tw_bot * 0.45
    pv_rx = pelvis_x   + tw_bot * 0.55

    # Arm path control points
    ua_w = girth * 0.32  # upper arm thickness
    fa_w = girth * 0.26  # forearm thickness

    # Thigh thickness
    th_w = girth * 0.40
    sh_w = girth * 0.30  # shin

    svg = f"""
<svg viewBox="0 0 560 520" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;">
  <defs>
    <linearGradient id="bgGrad" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="{BG_TOP}"/>
      <stop offset="1" stop-color="{BG_BOT}"/>
    </linearGradient>
    <linearGradient id="bodyGrad" x1="0" x2="1" y1="0" y2="0">
      <stop offset="0" stop-color="{BODY}"/>
      <stop offset="1" stop-color="{BODY2}"/>
    </linearGradient>
    <linearGradient id="chairGrad" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="{chair_c}" stop-opacity="0.95"/>
      <stop offset="1" stop-color="{chair_c}" stop-opacity="0.75"/>
    </linearGradient>
    <linearGradient id="deskGrad" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="{desk_c}"/>
      <stop offset="1" stop-color="{desk_c}" stop-opacity="0.85"/>
    </linearGradient>
    <linearGradient id="monGrad" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="#0f172a"/>
      <stop offset="1" stop-color="#1e293b"/>
    </linearGradient>
    <linearGradient id="screenGrad" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="#67e8f9" stop-opacity="0.35"/>
      <stop offset="1" stop-color="#a7f3d0" stop-opacity="0.20"/>
    </linearGradient>
    <radialGradient id="floorShadow" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="{SHADOW}" stop-opacity="0.25"/>
      <stop offset="1" stop-color="{SHADOW}" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <!-- Background -->
  <rect width="560" height="520" fill="url(#bgGrad)" rx="14"/>

  <!-- Floor: subtle dual line + perspective hint -->
  <line x1="20" y1="{floor_y}" x2="540" y2="{floor_y}" stroke="{FLOOR}" stroke-width="2.5"/>
  <line x1="20" y1="{floor_y+3}" x2="540" y2="{floor_y+3}" stroke="{FLOOR}" stroke-width="1" opacity="0.55"/>

  <!-- Chair pedestal shadow on floor -->
  <ellipse cx="{pelvis_x + 10}" cy="{floor_y + 6}" rx="56" ry="6" fill="url(#floorShadow)"/>
  <!-- Desk shadow on floor -->
  <ellipse cx="{desk_x_start + desk_w/2}" cy="{floor_y + 5}" rx="{desk_w*0.55}" ry="5" fill="url(#floorShadow)"/>

  <!-- ── Chair (modern ergonomic, side view) ──────────────── -->
  <!-- Backrest with curve -->
  <path d="M {pelvis_x - 42},{pelvis_y - 6}
           Q {pelvis_x - 50},{pelvis_y - 35} {pelvis_x - 45},{pelvis_y - 70}
           Q {pelvis_x - 40},{pelvis_y - 80} {pelvis_x - 30},{pelvis_y - 78}
           Q {pelvis_x - 26},{pelvis_y - 50} {pelvis_x - 28},{pelvis_y - 10} Z"
        fill="url(#chairGrad)" stroke="{chair_c}" stroke-width="1.5" opacity="0.92"/>
  <!-- Lumbar accent line -->
  <line x1="{pelvis_x - 40}" y1="{pelvis_y - 40}" x2="{pelvis_x - 32}" y2="{pelvis_y - 40}"
        stroke="white" stroke-width="1.5" opacity="0.6"/>

  <!-- Seat cushion (rounded) -->
  <rect x="{pelvis_x - 35}" y="{pelvis_y - 2}" width="86" height="14" rx="6"
        fill="url(#chairGrad)" stroke="{chair_c}" stroke-width="1.5"/>
  <!-- Seat front stitch -->
  <line x1="{pelvis_x - 30}" y1="{pelvis_y + 9}" x2="{pelvis_x + 46}" y2="{pelvis_y + 9}"
        stroke="white" stroke-width="0.8" opacity="0.6"/>

  <!-- Cylindrical pedestal -->
  <rect x="{pelvis_x + 6}" y="{pelvis_y + 12}" width="6" height="{floor_y - pelvis_y - 24}"
        fill="#64748b" rx="2"/>
  <!-- 5-star base (simplified two-arm view) -->
  <path d="M {pelvis_x - 28},{floor_y - 2}
           Q {pelvis_x + 9},{floor_y - 12} {pelvis_x + 50},{floor_y - 2}
           Q {pelvis_x + 30},{floor_y + 2} {pelvis_x + 9},{floor_y + 2}
           Q {pelvis_x - 10},{floor_y + 2} {pelvis_x - 28},{floor_y - 2} Z"
        fill="#475569"/>
  <!-- Caster wheels -->
  <circle cx="{pelvis_x - 22}" cy="{floor_y + 3}" r="4" fill="#1e293b"/>
  <circle cx="{pelvis_x + 44}" cy="{floor_y + 3}" r="4" fill="#1e293b"/>

  <!-- ── Desk (clean tabletop with thickness) ─────────────── -->
  <rect x="{desk_x_start}" y="{desk_y_svg}" width="{desk_w}" height="{desk_thickness}" rx="2"
        fill="url(#deskGrad)" stroke="{desk_c}" stroke-width="1.2"/>
  <rect x="{desk_x_start}" y="{desk_y_svg + desk_thickness}" width="{desk_w}" height="2" rx="1"
        fill="{desk_c}" opacity="0.45"/>
  <!-- Desk leg -->
  <rect x="{desk_x_start + desk_w - 10}" y="{desk_y_svg + desk_thickness}" width="4"
        height="{floor_y - desk_y_svg - desk_thickness}" fill="#64748b"/>

  <!-- ── Monitor (modern, with bezel and stand) ───────────── -->
  <!-- Monitor body -->
  <rect x="{mon_x}" y="{mon_top_y}" width="{mon_w}" height="{mon_h_svg}" rx="4"
        fill="url(#monGrad)" stroke="{monitor_c}" stroke-width="2.5"/>
  <!-- Screen area (inset for bezel effect) -->
  <rect x="{mon_x + bezel}" y="{mon_top_y + bezel}"
        width="{mon_w - 2*bezel}" height="{mon_h_svg - 2*bezel - 4}" rx="2"
        fill="url(#screenGrad)"/>
  <!-- Brand strip at bottom of monitor -->
  <rect x="{mon_x + mon_w/2 - 8}" y="{mon_top_y + mon_h_svg - 4}" width="16" height="2"
        fill="#475569" opacity="0.7"/>
  <!-- Monitor neck -->
  <path d="M {mon_x + mon_w/2 - 4},{mon_bot_y}
           L {mon_x + mon_w/2 + 4},{mon_bot_y}
           L {mon_x + mon_w/2 + 3},{desk_y_svg - 4}
           L {mon_x + mon_w/2 - 3},{desk_y_svg - 4} Z"
        fill="{monitor_c}" opacity="0.85"/>
  <!-- Monitor base on desk -->
  <ellipse cx="{mon_x + mon_w/2}" cy="{desk_y_svg - 2}" rx="22" ry="3.5" fill="{monitor_c}" opacity="0.85"/>

  <!-- ── Body silhouette ───────────────────────────────── -->
  <!-- Thigh (rounded shape, horizontal) -->
  <path d="M {pelvis_x - 4},{pelvis_y - th_w*0.45}
           L {knee_x - 6},{pelvis_y - th_w*0.45}
           Q {knee_x + 4},{pelvis_y - th_w*0.45} {knee_x + 4},{pelvis_y - th_w*0.10}
           Q {knee_x + 4},{pelvis_y + th_w*0.55} {knee_x - 8},{pelvis_y + th_w*0.55}
           L {pelvis_x - 4},{pelvis_y + th_w*0.55}
           Q {pelvis_x - 14},{pelvis_y + th_w*0.05} {pelvis_x - 4},{pelvis_y - th_w*0.45} Z"
        fill="url(#bodyGrad)"/>

  <!-- Shin (vertical rounded shape) -->
  <path d="M {knee_x - sh_w*0.45},{knee_y - 4}
           Q {knee_x - sh_w*0.55},{(knee_y+foot_y)/2} {knee_x - sh_w*0.40},{foot_y - 3}
           L {knee_x + sh_w*0.55},{foot_y - 3}
           Q {knee_x + sh_w*0.55},{(knee_y+foot_y)/2} {knee_x + sh_w*0.45},{knee_y - 4} Z"
        fill="url(#bodyGrad)"/>

  <!-- Foot (small angled shape, only if not dangling) -->
  {(f'''<path d="M {foot_x - sh_w*0.40},{foot_y - 3}
           L {foot_x + 16},{foot_y - 5}
           Q {foot_x + 19},{foot_y - 1} {foot_x + 17},{foot_y}
           L {foot_x - sh_w*0.40},{foot_y} Z"
        fill="{BODY}"/>''') if not feet_dangle else f'''<path d="M {foot_x - sh_w*0.40},{foot_y - 3}
           L {foot_x + 12},{foot_y - 5}
           Q {foot_x + 14},{foot_y - 1} {foot_x + 12},{foot_y}
           L {foot_x - sh_w*0.40},{foot_y} Z"
        fill="{BODY}"/>'''}

  <!-- Torso silhouette (trapezoid with curves) -->
  <path d="M {sh_lx},{shoulder_y}
           Q {sh_lx - 3},{shoulder_y + (pelvis_y-shoulder_y)*0.40} {pv_lx},{pelvis_y}
           L {pv_rx},{pelvis_y}
           Q {sh_rx + 4},{shoulder_y + (pelvis_y-shoulder_y)*0.45} {sh_rx},{shoulder_y}
           Q {shoulder_x},{shoulder_y - 6} {sh_lx},{shoulder_y} Z"
        fill="url(#bodyGrad)"/>
  <!-- Subtle chest highlight -->
  <path d="M {sh_lx + 4},{shoulder_y + 8}
           Q {shoulder_x - 2},{shoulder_y + (pelvis_y-shoulder_y)*0.35} {sh_lx + 8},{(shoulder_y + pelvis_y)/2}"
        stroke="white" stroke-width="2" fill="none" opacity="0.20"/>

  <!-- Upper arm (silhouette) -->
  <path d="M {shoulder_x - 1},{shoulder_y + 2}
           Q {shoulder_x + ua_w*0.3},{shoulder_y + ua_w*0.4} {elbow_x + ua_w*0.4},{elbow_y - ua_w*0.30}
           L {elbow_x + ua_w*0.5},{elbow_y + ua_w*0.15}
           Q {shoulder_x + 2},{shoulder_y + ua_w*0.7} {shoulder_x - ua_w*0.45},{shoulder_y + 6} Z"
        fill="url(#bodyGrad)"/>

  <!-- Forearm -->
  <path d="M {elbow_x - 2},{elbow_y - fa_w*0.35}
           Q {(elbow_x + hand_x)/2 + 2},{(elbow_y + hand_y)/2 - fa_w*0.30} {hand_x + fa_w*0.30},{hand_y - fa_w*0.30}
           L {hand_x + fa_w*0.30},{hand_y + fa_w*0.10}
           Q {(elbow_x + hand_x)/2},{(elbow_y + hand_y)/2 + fa_w*0.25} {elbow_x - 2},{elbow_y + fa_w*0.30} Z"
        fill="url(#bodyGrad)"/>

  <!-- Hand at desk -->
  <ellipse cx="{hand_x + 4}" cy="{hand_y - 1}" rx="8" ry="4" fill="{SKIN}" stroke="{SKIN_SHADE}" stroke-width="1"/>

  <!-- ── Head ─────────────────────────────────────────── -->
  <g transform="rotate({head_tilt} {head_cx} {head_cy})">
    <!-- Neck -->
    <path d="M {head_cx - 5},{head_cy + head_r - 2}
             L {head_cx + 5},{head_cy + head_r - 2}
             L {head_cx + 7},{shoulder_y + 1}
             L {head_cx - 7},{shoulder_y + 1} Z"
          fill="{SKIN}" stroke="{SKIN_SHADE}" stroke-width="1"/>
    <!-- Head (egg-shape, side view) -->
    <ellipse cx="{head_cx}" cy="{head_cy}" rx="{head_r}" ry="{head_r * 1.10}"
             fill="{SKIN}" stroke="{SKIN_SHADE}" stroke-width="1.5"/>
    <!-- Hair (top of head) -->
    <path d="M {head_cx - head_r * 0.9},{head_cy - head_r * 0.55}
             Q {head_cx},{head_cy - head_r * 1.30} {head_cx + head_r * 0.9},{head_cy - head_r * 0.45}
             Q {head_cx + head_r * 0.95},{head_cy - head_r * 0.10} {head_cx + head_r * 0.20},{head_cy - head_r * 0.40}
             Q {head_cx - head_r * 0.5},{head_cy - head_r * 0.70} {head_cx - head_r * 0.9},{head_cy - head_r * 0.55} Z"
          fill="{HAIR}"/>
    <!-- Ear -->
    <ellipse cx="{head_cx - head_r * 0.55}" cy="{head_cy + 1}" rx="2.5" ry="3.5"
             fill="{SKIN_SHADE}"/>
    <!-- Nose (small profile bump) -->
    <path d="M {head_cx + head_r * 0.90},{head_cy - 2}
             Q {head_cx + head_r * 1.12},{head_cy + 2} {head_cx + head_r * 0.88},{head_cy + 5}"
          stroke="{SKIN_SHADE}" stroke-width="1.5" fill="none"/>
    <!-- Eye -->
    <circle cx="{head_cx + head_r * 0.55}" cy="{head_cy - 1}" r="1.5" fill="{BODY}"/>
    <!-- Eyebrow -->
    <line x1="{head_cx + head_r * 0.40}" y1="{head_cy - 5}"
          x2="{head_cx + head_r * 0.75}" y2="{head_cy - 5}"
          stroke="{HAIR}" stroke-width="1.5" stroke-linecap="round"/>
    <!-- Mouth -->
    <line x1="{head_cx + head_r * 0.70}" y1="{head_cy + 7}"
          x2="{head_cx + head_r * 0.92}" y2="{head_cy + 7}"
          stroke="{SKIN_SHADE}" stroke-width="1.2" stroke-linecap="round"/>
  </g>

  <!-- ── Eye-level reference line (dashed, horizontal) ── -->
  <line x1="{head_cx + head_r + 4}" y1="{eye_y_svg}"
        x2="{mon_x + mon_w + 30}"    y2="{eye_y_svg}"
        stroke="{BAD if above_eye else '#0d9488'}" stroke-width="1.4"
        stroke-dasharray="4,4" opacity="0.85"/>
  <text x="{mon_x + mon_w + 34}" y="{eye_y_svg + 3}" font-size="9"
        font-family="Inter, sans-serif"
        fill="{BAD if above_eye else '#0d9488'}"
        font-weight="700" letter-spacing="0.6">EYE LEVEL · {eye_actual_cm:.0f} cm</text>

  {(f'''<!-- Warning band: monitor top ABOVE eye level -->
  <rect x="{mon_x - 6}" y="{mon_top_y - 3}"
        width="{mon_w + 12}" height="{eye_y_svg - mon_top_y + 6}"
        fill="{BAD}" opacity="0.14"/>
  <text x="{mon_x + mon_w / 2 - 60}" y="{mon_top_y - 22}" font-size="10"
        font-family="Inter, sans-serif" fill="{BAD}" font-weight="800"
        letter-spacing="0.6">⚠ MONITOR TOP ABOVE EYE LEVEL</text>
  ''') if above_eye else ''}

  {(f'''<!-- Ideal monitor top marker (dashed green line at safe eye-margin) -->
  <line x1="{mon_x - 4}" y1="{ideal_mon_top_y}"
        x2="{mon_x + mon_w + 4}" y2="{ideal_mon_top_y}"
        stroke="{OK}" stroke-width="2" stroke-dasharray="3,3" opacity="0.75"/>
  <text x="{mon_x + mon_w / 2 - 32}" y="{ideal_mon_top_y - 4}" font-size="9"
        font-family="Inter, sans-serif" fill="{OK}" font-weight="700"
        letter-spacing="0.5">IDEAL TOP · {ideal_mon_top_cm:.0f} cm</text>
  ''') if show_ideal_mon else ''}

  {(f'''<!-- Gaze-line from eye to monitor centre -->
  <line x1="{head_cx + head_r * 0.55}" y1="{head_cy - 1}"
        x2="{mon_x + mon_w / 2}" y2="{mon_top_y + mon_h_svg / 2}"
        stroke="{monitor_c}" stroke-width="1.3" stroke-dasharray="2,3" opacity="0.85"/>
  <text x="{(head_cx + mon_x + mon_w / 2) / 2 - 30}"
        y="{(head_cy + mon_top_y + mon_h_svg / 2) / 2 - 6}" font-size="9"
        font-family="Inter, sans-serif" fill="{monitor_c}" font-weight="700"
        letter-spacing="0.4">{gaze_note}</text>
  ''') if gaze_note else ''}

  <!-- ── Annotations ──────────────────────────────────── -->
  <text x="{pelvis_x - 95}" y="{pelvis_y - 85}" font-size="10.5" font-weight="700"
        font-family="Inter, sans-serif" fill="{chair_c}" letter-spacing="0.8">CHAIR · {chair_h:.0f} cm</text>
  <text x="{desk_x_start + 6}" y="{desk_y_svg - 10}" font-size="10.5" font-weight="700"
        font-family="Inter, sans-serif" fill="{desk_c}" letter-spacing="0.8">DESK · {desk_h:.0f} cm</text>
  <text x="{mon_x}" y="{mon_top_y - 8}" font-size="10.5" font-weight="700"
        font-family="Inter, sans-serif" fill="{monitor_c}" letter-spacing="0.8">MONITOR · {monitor_h:.0f} cm</text>

  {(f'<text x="{foot_x - 36}" y="{floor_y + 20}" font-size="10" fill="{BAD}" font-weight="700" font-family="Inter, sans-serif">⚠ Feet do not reach floor</text>') if feet_dangle else ''}
</svg>
"""
    return svg


# BMI display row (compact card)
st.markdown(
    f"""
    <div style="
        margin-top: 8px; padding: 14px 18px;
        background: white; border-radius: 10px;
        border-left: 5px solid {bmi_color};
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        display: flex; align-items: center; justify-content: space-between;
    ">
      <div>
        <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">
          Body Mass Index
        </div>
        <div style="font-size: 28px; font-weight: 700; color: {bmi_color};">
          {bmi}
          <span style="font-size: 14px; color: #4b5563; font-weight: 500; margin-left: 6px;">
            kg/m²
          </span>
        </div>
      </div>
      <div style="
        padding: 6px 14px; border-radius: 999px;
        background: {bmi_color}; color: white;
        font-weight: 600; font-size: 14px; letter-spacing: 0.3px;
      ">{bmi_cat}</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ====================================================================
# Seated anthropometric ratios for workstation dimensioning.
# Sources: Panero & Zelnik (Human Dimensions & Interior Space, 1979);
#          NASA STD-3000 (Man-Systems Integration Standards);
#          ANSUR I / ANSUR II US Army anthropometry.
# Direct measurements — when supplied — override height-based estimates.
#
# NOTE: Drillis & Contini 1966 is a DIFFERENT dataset that gives body
# segment PARAMETERS (mass, moment of inertia, segment length fractions)
# — used in the SVG silhouette code, not for seated ergonomic sizing.
# ====================================================================
if sex_anthro == "Female-typical":
    r_popliteal, r_elbow_sit, r_eye_sit = 0.239, 0.135, 0.453
elif sex_anthro == "Male-typical":
    r_popliteal, r_elbow_sit, r_eye_sit = 0.247, 0.131, 0.451
else:
    r_popliteal, r_elbow_sit, r_eye_sit = 0.243, 0.133, 0.452

# Ideal chair seat = measured popliteal height, OR estimated from stature
if popliteal_h_direct > 0:
    ideal_chair          = round(popliteal_h_direct, 1)
    _chair_source        = "direct"
else:
    ideal_chair          = round(r_popliteal * height, 1)
    _chair_source        = "estimate (Panero & Zelnik / ANSUR)"

# Ideal desk = chair + seated-elbow gap (direct if supplied)
if seated_elbow_h_direct > 0:
    seated_elbow_gap     = round(seated_elbow_h_direct, 1)
    _desk_source         = "direct"
else:
    seated_elbow_gap     = round(r_elbow_sit * height, 1)
    _desk_source         = "estimate"
ideal_desk_target        = round(ideal_chair + seated_elbow_gap, 1)

# Ideal monitor top edge:
# Best-practice ergonomics (ANSI/HFES 100, ISO 9241-5, OSHA):
# the TOP of the screen should be **at or slightly BELOW eye level**.
# A screen top ABOVE eye level forces sustained neck extension.
# We set the ideal at eye level MINUS a 5 cm safety margin so the
# top edge always sits comfortably at or below the eye reference line.
EYE_TO_MON_TOP_OFFSET_CM = 5  # ergonomic safety margin below eye level

if seated_eye_h_direct > 0:
    seated_eye_gap       = round(seated_eye_h_direct, 1)
    _mon_source          = "direct"
else:
    seated_eye_gap       = round(r_eye_sit * height, 1)
    _mon_source          = "estimate"

# eye_level_from_chair = seated_eye_gap
# ideal_monitor_top    = chair + eye_gap − offset (so it lands below eye level)
ideal_mon_target         = round(
    ideal_chair + seated_eye_gap - EYE_TO_MON_TOP_OFFSET_CM, 1
)


# ====================================================================
# Conditions library — evidence-based version
#
# Each condition uses a multi-factor risk model:
#     personal_risk = base_pct  ×  Π (applicable factor multipliers)
#
# All numbers are derived from PubMed meta-analyses / systematic reviews.
# DOIs are listed in the "sources" field — kept for internal reference only.
# Capped at 95% for sanity.
# ====================================================================
# Map each condition to the body region(s) where prior injury counts.
CONDITION_INJURY_REGIONS = {
    "cts":                  ["wrist"],
    "back_pain":            ["back"],
    "neck_strain":          ["neck"],
    "tendinitis_shoulder":  ["shoulder"],
    "epicondylitis_lat":    ["elbow"],
    "venous_insufficiency": ["leg"],
    # NOTE: DVT and Obstructive Sleep Apnea removed — out of scope for an
    # office-ergonomics screening tool per adversarial peer review 2026.
}
CONDITIONS = {
    # ----- 1. Carpal Tunnel Syndrome ---------------------------------
    "cts": {
        "name_en": "Carpal tunnel syndrome",
        "name_gr": "Σύνδρομο καρπιαίου σωλήνα",
        "description": (
            "Median nerve compression at the wrist; tingling/numbness in "
            "thumb, index and middle finger. Risk strongly elevated by BMI, "
            "computer/mouse exposure, female sex, diabetes, pregnancy."
        ),
        "base_pct": 4.0,                                # general adult point prevalence
        "factors": {
            "bmi":                {"normal": 1.0, "overweight": 1.47, "obese": 2.02},  # Shiri 2015
            "computer_hours_high": 1.34,                                               # ≥4 h/d, Shiri 2015
            "mouse_hours_high":    1.93,                                               # ≥4 h/d, Shiri 2015
            "sex_female":          1.40,                                               # CTS is markedly more common in women
            "diabetes":            2.00,                                               # well-established RR
            "pregnancy":           2.50,                                               # well-established RR
            "prior_injury":        1.30,
        },
        "sources": [
            ("Shiri et al., 2015 — BMI meta-analysis (n=1.38M, 58 studies)",
             "10.1111/obr.12324"),
            ("Shiri & Falah-Hassani, 2015 — Computer/mouse meta-analysis",
             "10.1016/j.jns.2014.12.037"),
        ],
    },

    # ----- 2. Lower Back Pain ----------------------------------------
    "back_pain": {
        "name_en": "Lower-back pain (lumbar)",
        "name_gr": "Οσφυαλγία",
        "description": (
            "Lumbar strain from sustained seated posture and biomechanical "
            "overload. Strongly associated with sitting hours, BMI, age, and prior injury."
        ),
        "base_pct": 18.0,                               # adult point prevalence (high-income range 10-30%)
        "factors": {
            "bmi":               {"normal": 1.0, "overweight": 1.20, "obese": 1.50},
            "sitting_hours_high": 1.47,                                               # workplace sitting OR, Dzakpasu 2021
            "age_over_45":        1.30,
            "smoking_current":    1.30,                                               # consistently elevated risk
            "prior_injury":       1.80,                                               # recurrence common
        },
        "sources": [
            ("Dzakpasu et al., 2021 — Workplace sitting & MSP meta-analysis",
             "10.1186/s12966-021-01191-y"),
            ("GBD 2021 — Global Burden of LBP (628.8M cases globally)",
             "10.3389/fpubh.2024.1480779"),
        ],
    },

    # ----- 3. Neck pain / Cervical strain ----------------------------
    "neck_strain": {
        "name_en": "Cervical strain / forward-head posture syndrome",
        "name_gr": "Αυχενική κάκωση / σύνδρομο πρόσθιας θέσης κεφαλιού",
        "description": (
            "Sustained neck flexion or extension, often from monitor too high "
            "or too low. Highly prevalent in office workers."
        ),
        "base_pct": 27.0,                               # office-worker annual prevalence midpoint
        "factors": {
            "computer_hours_high":  1.92,                                            # ≥4 h/d
            "sitting_hours_high":   1.73,                                            # workplace sitting → neck/shoulder OR
            "sex_female":           1.95,
            "age_over_30":          2.61,
            "bmi":                 {"normal": 1.0, "overweight": 1.10, "obese": 1.20},
            "prior_injury":         1.40,
        },
        "sources": [
            ("GBD 2021 (Lancet Rheumatol 2024) — Global neck pain burden",
             "10.1016/S2665-9913(23)00321-1"),
            ("Dzakpasu et al., 2021 — Workplace sitting & neck pain",
             "10.1186/s12966-021-01191-y"),
        ],
    },

    # ----- 4. Rotator cuff disease -----------------------------------
    "tendinitis_shoulder": {
        "name_en": "Rotator cuff disease (tendinopathy / tear)",
        "name_gr": "Τενοντίτιδα — Πάθηση στροφικού πετάλου",
        "description": (
            "Tendinopathy or partial tear of rotator cuff tendons from "
            "sustained shoulder elevation, repetitive overhead reaching, or "
            "elevated BMI. Prevalence increases dramatically with age."
        ),
        "base_pct": 12.0,                              # midpoint for adults <60 yr
        "factors": {
            "bmi":              {"normal": 1.0, "overweight": 1.21, "obese": 1.44},  # Herzberg 2024
            "age_over_45":       2.00,                                               # age is dominant factor
            "age_over_60":       3.00,                                               # cumulative
            "prior_injury":      1.70,
            "sex_female":        1.10,
        },
        "sources": [
            ("Herzberg et al., 2024 — BMI & rotator cuff meta-analysis (17 studies pooled)",
             "10.1016/j.asmr.2024.100953"),
            ("Teunis et al., 2014 — Age-stratified prevalence pooled analysis",
             "10.1016/j.jse.2014.08.001"),
        ],
    },

    # ----- 5. Lateral epicondylitis (Tennis elbow) -------------------
    "epicondylitis_lat": {
        "name_en": "Lateral epicondylitis (tennis elbow)",
        "name_gr": "Επικονδυλίτιδα (tennis elbow)",
        "description": (
            "Pain at outer elbow from repetitive forearm load or excessive "
            "wrist extension. Note: BMI is NOT a significant risk factor "
            "(per recent meta-analyses); smoking and manual load are."
        ),
        "base_pct": 1.3,                              # general adult prevalence
        "factors": {
            "age_35_to_54":      2.30,                # peak age band
            "smoking_current":   1.40,                # consistently elevated risk
            "sex_female":        1.10,                # slight female predominance in office work
            "mouse_hours_high":  1.30,                # repetitive wrist extension
            "prior_injury":      1.60,
        },
        "sources": [
            ("Landesa-Piñeiro & Leirós-Rodríguez, 2022 — Prevalence 1-3% ages 35-54 (background citation, primary paper is on treatment)",
             "10.3233/BMR-210053"),
            ("Sayampanathan et al., 2020 — Risk factors meta-analysis",
             "10.1016/j.jse.2019.11.004"),
        ],
    },

    # NOTE: Obstructive Sleep Apnea removed 2026 — out of scope for an
    # office-ergonomics screening tool. OSA screening belongs in primary
    # care / sleep medicine, not ergonomic assessment.

    # ----- 6. Chronic venous insufficiency ---------------------------
    "venous_insufficiency": {
        "name_en": "Chronic venous insufficiency",
        "name_gr": "Χρόνια φλεβική ανεπάρκεια",
        "description": (
            "Impaired venous return from sustained sitting; venous valves "
            "overloaded; lower-limb edema, varicose veins. Risk multiplied "
            "by BMI, oral contraceptives, pregnancy."
        ),
        "base_pct": 12.0,
        "factors": {
            "bmi":                {"normal": 1.0, "overweight": 1.40, "obese": 1.90},
            "sitting_hours_high":  1.35,
            "sex_female":          1.40,
            "pregnancy":           1.80,
            "oral_contra":         1.30,
            "age_over_45":         1.60,
        },
        "sources": [
            ("Beebe-Dimmer et al., 2005 — Epidemiology of CVI (review)",
             "10.1016/j.annepidem.2004.05.015"),
        ],
    },

    # NOTE: Deep Vein Thrombosis (DVT) removed 2026 — out of scope for an
    # office-ergonomics screening tool. The 0.5% baseline came from a
    # narrative review (not systematic), and personalised DVT probability
    # is a clinical decision requiring haematology consultation.
}


# ====================================================================
# Multi-factor personal-risk estimator
# ====================================================================
def estimated_personal_pct(condition_key, ctx):
    """Compute an *indicative* personal percentage by multiplying the baseline
    prevalence by the applicable factor multipliers given the subject context.

    `ctx` is a dict with the following keys (all optional):
        bmi_band:        "normal" | "overweight" | "obese"
        sex:             "Female" | "Male" | "Combined average"
        age:             int years
        hours_computer:  float hours/day
        hours_mouse:     float hours/day
        hours_sitting:   float hours/day
        diabetes:        bool
        smoking:         "Never" | "Former" | "Current"
        injury_regions:  dict {region_name: bool} for body regions with prior injury
        pregnant:        bool   (effectively False if Male)
        oral_contra:     bool   (effectively False if Male)
    """
    """DEPRECATED — kept for backward compatibility. Use `elevated_factors`
    below. The multiplication of independently-derived odds ratios does
    NOT produce a valid individual probability estimate (Zhang & Yu 1998).
    """
    count, _ = elevated_factors(condition_key, ctx)
    return count


# ====================================================================
# FACTOR_EVIDENCE — verified ORs and 95% CIs from PubMed lookups.
# Populated Sept 2026 after adversarial re-audit (see /Tool Documentation).
# Keys: (condition_key, factor_key, sub_key or None) → (OR, CI_lo, CI_hi, source)
# CI = None means the CI is not available for that specific factor.
# ====================================================================
FACTOR_EVIDENCE = {
    # ---- Carpal Tunnel Syndrome ----
    ("cts", "bmi", "overweight"):  (1.47, 1.37, 1.57, "Shiri 2015 (10.1111/obr.12324)"),
    ("cts", "bmi", "obese"):       (2.02, 1.92, 2.13, "Shiri 2015 (10.1111/obr.12324)"),
    ("cts", "computer_hours_high"):(1.34, 1.08, 1.65, "Shiri & Falah-Hassani 2015 (10.1016/j.jns.2014.12.037)"),
    ("cts", "mouse_hours_high"):   (1.93, 1.43, 2.61, "Shiri & Falah-Hassani 2015"),
    ("cts", "sex_female"):         (1.40, None, None, "Multiple population studies"),
    ("cts", "diabetes"):           (2.00, None, None, "Pooled RR — Pourmemari 2016 (Diab Res Clin Pract)"),
    ("cts", "pregnancy"):          (2.50, None, None, "Multiple pregnancy CTS reviews"),
    ("cts", "prior_injury"):       (1.30, None, None, "Recurrence estimate"),
    # ---- Lower Back Pain ----
    ("back_pain", "bmi", "overweight"):  (1.20, None, None, "Shiri 2010 (Am J Epidemiol) pooled"),
    ("back_pain", "bmi", "obese"):       (1.50, None, None, "Shiri 2010"),
    ("back_pain", "sitting_hours_high"): (1.47, 1.12, 1.92, "Dzakpasu 2021 (10.1186/s12966-021-01191-y)"),
    ("back_pain", "age_over_45"):        (1.30, None, None, "GBD 2021 age gradient"),
    ("back_pain", "smoking_current"):    (1.30, None, None, "Shiri 2010 (smoking-LBP)"),
    ("back_pain", "prior_injury"):       (1.80, None, None, "Recurrence estimate"),
    # ---- Neck strain ----
    ("neck_strain", "computer_hours_high"): (1.92, None, None, "Kim 2018 office worker meta"),
    ("neck_strain", "sitting_hours_high"):  (1.73, 1.46, 2.03, "Dzakpasu 2021"),
    ("neck_strain", "sex_female"):          (1.95, None, None, "GBD 2021 sex-stratified"),
    ("neck_strain", "age_over_30"):         (2.61, None, None, "GBD 2021 age gradient"),
    ("neck_strain", "bmi", "overweight"):   (1.10, None, None, "Small pooled effect"),
    ("neck_strain", "bmi", "obese"):        (1.20, None, None, "Small pooled effect"),
    ("neck_strain", "prior_injury"):        (1.40, None, None, "Recurrence estimate"),
    # ---- Rotator cuff disease ----
    ("tendinitis_shoulder", "bmi", "overweight"): (1.21, 1.10, 1.34, "Herzberg 2024 (10.1016/j.asmr.2024.100953)"),
    ("tendinitis_shoulder", "bmi", "obese"):      (1.44, 1.32, 1.59, "Herzberg 2024"),
    ("tendinitis_shoulder", "age_over_45"):       (2.00, None, None, "Teunis 2014 (10.1016/j.jse.2014.08.001)"),
    ("tendinitis_shoulder", "age_over_60"):       (3.00, None, None, "Teunis 2014"),
    ("tendinitis_shoulder", "prior_injury"):      (1.70, None, None, "Recurrence estimate"),
    ("tendinitis_shoulder", "sex_female"):        (1.10, None, None, "Small pooled effect"),
    # ---- Lateral epicondylitis ----
    ("epicondylitis_lat", "age_35_to_54"):      (2.30, None, None, "Landesa-Piñeiro 2022 peak-age band"),
    ("epicondylitis_lat", "smoking_current"):   (1.40, None, None, "Sayampanathan 2020 (10.1016/j.jse.2019.11.004)"),
    ("epicondylitis_lat", "sex_female"):        (1.10, None, None, "Office-work subgroup"),
    ("epicondylitis_lat", "mouse_hours_high"):  (1.30, None, None, "Repetitive-load estimate"),
    ("epicondylitis_lat", "prior_injury"):      (1.60, None, None, "Recurrence estimate"),
    # ---- Chronic venous insufficiency ----
    ("venous_insufficiency", "bmi", "overweight"): (1.40, None, None, "Beebe-Dimmer 2005 pooled"),
    ("venous_insufficiency", "bmi", "obese"):      (1.90, None, None, "Beebe-Dimmer 2005"),
    ("venous_insufficiency", "sitting_hours_high"):(1.35, None, None, "Prolonged sitting estimate"),
    ("venous_insufficiency", "sex_female"):        (1.40, None, None, "Beebe-Dimmer 2005"),
    ("venous_insufficiency", "pregnancy"):         (1.80, None, None, "Beebe-Dimmer 2005"),
    ("venous_insufficiency", "oral_contra"):       (1.30, None, None, "Beebe-Dimmer 2005"),
    ("venous_insufficiency", "age_over_45"):       (1.60, None, None, "Beebe-Dimmer 2005"),
}


def _factor_tier(or_value):
    """Categorise a factor by effect-size magnitude.
    Weighted risk model (adversarial-review-driven):
        small (OR 1.00-1.29) → 1 point
        moderate (OR 1.30-1.79) → 2 points
        strong (OR ≥ 1.80) → 3 points
    """
    if or_value < 1.30:
        return ("small",    1, "#a3e635")   # lime
    if or_value < 1.80:
        return ("moderate", 2, "#f59e0b")   # amber
    return ("strong",   3, "#ef4444")       # red


def weighted_risk_analysis(condition_key, ctx):
    """Compute a weighted risk-factor analysis for one condition.

    Returns a dict with:
      - factors: list of dicts, each: {
            "label": str, "or": float, "ci": (lo, hi) or None,
            "tier": str, "points": int, "color": str, "source": str
        }
      - score: int (weighted sum of points)
      - score_max: theoretical maximum (used for %-of-max display)
      - category: "Low" | "Moderate" | "High"
      - category_color: hex color for the category badge
    """
    c = CONDITIONS[condition_key]
    f = c.get("factors", {})
    is_female = (ctx.get("sex") == "Female")
    is_male   = (ctx.get("sex") == "Male")
    age       = ctx.get("age", 35)
    factors_out = []

    def _add(label, or_value, ci, source):
        tier, pts, color = _factor_tier(or_value)
        factors_out.append({
            "label":  label, "or": or_value, "ci": ci,
            "tier":   tier, "points": pts, "color": color, "source": source,
        })

    def _ev(sub=None):
        """Return (OR, CI, source) from FACTOR_EVIDENCE or a safe default."""
        key = (condition_key, _current_factor, sub) if sub else (condition_key, _current_factor)
        info = FACTOR_EVIDENCE.get(key)
        if info is None:
            # Fallback: use the multiplier from the CONDITIONS dict
            fval = f.get(_current_factor)
            if isinstance(fval, dict) and sub is not None:
                return (fval.get(sub, 1.0), None, None, "internal reference")
            if isinstance(fval, (int, float)):
                return (fval, None, None, "internal reference")
            return (1.0, None, None, "unknown")
        return info

    # ---- BMI (with nuanced muscle-mass adjustment) --------------
    # BMI drives TWO different risk mechanisms:
    #   (A) MECHANICAL LOAD — spinal/joint compression, seat pressure.
    #       Applies to total body mass regardless of composition.
    #       Relevant conditions: back_pain, venous_insufficiency.
    #   (B) METABOLIC INFLAMMATION — visceral-fat-driven low-grade
    #       inflammation that mediates tendinopathy and nerve entrapment.
    #       Relevant conditions: cts, tendinitis_shoulder,
    #       epicondylitis_lat, neck_strain.
    # If the subject reports resistance-training hypertrophy, elevated
    # BMI likely reflects lean mass → the METABOLIC pathway (B) is
    # attenuated but the MECHANICAL pathway (A) still applies.
    # Reference: Prentice 2001 (Nutr Rev); Rothman 2008 (Int J Obes).
    _current_factor = "bmi"
    MECHANICAL_BMI_CONDITIONS = {"back_pain", "venous_insufficiency"}

    if "bmi" in f:
        band = ctx.get("bmi_band", "normal")
        if band != "normal":
            or_v, ci_lo, ci_hi, src = FACTOR_EVIDENCE.get(
                (condition_key, "bmi", band),
                (f["bmi"].get(band, 1.0), None, None, "internal"),
            )
            if or_v > 1.0:
                bmi_val = ctx.get("bmi_value")
                is_mechanical = condition_key in MECHANICAL_BMI_CONDITIONS
                hypertrophy   = ctx.get("muscle_hypertrophy", False)

                if hypertrophy and is_mechanical:
                    # Mechanical load still applies — full factor counted
                    tier, pts, color = _factor_tier(or_v)
                    factors_out.append({
                        "label": (
                            f"Elevated BMI ({band}, {bmi_val} kg/m²) — "
                            "MECHANICAL load still applies (body mass compresses "
                            "spine/joints regardless of composition). Metabolic "
                            "inflammation pathway is likely reduced due to "
                            "resistance-training hypertrophy."
                        ),
                        "or": or_v,
                        "ci": (ci_lo, ci_hi) if ci_lo else None,
                        "tier": tier, "points": pts, "color": color,
                        "source": src + " · mechanical-only interpretation (Prentice 2001)",
                    })
                elif hypertrophy and not is_mechanical:
                    # Metabolic pathway attenuated — factor reduced to
                    # ~50 % contribution (1 point instead of 2-3)
                    factors_out.append({
                        "label": (
                            f"Elevated BMI ({band}, {bmi_val} kg/m²) — "
                            "REDUCED WEIGHTING (½ pt) because the metabolic-"
                            "inflammation pathway that drives {c_name} risk "
                            "is attenuated in resistance-trained individuals "
                            "with muscle hypertrophy. Consider waist-to-hip "
                            "ratio for a cleaner signal."
                        ).replace("{c_name}", c["name_en"]),
                        "or": or_v,
                        "ci": (ci_lo, ci_hi) if ci_lo else None,
                        "tier": "small", "points": 1, "color": "#a3e635",
                        "source": src + " · attenuated-metabolic interpretation (Rothman 2008)",
                    })
                else:
                    # Standard: no hypertrophy adjustment
                    _add(
                        f"Elevated BMI ({band}, {bmi_val} kg/m²)",
                        or_v, (ci_lo, ci_hi) if ci_lo else None, src,
                    )

    # ---- Occupational exposure ---------------------------------
    def _try(factor_key, condition_met, label_fmt):
        if factor_key in f and condition_met:
            info = FACTOR_EVIDENCE.get((condition_key, factor_key))
            if info:
                or_v, ci_lo, ci_hi, src = info
                ci = (ci_lo, ci_hi) if ci_lo else None
                _add(label_fmt, or_v, ci, src)
            else:
                _add(label_fmt, f[factor_key] if isinstance(f[factor_key], (int, float)) else 1.0, None, "internal")

    _try("computer_hours_high", ctx.get("hours_computer", 0) >= 4,
         f"Prolonged computer use ({ctx.get('hours_computer')}h/day)")
    _try("mouse_hours_high",    ctx.get("hours_mouse", 0) >= 4,
         f"Prolonged mouse use ({ctx.get('hours_mouse')}h/day)")
    _try("sitting_hours_high",  ctx.get("hours_sitting", 0) >= 6,
         f"Prolonged workplace sitting ({ctx.get('hours_sitting')}h/day)")
    _try("sex_female", is_female, "Female sex (population-level association)")
    _try("sex_male",   is_male,   "Male sex (population-level association)")

    if "age_over_30" in f and age > 30:
        _try("age_over_30", True, f"Age > 30 ({age})")
    if "age_over_45" in f and age > 45:
        _try("age_over_45", True, f"Age > 45 ({age})")
    if "age_over_60" in f and age > 60:
        _try("age_over_60", True, f"Age > 60 ({age})")
    if "age_35_to_54" in f and 35 <= age <= 54:
        _try("age_35_to_54", True, f"Peak-incidence age band 35-54 ({age})")

    _try("diabetes",        ctx.get("diabetes", False),      "Diabetes mellitus")
    _try("smoking_current", ctx.get("smoking") == "Current", "Current smoker")

    if "prior_injury" in f:
        regions  = ctx.get("injury_regions", {}) or {}
        relevant = CONDITION_INJURY_REGIONS.get(condition_key, [])
        matching = [r for r in relevant if regions.get(r, False)]
        if matching:
            _try("prior_injury", True,
                 f"Prior injury/pain in relevant region(s): {', '.join(matching)}")

    if "pregnancy" in f and is_female and ctx.get("pregnant", False):
        _try("pregnancy", True, "Current pregnancy")
    if "oral_contra" in f and is_female and ctx.get("oral_contra", False):
        _try("oral_contra", True, "Oral contraceptive use")

    # ---- Modifiable-risk credits (protective factors) ----------
    # A very active person or good sleep/nutrition profile REDUCES
    # overall risk; this is reflected as a downward adjustment
    # (small negative points) rather than a hard-coded protective OR.
    # Never allow the score to go negative.
    protective_credit = 0
    protective_notes  = []
    if ctx.get("exercise_freq") in ("3-5x/week", "6+/week"):
        protective_credit -= 1
        protective_notes.append("Regular exercise (3+ sessions/week) — evidence for reduced MSK symptom incidence")
    if ctx.get("sleep_hours") in ("7-8h", "8-9h"):
        protective_credit -= 1
        protective_notes.append("Adequate sleep (7-9h) — evidence for lower musculoskeletal pain intensity")
    if ctx.get("diet_med") == "High":
        protective_credit -= 1
        protective_notes.append("High Mediterranean-diet adherence — anti-inflammatory effect")
    if ctx.get("non_work_pa_min", 0) >= 150:
        protective_credit -= 1
        protective_notes.append("Meets WHO PA guidelines (≥150 min/week moderate PA)")

    # ---- Compute weighted score ---------------------------------
    raw_score = sum(x["points"] for x in factors_out)
    score     = max(0, raw_score + protective_credit)
    n_avail   = sum(1 for k in f.keys() if k not in ("bmi",)) + (
        3 if "bmi" in f else 0  # bmi can contribute up to 3 pts (obese=strong)
    )
    # Theoretical max points if every factor was "strong" (3 pts each)
    score_max = 3 * len([k for k in f.keys() if k != "bmi"]) + (3 if "bmi" in f else 0)

    # Category tiers
    if score <= 2:
        category, cat_color = "Low", "#10b981"
    elif score <= 5:
        category, cat_color = "Moderate", "#f59e0b"
    else:
        category, cat_color = "High", "#ef4444"

    return {
        "factors":           factors_out,
        "score":             score,
        "raw_score":         raw_score,
        "protective_credit": protective_credit,
        "protective_notes":  protective_notes,
        "score_max":         score_max,
        "category":          category,
        "category_color":    cat_color,
    }


def elevated_factors(condition_key, ctx):
    """DEPRECATED — kept for backward compatibility with old summary code.
    Returns (count, [factor_labels]) — a naive unweighted count.
    Use `weighted_risk_analysis()` for the current tiered scoring.
    """
    c = CONDITIONS[condition_key]
    f = c.get("factors", {})
    factors_found = []

    # --- BMI ---------------------------------------------------------
    if "bmi" in f:
        band = ctx.get("bmi_band", "normal")
        if band != "normal" and f["bmi"].get(band, 1.0) > 1.0:
            bmi_val = ctx.get("bmi_value")
            label = f"Elevated BMI ({band}"
            if bmi_val is not None:
                label += f", {bmi_val} kg/m²"
            label += ")"
            factors_found.append(label)

    # --- Occupational exposure ---------------------------------------
    if "computer_hours_high" in f and ctx.get("hours_computer", 0) >= 4:
        factors_found.append(
            f"Prolonged computer use ({ctx.get('hours_computer')}h/day)"
        )
    if "mouse_hours_high" in f and ctx.get("hours_mouse", 0) >= 4:
        factors_found.append(
            f"Prolonged mouse use ({ctx.get('hours_mouse')}h/day)"
        )
    if "sitting_hours_high" in f and ctx.get("hours_sitting", 0) >= 6:
        factors_found.append(
            f"Prolonged sitting ({ctx.get('hours_sitting')}h/day)"
        )

    # --- Sex ---------------------------------------------------------
    if "sex_female" in f and ctx.get("sex") == "Female":
        factors_found.append("Female sex (population-level association)")
    if "sex_male"   in f and ctx.get("sex") == "Male":
        factors_found.append("Male sex (population-level association)")

    # --- Age ---------------------------------------------------------
    age = ctx.get("age", 35)
    if "age_over_30"  in f and age > 30: factors_found.append(f"Age > 30 ({age})")
    if "age_over_45"  in f and age > 45: factors_found.append(f"Age > 45 ({age})")
    if "age_over_60"  in f and age > 60: factors_found.append(f"Age > 60 ({age})")
    if "age_35_to_54" in f and 35 <= age <= 54:
        factors_found.append(f"Peak-incidence age band 35–54 ({age})")

    # --- Comorbidities & lifestyle -----------------------------------
    if "diabetes"        in f and ctx.get("diabetes", False):
        factors_found.append("Diabetes mellitus")
    if "smoking_current" in f and ctx.get("smoking") == "Current":
        factors_found.append("Current smoker")

    # --- Prior injury — region-specific ------------------------------
    if "prior_injury" in f:
        regions  = ctx.get("injury_regions", {}) or {}
        relevant = CONDITION_INJURY_REGIONS.get(condition_key, [])
        matching = [r for r in relevant if regions.get(r, False)]
        if matching:
            factors_found.append(
                f"Prior injury/pain in relevant region(s): {', '.join(matching)}"
            )

    # --- Female-only -------------------------------------------------
    is_female = (ctx.get("sex") == "Female")
    if "pregnancy"  in f and is_female and ctx.get("pregnant",   False):
        factors_found.append("Current pregnancy")
    if "oral_contra" in f and is_female and ctx.get("oral_contra", False):
        factors_found.append("Oral contraceptive use")

    return len(factors_found), factors_found


def risk_status(count):
    """Map factor count → qualitative category + color + label.
    Uses module-level `t` for translations (set from language selector).
    """
    if count == 0:
        return (t["risk_status_none"], "#10b981")
    if count <= 2:
        return (t["risk_status_some"], "#f59e0b")
    return (t["risk_status_many"], "#ef4444")


# ====================================================================
# ROSA — Rapid Office Strain Assessment
# Source: Sonne, Villalta & Andrews (2012), Applied Ergonomics 43:98-108
# Worksheet reference: TuMeke Ergonomics ROSA worksheet (public).
# ====================================================================

# --- Section A: Chair combination table (Y = A.1+A.2, X = A.3+A.4) ---
# Rows = Y (Chair-height + Pan-depth), Cols = X (Armrest + Back-support)
ROSA_CHAIR = {
    #      X: 2  3  4  5  6  7  8  9
    2:    [   1, 2, 3, 4, 5, 6, 7, 8 ],
    3:    [   2, 2, 3, 4, 5, 6, 7, 8 ],
    4:    [   3, 3, 3, 4, 5, 6, 7, 8 ],
    5:    [   4, 4, 4, 4, 5, 6, 7, 8 ],
    6:    [   5, 5, 5, 5, 6, 7, 8, 9 ],
    7:    [   6, 6, 6, 7, 7, 8, 8, 9 ],
    8:    [   7, 7, 7, 8, 8, 9, 9, 9 ],
}

# --- Section B: Monitor + Phone combination table ---
# Rows = B.2 (Phone), Cols = B.1 (Monitor)
ROSA_SECTION_B = {
    #      B.1:  0  1  2  3  4  5  6  7
    0:    [   1, 1, 1, 2, 3, 4, 5, 6 ],
    1:    [   1, 1, 2, 2, 3, 4, 5, 6 ],
    2:    [   1, 2, 2, 3, 3, 4, 6, 7 ],
    3:    [   2, 2, 3, 3, 4, 5, 6, 8 ],
    4:    [   3, 3, 4, 4, 5, 6, 7, 8 ],
    5:    [   4, 4, 5, 5, 6, 7, 8, 9 ],
    6:    [   5, 5, 6, 7, 8, 8, 9, 9 ],
}

# --- Section C: Mouse + Keyboard combination table ---
# Rows = C.2 (Keyboard), Cols = C.1 (Mouse)
ROSA_SECTION_C = {
    #      C.1:  0  1  2  3  4  5  6  7
    0:    [   1, 1, 1, 2, 3, 4, 5, 6 ],
    1:    [   1, 1, 2, 3, 4, 5, 6, 7 ],
    2:    [   1, 2, 2, 3, 4, 5, 6, 7 ],
    3:    [   2, 3, 3, 3, 5, 6, 7, 8 ],
    4:    [   3, 4, 4, 5, 5, 6, 7, 8 ],
    5:    [   4, 5, 5, 6, 6, 7, 8, 9 ],
    6:    [   5, 6, 6, 7, 7, 8, 8, 9 ],
    7:    [   6, 7, 7, 8, 8, 9, 9, 9 ],
}

# --- Monitor & Peripherals ROSA = Section B × Section C ---
# Rows = Section B, Cols = Section C
ROSA_MON_PERI = {
    #        C:  1  2  3  4  5  6  7  8  9
    1:    [   1, 2, 3, 4, 5, 6, 7, 8, 9 ],
    2:    [   2, 2, 3, 4, 5, 6, 7, 8, 9 ],
    3:    [   3, 3, 3, 4, 5, 6, 7, 8, 9 ],
    4:    [   4, 4, 4, 4, 5, 6, 7, 8, 9 ],
    5:    [   5, 5, 5, 5, 5, 6, 7, 8, 9 ],
    6:    [   6, 6, 6, 6, 6, 6, 7, 8, 9 ],
    7:    [   7, 7, 7, 7, 7, 7, 7, 8, 9 ],
    8:    [   8, 8, 8, 8, 8, 8, 8, 8, 9 ],
    9:    [   9, 9, 9, 9, 9, 9, 9, 9, 9 ],
}

# --- ROSA FINAL = Chair ROSA × Monitor & Peripherals ROSA ---
# Rows = Chair ROSA (1-10), Cols = Monitor & Peripherals ROSA (1-10)
ROSA_FINAL = {
    #        MP:  1  2  3  4  5  6  7  8  9 10
    1:    [   1, 2, 3, 4, 5, 6, 7, 8, 9, 10 ],
    2:    [   2, 2, 3, 4, 5, 6, 7, 8, 9, 10 ],
    3:    [   3, 3, 3, 4, 5, 6, 7, 8, 9, 10 ],
    4:    [   4, 4, 4, 4, 5, 6, 7, 8, 9, 10 ],
    5:    [   5, 5, 5, 5, 5, 6, 7, 8, 9, 10 ],
    6:    [   6, 6, 6, 6, 6, 6, 7, 8, 9, 10 ],
    7:    [   7, 7, 7, 7, 7, 7, 7, 8, 9, 10 ],
    8:    [   8, 8, 8, 8, 8, 8, 8, 8, 9, 10 ],
    9:    [   9, 9, 9, 9, 9, 9, 9, 9, 9, 10 ],
    10:   [  10,10,10,10,10,10,10,10,10, 10 ],
}


def _rosa_lookup(table, row, col, row_offset=None, col_offset=None):
    """Safe lookup with clamping to table bounds."""
    rows_available = sorted(table.keys())
    row_c = max(rows_available[0], min(rows_available[-1], row))
    cols_len = len(table[row_c])
    # Column index: shift if table has non-zero starting column
    if col_offset is None:
        col_offset = 0
    idx = max(0, min(cols_len - 1, col - col_offset))
    return table[row_c][idx]


def rosa_final_score(a1, a2, a3, a4, duration_chair,
                     b1, b2, duration_mon, duration_phone,
                     c1, c2, duration_mouse, duration_kbd):
    """Compute full ROSA score from sub-component scores.

    Each sub-score (a1..c2) is the raw sum of "1 + adjustments"
    already computed from the user's checkbox selections.
    Duration values are -1, 0, or +1.

    Returns a dict with chair, mon_peri, final scores and action level.
    """
    # --- Section A: Chair ---
    y_axis = a1 + a2                          # Chair height + Pan depth
    x_axis = a3 + a4                          # Armrests + Back support
    chair_raw = _rosa_lookup(
        ROSA_CHAIR, row=y_axis, col=x_axis,
        col_offset=2,       # X axis starts at 2
    )
    chair_rosa = max(1, min(10, chair_raw + duration_chair))

    # --- Section B: Monitor + Phone ---
    b1_score = max(0, b1 + duration_mon)
    b2_score = max(0, b2 + duration_phone)
    section_b = _rosa_lookup(ROSA_SECTION_B, row=b2_score, col=b1_score,
                             col_offset=0)

    # --- Section C: Mouse + Keyboard ---
    c1_score = max(0, c1 + duration_mouse)
    c2_score = max(0, c2 + duration_kbd)
    section_c = _rosa_lookup(ROSA_SECTION_C, row=c2_score, col=c1_score,
                             col_offset=0)

    # --- Monitor & Peripherals ROSA ---
    mon_peri = _rosa_lookup(ROSA_MON_PERI, row=section_b, col=section_c,
                            col_offset=1)

    # --- ROSA FINAL ---
    final = _rosa_lookup(ROSA_FINAL, row=chair_rosa, col=mon_peri,
                         col_offset=1)

    # Action level per Sonne 2012
    if final <= 2:
        action, action_color = "Low risk — no further assessment required", "#10b981"
    elif final <= 4:
        action, action_color = "Moderate — reassess in 6 months", "#f59e0b"
    else:
        action, action_color = "High risk — immediate intervention needed", "#ef4444"

    return {
        "chair_rosa":  chair_rosa,
        "section_b":   section_b,
        "section_c":   section_c,
        "mon_peri":    mon_peri,
        "final":       final,
        "action":      action,
        "action_color":action_color,
    }


def compute_risk_profile(chair_diff, desk_diff, monitor_diff,
                         osha_pct, angle_results, n_total_osha,
                         ctx):
    """Map current assessment findings to evidence-linked conditions.

    Returns: list of (risk_factor_label, [condition_keys]) tuples.
    """
    profile = []
    bmi_band  = ctx.get("bmi_band", "normal")
    bmi_value = ctx.get("bmi_value")
    bmi_label = f" (BMI {bmi_value})" if bmi_value is not None else ""

    # --- Workstation height issues -----------------------------------
    if desk_diff > 2:
        profile.append((
            f"Desk too high ({desk_diff:+.1f} cm) — wrist extension, shoulder elevation, "
            "repetitive finger strain during typing",
            ["cts", "tendinitis_shoulder", "epicondylitis_lat"],
        ))
    elif desk_diff < -2:
        profile.append((
            f"Desk too low ({desk_diff:+.1f} cm) — sustained spinal flexion, hunching",
            ["back_pain", "neck_strain"],
        ))

    if chair_diff < -2:
        profile.append((
            f"Chair too low ({chair_diff:+.1f} cm) — knees above hips, increased lumbar load",
            ["back_pain"],
        ))
    elif chair_diff > 2:
        profile.append((
            f"Chair too high ({chair_diff:+.1f} cm) — feet unsupported, thigh compression",
            ["back_pain", "venous_insufficiency"],
        ))

    if monitor_diff > 4:
        profile.append((
            f"Monitor too high ({monitor_diff:+.1f} cm) — neck extension, upward gaze",
            ["neck_strain"],
        ))
    elif monitor_diff < -4:
        profile.append((
            f"Monitor too low ({monitor_diff:+.1f} cm) — forward head posture, neck flexion",
            ["neck_strain", "back_pain"],
        ))

    # --- Chair compliance --------------------------------------------
    if osha_pct < 0.6:
        profile.append((
            f"Chair fails > 40% of EN 1335 / ISO 9241-5 design criteria — overall poor seating",
            ["back_pain", "neck_strain"],
        ))

    # --- Joint angles ------------------------------------------------
    for label, (status, val, (lo, hi)) in angle_results.items():
        if status != "warn":
            continue
        if "Κορμός" in label:
            profile.append((
                f"Trunk posture out of range — {label} ({val}°)",
                ["back_pain"],
            ))
        elif "Βραχίονας" in label:
            profile.append((
                f"Arm posture out of range — {label} ({val}°)",
                ["tendinitis_shoulder", "epicondylitis_lat", "neck_strain"],
            ))

    # --- Occupational exposure (independent of workstation geometry) -
    if ctx.get("hours_computer", 0) >= 4:
        profile.append((
            f"Heavy computer exposure ({ctx['hours_computer']:.1f} h/day) — "
            "elevated risk for upper-limb and neck disorders",
            ["cts", "neck_strain"],
        ))
    if ctx.get("hours_mouse", 0) >= 4:
        profile.append((
            f"Heavy mouse use ({ctx['hours_mouse']:.1f} h/day) — repetitive wrist load",
            ["cts", "epicondylitis_lat"],
        ))
    if ctx.get("hours_sitting", 0) >= 8:
        profile.append((
            f"Prolonged sitting ({ctx['hours_sitting']:.1f} h/day) — "
            "circulatory stagnation, lumbar load, neck strain",
            ["back_pain", "neck_strain", "venous_insufficiency"],
        ))

    # --- Comorbidities & lifestyle -----------------------------------
    if ctx.get("diabetes", False):
        profile.append((
            "Diabetes mellitus — multiplies upper-limb tendinopathy and CTS risk",
            ["cts"],
        ))
    if ctx.get("smoking") == "Current":
        profile.append((
            "Current smoking — elevates LBP and tendinopathy risk",
            ["back_pain", "epicondylitis_lat"],
        ))
    # Region-specific prior injuries
    regions = ctx.get("injury_regions", {}) or {}
    region_to_label_conds = {
        "neck":     ("Prior neck injury — recurrence and chronic neck-pain risk",
                     ["neck_strain"]),
        "shoulder": ("Prior shoulder injury — elevated rotator-cuff disease risk",
                     ["tendinitis_shoulder"]),
        "elbow":    ("Prior elbow injury — elevated tennis-elbow risk",
                     ["epicondylitis_lat"]),
        "wrist":    ("Prior wrist / hand injury — elevated CTS risk",
                     ["cts"]),
        "back":     ("Prior lower-back injury — elevated chronic LBP risk",
                     ["back_pain"]),
        "leg":      ("Prior leg / lower-extremity injury — elevated venous risk",
                     ["venous_insufficiency"]),
    }
    for region, (label, conds) in region_to_label_conds.items():
        if regions.get(region, False):
            profile.append((label, conds))

    # --- Female-only ------------------------------------------------
    if ctx.get("sex") == "Female":
        if ctx.get("pregnant", False):
            profile.append((
                "Pregnancy — elevated CTS, de Quervain, and venous insufficiency risk",
                ["cts", "venous_insufficiency"],
            ))
        if ctx.get("oral_contra", False):
            profile.append((
                "Oral contraceptive use — combined with prolonged sitting elevates venous risk",
                ["venous_insufficiency"],
            ))

    # --- BMI-related risk factors ------------------------------------
    if bmi_band == "overweight":
        profile.append((
            f"Overweight body composition{bmi_label} — elevated load on spine, joints, wrists",
            ["back_pain", "cts", "tendinitis_shoulder", "venous_insufficiency"],
        ))
    elif bmi_band == "obese":
        profile.append((
            f"Obese body composition{bmi_label} — substantially elevated load on spine, joints, circulatory system",
            ["back_pain", "cts", "tendinitis_shoulder", "venous_insufficiency"],
        ))

    # --- Psychosocial (Karasek Job Demand-Control-Support) -----------
    # High demand + low control ("job strain") is independently associated
    # with MSK disorders — see Landsbergis 2020, Nguyen 2023.
    ps_demand  = ctx.get("psy_demand",  "Moderate")
    ps_control = ctx.get("psy_control", "Moderate")
    ps_support = ctx.get("psy_support", "Moderate")
    if ps_demand == "High" and ps_control == "Low":
        profile.append((
            "**Job strain** (high demand + low control) — independently linked "
            "to elevated musculoskeletal symptom risk",
            ["back_pain", "neck_strain"],
        ))
    if ps_support == "Low":
        profile.append((
            "Low workplace social support — additive risk factor for MSK "
            "symptoms per Karasek Iso-Strain model",
            ["back_pain", "neck_strain"],
        ))

    return profile


# ====================================================================
# Tabs — wrapped in a green "assessment sections" panel
# ====================================================================
st.markdown(
    f"""
    <div class="tabs-divider">
        <span class="brand-dot"></span>
        <span>{t["sections_label"]}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_ideal, tab_assessment, tab_osha, tab_angles, tab_rosa, tab_summary = st.tabs([
    t["tab_1"], t["tab_2"], t["tab_3"], t["tab_4"], t["tab_rosa"], t["tab_5"],
])


# --------------------------------------------------------------------
# Tab 1 — Ideal Workstation Setup (reference targets only)
# --------------------------------------------------------------------
with tab_ideal:
    st.subheader("Ideal — Proposed Workstation Setup")
    st.caption(
        "Results are computed based on the personal data you provided "
        "and standard anthropometric reference data."
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Ideal chair seat",  f"{ideal_chair} cm")
    m2.metric("Ideal desk height", f"{ideal_desk_target} cm")
    m3.metric("Ideal monitor top", f"{ideal_mon_target} cm")

    st.markdown("")
    st.markdown(
        "*Chair seat = popliteal height (back of knee). "
        "Desk = chair seat + seated elbow rest. "
        "Monitor top = chair seat + seated eye height.*"
    )


# --------------------------------------------------------------------
# Tab 2 — Workstation Assessment (measured + per-item evaluation)
# --------------------------------------------------------------------
with tab_assessment:
    st.subheader("Measured workstation")
    st.caption("Enter the actual measurements of your current workstation.")

    chair_height = st.selectbox(
        "Chair seat height — floor to top of seat (cm)",
        options=list(range(35, 71)), index=10,
    )
    desk_height = st.selectbox(
        "Desk height — floor to top of desk (cm)",
        options=list(range(55, 121)), index=20,
    )
    monitor_height = st.selectbox(
        "Monitor top-edge height — floor to top of screen (cm)",
        options=list(range(60, 181)), index=60,
    )

    desk_for_actual_chair    = round(chair_height + seated_elbow_gap, 1)
    # Monitor top ideal = eye level MINUS the 5 cm safety margin
    # (top of screen should sit at-or-below eye level, never above).
    monitor_for_actual_chair = round(
        chair_height + seated_eye_gap - EYE_TO_MON_TOP_OFFSET_CM, 1
    )

    chair_diff   = chair_height   - ideal_chair
    desk_diff    = desk_height    - desk_for_actual_chair
    monitor_diff = monitor_height - monitor_for_actual_chair

    st.divider()

    eval_col, vis_col = st.columns([3, 2], gap="large")

    # ============================================================
    # LEFT — per-item evaluation
    # ============================================================
    with eval_col:
        st.subheader("Per-item evaluation")

        # --- 1. Chair seat ---------------------------------------
        st.markdown("**1. Chair seat height**")
        st.write(f"Target: **{ideal_chair} cm** — measured: **{chair_height} cm** "
                 f"(Δ {chair_diff:+.1f} cm)")
        st.caption(
            "**Tolerance ±2 cm** — the chair is considered ergonomically OK if "
            "the difference (Δ) between measured and target seat height is within "
            "±2 cm. Δ refers to *measured − target*."
        )
        if abs(chair_diff) <= 2:
            st.success("Within comfortable range.")
        elif chair_diff > 2:
            st.warning("Chair too HIGH — feet dangle, pressure under thighs, reduced circulation.")
        else:
            st.warning("Chair too LOW — knees rise above hips, lower-back load increases.")

        st.markdown("")

        # --- 2. Desk ---------------------------------------------
        st.markdown("**2. Desk height**")
        st.write(f"For *current* chair: **{desk_for_actual_chair} cm** — measured: "
                 f"**{desk_height} cm** (Δ {desk_diff:+.1f} cm)")
        st.write(f"For *ideal* chair: **{ideal_desk_target} cm**")
        st.caption(
            "**Tolerance ±2 cm** — desk is OK if the difference between measured "
            "and *for-current-chair* target is within ±2 cm. Δ = measured − target."
        )
        if abs(desk_diff) <= 2:
            st.success("Well-matched to current chair.")
        elif desk_diff > 2:
            st.warning("Desk too HIGH — shoulder shrugging, wrist extension, upper-trap tension.")
        else:
            st.warning("Desk too LOW — hunching forward, lower-back fatigue.")

        st.markdown("")

        # --- 3. Monitor ------------------------------------------
        st.markdown("**3. Monitor top-edge height**")
        st.write(f"For *current* chair: **{monitor_for_actual_chair} cm** — measured: "
                 f"**{monitor_height} cm** (Δ {monitor_diff:+.1f} cm)")
        st.write(f"For *ideal* chair: **{ideal_mon_target} cm**")
        st.caption(
            "**Tolerance ±4 cm** — monitor is OK if the difference between measured "
            "and *for-current-chair* target is within ±4 cm. The tolerance here is "
            "wider than chair/desk because head/eye position is naturally adjustable."
        )
        if abs(monitor_diff) <= 4:
            st.success("Well placed.")
        elif monitor_diff > 4:
            st.warning("Monitor too HIGH — neck extension, dry-eye, upper-trap tension.")
        else:
            st.warning("Monitor too LOW — forward head posture, neck flexion, upper-back strain.")

    # ============================================================
    # RIGHT — live posture visualization
    # ============================================================
    with vis_col:
        st.subheader("Live posture preview")
        st.caption(
            "Side-view of your current setup. Body is scaled to your stature "
            "and weight; chair, desk and monitor are drawn at their measured "
            "heights. Green = within tolerance · amber = mild deviation · red = significant."
        )
        _svg_markup = render_posture_svg(
            stature_cm=height,
            weight_kg=weight,
            chair_h=chair_height,
            desk_h=desk_height,
            monitor_h=monitor_height,
            chair_diff=chair_diff,
            desk_diff=desk_diff,
            monitor_diff=monitor_diff,
        )
        # Encode as data URI so Streamlit's markdown sanitizer keeps it intact
        _svg_b64 = base64.b64encode(_svg_markup.encode("utf-8")).decode("ascii")
        st.markdown(
            f'<img src="data:image/svg+xml;base64,{_svg_b64}" '
            f'alt="posture preview" style="width:100%; height:auto; '
            f'border:1px solid #99f6e4; border-radius:14px; background:#f0fdfa;"/>',
            unsafe_allow_html=True,
        )


# --------------------------------------------------------------------
# Tab 2 — OSHA chair design checklist
# --------------------------------------------------------------------
with tab_osha:
    st.subheader(t["chair_tab_head"])
    st.caption(t["chair_tab_cap"])

    # Bilingual chair checklist items (EN 1335 / ISO 9241-5 based).
    # Each item = (key, {"el": Greek label, "en": English label})
    _CHAIR_ITEMS_BILINGUAL = [
        ("adjust", {
            "el": "Παρέχει εύκολες ρυθμίσεις",
            "en": "Provides easy adjustments",
        }),
        ("back_tilt", {
            "el": "Κλίση πλάτης ρυθμιζόμενη (συνιστώμενο εύρος 90°–120°)",
            "en": "Backrest tilt is adjustable (recommended range 90°–120°)",
        }),
        ("back_lock", {
            "el": "Η πλάτη σταθεροποιείται σε κάθε επιλεγμένη θέση",
            "en": "Backrest locks in any selected position",
        }),
        ("back_height", {
            "el": "Το ύψος της πλάτης είναι κατάλληλο (EN 1335: χαμηλή ≤ 40 cm, μεσαία ≤ 50 cm, υψηλή > 50 cm — μετρημένο από την έδρα προς τα πάνω)",
            "en": "Backrest height is appropriate (EN 1335: low ≤ 40 cm, medium ≤ 50 cm, high > 50 cm — measured from seat upward)",
        }),
        ("back_width", {
            "el": "Το πλάτος της πλάτης της καρέκλας είναι ≥ 31 cm",
            "en": "Backrest width is ≥ 31 cm",
        }),
        ("lumbar", {
            "el": "Η πλάτη της καρέκλας υποστηρίζει την φυσική κυρτότητα της οσφυϊκής χώρας (lumbar support)",
            "en": "The backrest supports the natural lumbar curvature (lumbar support)",
        }),
        ("back_angle", {
            "el": "Η γωνία μεταξύ καθίσματος και πλάτης της καρέκλας είναι 90°–120°",
            "en": "The seat-to-backrest angle is 90°–120°",
        }),
        ("rounded", {
            "el": "Τα άκρα της πλάτης και της έδρας είναι περιμετρικά στρογγυλεμένα",
            "en": "Backrest and seat edges are rounded all around",
        }),
        ("seat_height", {
            "el": "Το ύψος της έδρας είναι ρυθμιζόμενο (EN 1335-1: 40–51 cm από το έδαφος)",
            "en": "Seat height is adjustable (EN 1335-1: 40–51 cm from the floor)",
        }),
        ("seat_depth", {
            "el": "Το βάθος της έδρας είναι ρυθμιζόμενο (συνιστώμενο εύρος 38–45 cm)",
            "en": "Seat depth is adjustable (recommended range 38–45 cm)",
        }),
        ("seat_width", {
            "el": "Το πλάτος της έδρας είναι ≥ 45 cm",
            "en": "Seat width is ≥ 45 cm",
        }),
        ("seat_tilt", {
            "el": "Η έδρα έχει κλίση 0°–7° σε σχέση με το οριζόντιο επίπεδο",
            "en": "The seat has a 0°–7° tilt relative to horizontal",
        }),
        ("seat_front", {
            "el": "Το μπροστινό μέρος της έδρας έχει ελαφριά κλίση και είναι στρογγυλεμένο (waterfall type)",
            "en": "The front edge of the seat is slightly inclined and rounded (waterfall design)",
        }),
        ("seat_concave", {
            "el": "Η επιφάνεια της έδρας έχει ελαφρύ κοίλωμα για ομοιόμορφη στήριξη",
            "en": "The seat surface has a slight concavity for even support",
        }),
        ("seat_elastic", {
            "el": "Το υλικό της έδρας και της πλάτης έχει κατάλληλη ελαστικότητα (cushioning)",
            "en": "The seat and backrest material has appropriate cushioning",
        }),
        ("seat_fabric", {
            "el": "Επένδυση ανθεκτική, μη ολισθηρή, υδατοδιαπερατή (αναπνέει)",
            "en": "Upholstery is durable, non-slip, and breathable",
        }),
        ("arm_height", {
            "el": "Το ύψος των υποβραχιόνιων ρυθμίζεται (αποδεκτό ~25 cm από την έδρα)",
            "en": "Armrest height is adjustable (typical ~25 cm above the seat)",
        }),
        ("arm_distance", {
            "el": "Η απόσταση μεταξύ των δύο υποβραχιόνιων ρυθμίζεται (> 40 cm)",
            "en": "The distance between the two armrests is adjustable (> 40 cm)",
        }),
        ("arm_width", {
            "el": "Πλάτος υποβραχιόνων ≥ 5 cm",
            "en": "Armrest width is ≥ 5 cm",
        }),
        ("base", {
            "el": "Βάση με ≥ 5 ακτίνες, ροδάκια απρόσκοπτης κύλισης",
            "en": "5-star base with smooth-rolling casters",
        }),
        ("swivel", {
            "el": "Το κάθισμα περιστρέφεται περί του άξονά του (swivel)",
            "en": "The seat rotates freely around its central axis (swivel)",
        }),
    ]

    # Build the display list using the currently selected language.
    OSHA_ITEMS = [(key, labels[lang]) for key, labels in _CHAIR_ITEMS_BILINGUAL]

    osha_results = {}
    half = (len(OSHA_ITEMS) + 1) // 2
    cA, cB = st.columns(2)
    for i, (key, label) in enumerate(OSHA_ITEMS):
        target_col = cA if i < half else cB
        with target_col:
            osha_results[label] = st.checkbox(label, key=f"osha_{key}")

    st.divider()
    n_pass  = sum(osha_results.values())
    n_total = len(OSHA_ITEMS)
    pct     = n_pass / n_total

    st.metric(t["chair_score"], f"{n_pass} / {n_total}",
              delta=f"{pct*100:.0f}%")

    if pct == 1.0:
        st.success("Όλα τα κριτήρια πληρούνται.")
    elif pct >= 0.85:
        st.info(f"{n_pass}/{n_total} OK — μικρές ελλείψεις.")
    elif pct >= 0.60:
        st.warning(f"{n_pass}/{n_total} OK — σημαντικές ελλείψεις, χρειάζεται παρέμβαση.")
    else:
        st.error(f"Μόνο {n_pass}/{n_total} OK — η καρέκλα δεν είναι κατάλληλη για παρατεταμένη χρήση.")

    failed = [label for label, ok in osha_results.items() if not ok]
    if failed:
        with st.expander(f"Items not satisfied ({len(failed)})", expanded=False):
            for item in failed:
                st.write(f"- {item}")


# --------------------------------------------------------------------
# Tab 3 — Joint comfort angles
# --------------------------------------------------------------------
with tab_angles:
    st.subheader(t["angles_tab_head"])
    st.caption(t["angles_tab_cap"])

    JOINT_ITEMS = [
        ("trunk_vert",     "1. Κορμός — κατακόρυφος άξονας (γωνία κλίσης κορμού)",                     10,  20, 15),
        ("trunk_thigh",    "2. Κορμός — μηρός (γωνία ισχίου)",                                         90, 110, 100),
        ("thigh_shin",     "3. Μηρός — κνήμη (γωνία γόνατος)",                                         95, 120, 105),
        ("shin_foot",      "4. Κνήμη — πέλμα (γωνία ποδοκνημικής)",                                    90, 110, 100),
        ("upper_frontal",  "5. Βραχίονας — κατακόρυφος, μετωπιαίο επίπεδο (απαγωγή ώμου)",              0,  30, 10),
        ("upper_sagittal", "6. Βραχίονας — κατακόρυφος, προσθοπίσθιο επίπεδο (κάμψη ώμου)",            10,  35, 20),
        ("upper_lower",    "7. Βραχίονας — αντιβράχιο (γωνία αγκώνα, ISO 11226 / RULA)",              90, 120, 100),
        # Added 2026 — wrist assessment was missing per adversarial peer review.
        # Ranges: ISO 11226 & Occupational Biomechanics (Chaffin et al.).
        ("wrist_ext",      "8. Καρπός — έκταση/κάμψη (0° = ουδέτερο, θετικό = έκταση)",              -15,  15, 0),
        ("wrist_uln",      "9. Καρπός — ωλένια απόκλιση (0° = ουδέτερο)",                            -10,  15, 5),
    ]

    angle_results = {}
    for key, label, lo, hi, default in JOINT_ITEMS:
        c_label, c_input, c_status = st.columns([3, 1, 2])
        with c_label:
            st.write(f"**{label}**")
            st.caption(f"Comfort range: {lo}° – {hi}°")
        with c_input:
            # Wrist angles allow negative values (flexion / radial deviation)
            _min = -30 if key.startswith("wrist") else 0
            angle = st.number_input(
                "Angle (°)",
                min_value=_min, max_value=180, value=default, step=5,
                key=f"angle_{key}",
                label_visibility="collapsed",
            )
        with c_status:
            if lo <= angle <= hi:
                st.success(f"✓ {angle}° — within range")
                angle_results[label] = ("ok", angle, (lo, hi))
            else:
                st.warning(f"✗ {angle}° — outside {lo}°–{hi}°")
                angle_results[label] = ("warn", angle, (lo, hi))

    st.divider()
    n_ok = sum(1 for v in angle_results.values() if v[0] == "ok")
    n_total_angles = len(angle_results)
    st.metric(t["angles_score"], f"{n_ok} / {n_total_angles}")

    if n_ok < n_total_angles:
        with st.expander(t["angles_out"], expanded=False):
            for label, (status, val, (lo, hi)) in angle_results.items():
                if status == "warn":
                    st.write(f"- {label}: **{val}°** (target {lo}°–{hi}°)")


# --------------------------------------------------------------------
# Tab 5 — ROSA Assessment (validated instrument, ergonomist-only)
# --------------------------------------------------------------------
with tab_rosa:
    st.subheader(t["rosa_title"])
    st.caption(t["rosa_intro"])
    st.info(t["rosa_check_all"])

    # Bilingual option labels for ROSA sub-items
    _ROSA_L = {
        "el": {
            # A.1 Chair height
            "a1_base":   "Γόνατα σε 90° (βασικό, δεν προσθέτει)",
            "a1_low":    "Πολύ χαμηλή (γόνατο <90°) +2",
            "a1_high":   "Πολύ ψηλή (γόνατο >90°) +2",
            "a1_nofoot": "Τα πέλματα δεν πατούν στο έδαφος +3",
            "a1_cramp":  "Δεν χωράνε τα πόδια κάτω από το γραφείο +1",
            "a1_nonadj": "Μη ρυθμιζόμενη +1",
            # A.2 Pan depth
            "a2_base":   "~3 δάχτυλα χώρος πίσω από το γόνατο (βασικό)",
            "a2_long":   "Πολύ μακρύ βάθος έδρας (<3 δάχτυλα χώρος) +2",
            "a2_short":  "Πολύ κοντό βάθος έδρας (>3 δάχτυλα χώρος) +2",
            "a2_nonadj": "Μη ρυθμιζόμενο +1",
            # A.3 Armrests
            "a3_base":   "Αγκώνες στηριγμένοι, στη σειρά με ώμο, ώμοι χαλαροί (βασικό)",
            "a3_high":   "Πολύ ψηλά (ώμοι σηκωμένοι) ή χαμηλά (χωρίς στήριξη) +2",
            "a3_hard":   "Σκληρή/κατεστραμμένη επιφάνεια +1",
            "a3_wide":   "Πολύ μακριά μεταξύ τους +1",
            "a3_nonadj": "Μη ρυθμιζόμενα +1",
            # A.4 Back support
            "a4_base":   "Καλή στήριξη οσφύος, κλίση 95°–110° (βασικό)",
            "a4_nolumb": "Δεν υπάρχει lumbar support ή είναι σε λάθος θέση +2",
            "a4_angle":  "Πλάτη κεκλιμένη >110° ή <95° +2",
            "a4_noback": "Χωρίς πλάτη (σκαμπό) ή κύψη προς τα εμπρός +3",
            "a4_hidesk": "Επιφάνεια εργασίας πολύ ψηλή (ώμοι σηκωμένοι) +1",
            "a4_nonadj": "Πλάτη μη ρυθμιζόμενη +1",
            # B.1 Monitor
            "b1_base":   "Απόσταση μπράτσου (40–75 cm), στο ύψος ματιών (βασικό)",
            "b1_low":    "Πολύ χαμηλά (>30° κάτω) +2",
            "b1_far":    "Πολύ μακριά +1",
            "b1_high":   "Πολύ ψηλά (έκταση αυχένα) +3",
            "b1_twist":  "Στροφή αυχένα >30° +1",
            "b1_glare":  "Αντανάκλαση στην οθόνη +1",
            "b1_docs":   "Έγγραφα χωρίς βάση/document holder +1",
            # B.2 Phone
            "b2_base":   "Headset ή ένα χέρι + ουδέτερη στάση αυχένα (βασικό)",
            "b2_far":    "Πολύ μακριά (πάνω από 30 cm) +2",
            "b2_hold":   "Το κρατά ανάμεσα σε αυχένα και ώμο +2",
            "b2_nohnd":  "Χωρίς hands-free επιλογή +1",
            # C.1 Mouse
            "c1_base":   "Ποντίκι στη σειρά με τον ώμο (βασικό)",
            "c1_reach":  "Πρέπει να τεντώνεται για να το φτάσει +2",
            "c1_diff":   "Ποντίκι/πληκτρολόγιο σε διαφορετικές επιφάνειες +2",
            "c1_pinch":  "Πιάσιμο με τσιμπίδα (pinch grip) +1",
            "c1_palm":   "Palmrest μπροστά από το ποντίκι +1",
            # C.2 Keyboard
            "c2_base":   "Καρποί ίσιοι, ώμοι χαλαροί (βασικό)",
            "c2_ext":    "Καρποί σε έκταση >15° / πληκτρολόγιο σε θετική γωνία +2",
            "c2_dev":    "Ωλένια/κερκιδική απόκλιση κατά την πληκτρολόγηση +1",
            "c2_hi":     "Πληκτρολόγιο πολύ ψηλά — ώμοι σηκωμένοι +1",
            "c2_over":   "Πρέπει να τεντώνεται για overhead αντικείμενα +1",
            "c2_nonadj": "Πλατφόρμα μη ρυθμιζόμενη +1",
        },
        "en": {
            "a1_base":   "Knees at 90° (base, no addition)",
            "a1_low":    "Too low (knee angle <90°) +2",
            "a1_high":   "Too high (knee angle >90°) +2",
            "a1_nofoot": "No foot contact on ground +3",
            "a1_cramp":  "Insufficient space under desk (can't cross legs) +1",
            "a1_nonadj": "Non-adjustable +1",
            "a2_base":   "~3 inches (about 8 cm) space behind knee (base)",
            "a2_long":   "Pan too long (<3 inches space) +2",
            "a2_short":  "Pan too short (>3 inches space) +2",
            "a2_nonadj": "Non-adjustable +1",
            "a3_base":   "Elbows supported, in line with shoulder, shoulders relaxed (base)",
            "a3_high":   "Too high (shoulders shrugged) or low (arms unsupported) +2",
            "a3_hard":   "Hard / damaged surface +1",
            "a3_wide":   "Too wide apart +1",
            "a3_nonadj": "Non-adjustable +1",
            "a4_base":   "Adequate lumbar support, chair reclined 95°–110° (base)",
            "a4_nolumb": "No lumbar support OR support not in small of back +2",
            "a4_angle":  "Angled too far back (>110°) or forward (<95°) +2",
            "a4_noback": "No back support (stool) or leaning forward +3",
            "a4_hidesk": "Work surface too high (shoulders shrugged) +1",
            "a4_nonadj": "Back rest non-adjustable +1",
            "b1_base":   "Arm's-length distance (40–75 cm), screen at eye level (base)",
            "b1_low":    "Too low (below 30°) +2",
            "b1_far":    "Too far +1",
            "b1_high":   "Too high (neck extension) +3",
            "b1_twist":  "Neck twist greater than 30° +1",
            "b1_glare":  "Glare on screen +1",
            "b1_docs":   "Documents without holder +1",
            "b2_base":   "Headset or one hand on phone + neutral neck posture (base)",
            "b2_far":    "Too far of reach (outside 30 cm) +2",
            "b2_hold":   "Neck and shoulder hold +2",
            "b2_nohnd":  "No hands-free options +1",
            "c1_base":   "Mouse in line with shoulder (base)",
            "c1_reach":  "Reaching to mouse +2",
            "c1_diff":   "Mouse/keyboard on different surfaces +2",
            "c1_pinch":  "Pinch grip on mouse +1",
            "c1_palm":   "Palmrest in front of mouse +1",
            "c2_base":   "Wrists straight, shoulders relaxed (base)",
            "c2_ext":    "Wrists extended / keyboard on positive angle (>15° wrist ext.) +2",
            "c2_dev":    "Deviation while typing +1",
            "c2_hi":     "Keyboard too high — shoulders shrugged +1",
            "c2_over":   "Reaching to overhead items +1",
            "c2_nonadj": "Platform non-adjustable +1",
        },
    }
    L = _ROSA_L[lang]

    def _rosa_checkbox(label, points, key):
        return points if st.checkbox(label, key=key) else 0

    def _duration_selector(key):
        choice = st.radio(
            t["rosa_duration"],
            options=[-1, 0, 1],
            format_func=lambda v: {
                -1: t["rosa_dur_low"],
                 0: t["rosa_dur_mid"],
                 1: t["rosa_dur_high"],
            }[v],
            index=1,
            key=key,
            horizontal=False,
        )
        return int(choice)

    # ── Section A: Chair ──────────────────────────────────────────
    st.markdown(f"### {t['rosa_sec_a']}")
    colA1, colA2 = st.columns(2)
    with colA1:
        st.markdown(f"**{t['rosa_a1']}**")
        st.caption(L["a1_base"])
        a1_pts = 1  # base
        a1_pts += _rosa_checkbox(L["a1_low"],    2, "rosa_a1_low")
        a1_pts += _rosa_checkbox(L["a1_high"],   2, "rosa_a1_high")
        a1_pts += _rosa_checkbox(L["a1_nofoot"], 3, "rosa_a1_nofoot")
        a1_pts += _rosa_checkbox(L["a1_cramp"],  1, "rosa_a1_cramp")
        a1_pts += _rosa_checkbox(L["a1_nonadj"], 1, "rosa_a1_nonadj")

        st.markdown(f"**{t['rosa_a3']}**")
        st.caption(L["a3_base"])
        a3_pts = 1
        a3_pts += _rosa_checkbox(L["a3_high"],   2, "rosa_a3_high")
        a3_pts += _rosa_checkbox(L["a3_hard"],   1, "rosa_a3_hard")
        a3_pts += _rosa_checkbox(L["a3_wide"],   1, "rosa_a3_wide")
        a3_pts += _rosa_checkbox(L["a3_nonadj"], 1, "rosa_a3_nonadj")

    with colA2:
        st.markdown(f"**{t['rosa_a2']}**")
        st.caption(L["a2_base"])
        a2_pts = 1
        a2_pts += _rosa_checkbox(L["a2_long"],   2, "rosa_a2_long")
        a2_pts += _rosa_checkbox(L["a2_short"],  2, "rosa_a2_short")
        a2_pts += _rosa_checkbox(L["a2_nonadj"], 1, "rosa_a2_nonadj")

        st.markdown(f"**{t['rosa_a4']}**")
        st.caption(L["a4_base"])
        a4_pts = 1
        a4_pts += _rosa_checkbox(L["a4_nolumb"], 2, "rosa_a4_nolumb")
        a4_pts += _rosa_checkbox(L["a4_angle"],  2, "rosa_a4_angle")
        a4_pts += _rosa_checkbox(L["a4_noback"], 3, "rosa_a4_noback")
        a4_pts += _rosa_checkbox(L["a4_hidesk"], 1, "rosa_a4_hidesk")
        a4_pts += _rosa_checkbox(L["a4_nonadj"], 1, "rosa_a4_nonadj")

    st.markdown("**" + t["rosa_duration"] + " · Chair**")
    dur_chair = _duration_selector("rosa_dur_chair")

    st.divider()

    # ── Section B: Monitor + Phone ────────────────────────────────
    st.markdown(f"### {t['rosa_sec_b']}")
    colB1, colB2 = st.columns(2)
    with colB1:
        st.markdown(f"**{t['rosa_b1']}**")
        st.caption(L["b1_base"])
        b1_pts = 1
        b1_pts += _rosa_checkbox(L["b1_low"],    2, "rosa_b1_low")
        b1_pts += _rosa_checkbox(L["b1_far"],    1, "rosa_b1_far")
        b1_pts += _rosa_checkbox(L["b1_high"],   3, "rosa_b1_high")
        b1_pts += _rosa_checkbox(L["b1_twist"],  1, "rosa_b1_twist")
        b1_pts += _rosa_checkbox(L["b1_glare"],  1, "rosa_b1_glare")
        b1_pts += _rosa_checkbox(L["b1_docs"],   1, "rosa_b1_docs")
        st.markdown("**" + t["rosa_duration"] + " · Monitor**")
        dur_mon = _duration_selector("rosa_dur_mon")

    with colB2:
        st.markdown(f"**{t['rosa_b2']}**")
        st.caption(L["b2_base"])
        b2_pts = 1
        b2_pts += _rosa_checkbox(L["b2_far"],   2, "rosa_b2_far")
        b2_pts += _rosa_checkbox(L["b2_hold"],  2, "rosa_b2_hold")
        b2_pts += _rosa_checkbox(L["b2_nohnd"], 1, "rosa_b2_nohnd")
        st.markdown("**" + t["rosa_duration"] + " · Phone**")
        dur_phone = _duration_selector("rosa_dur_phone")

    st.divider()

    # ── Section C: Mouse + Keyboard ───────────────────────────────
    st.markdown(f"### {t['rosa_sec_c']}")
    colC1, colC2 = st.columns(2)
    with colC1:
        st.markdown(f"**{t['rosa_c1']}**")
        st.caption(L["c1_base"])
        c1_pts = 1
        c1_pts += _rosa_checkbox(L["c1_reach"],  2, "rosa_c1_reach")
        c1_pts += _rosa_checkbox(L["c1_diff"],   2, "rosa_c1_diff")
        c1_pts += _rosa_checkbox(L["c1_pinch"],  1, "rosa_c1_pinch")
        c1_pts += _rosa_checkbox(L["c1_palm"],   1, "rosa_c1_palm")
        st.markdown("**" + t["rosa_duration"] + " · Mouse**")
        dur_mouse = _duration_selector("rosa_dur_mouse")

    with colC2:
        st.markdown(f"**{t['rosa_c2']}**")
        st.caption(L["c2_base"])
        c2_pts = 1
        c2_pts += _rosa_checkbox(L["c2_ext"],    2, "rosa_c2_ext")
        c2_pts += _rosa_checkbox(L["c2_dev"],    1, "rosa_c2_dev")
        c2_pts += _rosa_checkbox(L["c2_hi"],     1, "rosa_c2_hi")
        c2_pts += _rosa_checkbox(L["c2_over"],   1, "rosa_c2_over")
        c2_pts += _rosa_checkbox(L["c2_nonadj"], 1, "rosa_c2_nonadj")
        st.markdown("**" + t["rosa_duration"] + " · Keyboard**")
        dur_kbd = _duration_selector("rosa_dur_kbd")

    st.divider()

    # ── Compute final ROSA scores ─────────────────────────────────
    rosa = rosa_final_score(
        a1=a1_pts, a2=a2_pts, a3=a3_pts, a4=a4_pts,
        duration_chair=dur_chair,
        b1=b1_pts, b2=b2_pts,
        duration_mon=dur_mon, duration_phone=dur_phone,
        c1=c1_pts, c2=c2_pts,
        duration_mouse=dur_mouse, duration_kbd=dur_kbd,
    )

    # ── Display final scores ──────────────────────────────────────
    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        st.metric(t["rosa_chair_score"], f"{rosa['chair_rosa']} / 10")
    with rc2:
        st.metric(t["rosa_monperi"], f"{rosa['mon_peri']} / 10")
    with rc3:
        st.metric(t["rosa_final"], f"{rosa['final']} / 10")

    # Action banner (color-coded)
    st.markdown(
        f"<div style='padding:18px 22px; background:{rosa['action_color']}; "
        f"color:white; border-radius:12px; margin-top:10px; "
        f"font-weight:800; font-size:15px; text-align:center;'>"
        f"{t['rosa_action']}: {rosa['action']}</div>",
        unsafe_allow_html=True,
    )

    # Sub-score breakdown (for the ergonomist / auditability)
    with st.expander("Sub-score breakdown"):
        st.markdown(
            f"- A.1 Chair height: **{a1_pts}**  \n"
            f"- A.2 Pan depth: **{a2_pts}**  \n"
            f"- A.3 Armrests: **{a3_pts}**  \n"
            f"- A.4 Back support: **{a4_pts}**  \n"
            f"- Duration adj (chair): **{dur_chair:+d}**  \n"
            f"- **→ Chair ROSA = {rosa['chair_rosa']}**  \n\n"
            f"- B.1 Monitor: **{b1_pts}** · Duration: **{dur_mon:+d}**  \n"
            f"- B.2 Phone: **{b2_pts}** · Duration: **{dur_phone:+d}**  \n"
            f"- **→ Section B = {rosa['section_b']}**  \n\n"
            f"- C.1 Mouse: **{c1_pts}** · Duration: **{dur_mouse:+d}**  \n"
            f"- C.2 Keyboard: **{c2_pts}** · Duration: **{dur_kbd:+d}**  \n"
            f"- **→ Section C = {rosa['section_c']}**  \n\n"
            f"- Monitor & Peripherals ROSA = **{rosa['mon_peri']}**  \n"
            f"- **ROSA FINAL = {rosa['final']}**"
        )


# --------------------------------------------------------------------
# Tab 5 (was 4) — Polished Summary
# --------------------------------------------------------------------
with tab_summary:

    sub_label = subject_id.strip() if subject_id.strip() else (
        "Χωρίς όνομα" if lang == "el" else "Unidentified subject"
    )

    # ---- Component-wise findings (NO composite score) -----------
    # An aggregate percentage was removed 2026: an arithmetic mean of
    # three unequally-weighted sub-scores has no scientific basis, and
    # arbitrary "Excellent/Good" bands imply validated cut-offs that do
    # not exist. Each domain is now reported descriptively.
    ws_pass = sum([
        abs(chair_diff)   <= 2,
        abs(desk_diff)    <= 2,
        abs(monitor_diff) <= 4,
    ])
    ws_pct    = ws_pass / 3 * 100
    osha_pct  = (n_pass / n_total) * 100
    angle_pct = (n_ok / n_total_angles) * 100

    def _domain_label(passed, total, high_bar):
        """Descriptive category, no percentages presented as a validated grade."""
        ratio = passed / total if total else 0
        if ratio >= high_bar: return (t["dl_all_met"],  "#10b981")
        if ratio >= 0.6:      return (t["dl_some_not"], "#f59e0b")
        return (t["dl_many_not"], "#ef4444")

    ws_label,    ws_color    = _domain_label(ws_pass,   3,               2/3)
    osha_label,  osha_color  = _domain_label(n_pass,    n_total,         0.85)
    angle_label, angle_color = _domain_label(n_ok,      n_total_angles,  5/6)

    # ---- Top banner ---------------------------------------------
    st.markdown(
        f"""
        <div class="summary-banner">
            <h2>{t["sum_report_title"]}</h2>
            <div class="meta">
                <strong>{sub_label}</strong> &nbsp;·&nbsp; {assess_date.strftime("%d %b %Y")}
                &nbsp;·&nbsp; {t["f_stature"]}: {height} cm &nbsp;·&nbsp; {t["f_weight"]}: {weight} kg
                &nbsp;·&nbsp; BMI {bmi} ({bmi_cat}) &nbsp;·&nbsp; {_sex_label(sex)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- Intended-purpose / non-medical disclaimer (top of summary)
    st.info(t["sum_intended"])

    # ---- ROSA FINAL SCORE banner (validated instrument, ergonomist input) --
    st.markdown(
        f"<div style='display:flex; align-items:center; gap:16px; "
        f"padding:18px 22px; margin:10px 0 4px; "
        f"background:linear-gradient(135deg,{rosa['action_color']}22 0%,white 60%); "
        f"border-left:6px solid {rosa['action_color']}; border-radius:12px;'>"
        f"<div style='font-size:38px; font-weight:800; color:{rosa['action_color']};'>"
        f"{rosa['final']}<span style='font-size:18px; color:#64748b;'>/10</span></div>"
        f"<div style='flex:1;'>"
        f"<div style='font-size:11px; letter-spacing:.14em; text-transform:uppercase; "
        f"color:#64748b; font-weight:700;'>ROSA FINAL SCORE</div>"
        f"<div style='font-size:14px; color:#0f172a; font-weight:600; margin-top:2px;'>"
        f"{rosa['action']}</div>"
        f"<div style='font-size:11px; color:#94a3b8; margin-top:4px;'>"
        f"Sonne, Villalta &amp; Andrews (2012) · Chair {rosa['chair_rosa']}/10 · "
        f"Monitor &amp; Peripherals {rosa['mon_peri']}/10</div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    # ---- Three domain cards (no overall composite) --------------
    q1, q2, q3 = st.columns(3)

    def _quad(title, value, subtitle, color):
        return f"""
        <div class="quad-card" style="border-top: 4px solid {color};">
            <div class="quad-title">{title}</div>
            <div class="quad-value" style="color: {color};">{value}</div>
            <div class="quad-sub">{subtitle}</div>
        </div>
        """

    q1.markdown(_quad(t["sum_card_ws"], f"{ws_pass}/3",
                      f"{t['sum_ws_sub']} · {ws_label}", ws_color),
                unsafe_allow_html=True)
    q2.markdown(_quad(t["sum_card_chair"], f"{n_pass}/{n_total}",
                      f"{osha_label}", osha_color),
                unsafe_allow_html=True)
    q3.markdown(_quad(t["sum_card_angles"], f"{n_ok}/{n_total_angles}",
                      f"{angle_label}", angle_color),
                unsafe_allow_html=True)

    st.write("")

    # ---- BMI-related ergonomic considerations (qualitative) -----
    # Previously this section reported numerical multipliers (e.g. "×1.44
    # L4/L5 disc load") which risked being read as a personalised
    # biomechanical measurement. Per adversarial peer review 2026, these
    # multipliers are now presented as qualitative ergonomic considerations,
    # not as fabricated per-subject numeric loads.
    st.markdown(f"### {t['bmi_head']}")

    if bmi_band == "normal":
        st.markdown(
            f'<div class="finding-ok">'
            + t["bmi_normal"].format(bmi=bmi, cat=bmi_cat)
            + '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption(
            f"BMI {bmi} kg/m² ({bmi_cat}). The following ergonomic considerations "
            "are commonly discussed in the biomechanical literature for overweight "
            "and obese populations (e.g. Nachemson intradiscal pressure studies, "
            "McGill spinal biomechanics). They are **qualitative guidance**, not "
            "individual measurements."
        )
        considerations = [
            "**Lumbar disc load** is typically elevated in seated postures at "
            "higher body mass — favour chairs with strong lumbar support and "
            "encourage short standing/walking breaks.",
            "**Sustained neck/trapezius activity** may be increased with forward "
            "head posture — verify monitor height and viewing distance carefully.",
            "**Seat contact pressure** distribution is affected by body mass — "
            "ensure adequate cushioning, seat depth, and a waterfall front edge.",
            "**Overhead / forward reach envelope** is reduced by abdominal mass — "
            "keep keyboard, mouse, and frequently-used items within a shorter reach.",
            "**Lower-limb circulation** during prolonged sitting may benefit from "
            "more frequent postural changes and calf-pump exercises.",
        ]
        for line in considerations:
            st.markdown(f"- {line}")

    st.write("")

    # ---- BMI-adjusted equipment specifications ------------------
    st.markdown("### 🛠️ Required equipment specifications (BMI-adjusted)")

    if bmi_band == "normal":
        st.caption("Standard ergonomic specifications apply.")
    else:
        st.caption(
            f"Specifications below reflect requirements for **{bmi_cat}** category. "
            "Verify the actual equipment in use against these targets."
        )

    spec_color = "#10b981" if bmi_band == "normal" else \
                 "#f59e0b" if bmi_band == "overweight" else "#ef4444"

    def _spec_card(title, icon, items, color):
        rows = "".join(
            f'<tr>'
            f'<td style="padding: 6px 12px 6px 0; color: #6b7280; '
            f'font-size: 13px; vertical-align: top; white-space: nowrap;">{label}</td>'
            f'<td style="padding: 6px 0; color: #1f2937; '
            f'font-size: 14px; font-weight: 500;">{value}</td>'
            f'</tr>'
            for label, value in items
        )
        return f"""
        <div style="
            padding: 18px 22px; background: white; border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            border-top: 4px solid {color}; height: 100%;
        ">
            <div style="font-size: 16px; font-weight: 700;
                        color: #111827; margin-bottom: 12px;">
                {icon} &nbsp; {title}
            </div>
            <table style="border-collapse: collapse; width: 100%;">
                {rows}
            </table>
        </div>
        """

    sc1, sc2 = st.columns(2)
    sc1.markdown(_spec_card("Chair / Seat", "🪑", equip["chair"], spec_color),
                 unsafe_allow_html=True)
    sc2.markdown(_spec_card("Desk / Workspace", "🗄️", equip["desk"], spec_color),
                 unsafe_allow_html=True)

    st.write("")

    # ---- Key findings -------------------------------------------
    st.markdown("### Key findings")

    findings = []
    if abs(chair_diff) > 2:
        d = "too high" if chair_diff > 0 else "too low"
        findings.append(f"Chair seat is {abs(chair_diff):.1f} cm {d} for this subject's stature.")
    if abs(desk_diff) > 2:
        d = "too high" if desk_diff > 0 else "too low"
        findings.append(f"Desk is {abs(desk_diff):.1f} cm {d} for the current chair height.")
    if abs(monitor_diff) > 4:
        d = "too high" if monitor_diff > 0 else "too low"
        findings.append(f"Monitor top is {abs(monitor_diff):.1f} cm {d} relative to seated eye level.")

    failed_osha_items = [label for label, ok in osha_results.items() if not ok]
    if failed_osha_items:
        findings.append(f"{len(failed_osha_items)} EN 1335 / ISO 9241-5 chair criteria not met "
                        f"({len(failed_osha_items)/n_total*100:.0f}% of the checklist).")

    bad_angles = [(label, val, lo, hi) for label, (status, val, (lo, hi))
                  in angle_results.items() if status == "warn"]
    if bad_angles:
        findings.append(f"{len(bad_angles)} joint(s) outside the comfort range.")

    if findings:
        for f in findings:
            st.markdown(f'<div class="finding-row">⚠ {f}</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="finding-ok">✓ No significant ergonomic issues detected. '
            'Workstation is well-matched to the subject.</div>',
            unsafe_allow_html=True,
        )

    st.write("")

    # ---- Detailed breakdowns (collapsible) ----------------------
    with st.expander("📐 Workstation measurements — detail", expanded=False):
        rows = [
            ("Chair seat",     f"{chair_height} cm",  f"{ideal_chair} cm",         f"{chair_diff:+.1f} cm"),
            ("Desk (vs current chair)", f"{desk_height} cm", f"{desk_for_actual_chair} cm", f"{desk_diff:+.1f} cm"),
            ("Desk (vs ideal chair)",   f"{desk_height} cm", f"{ideal_desk_target} cm",     f"{desk_height - ideal_desk_target:+.1f} cm"),
            ("Monitor top (vs current chair)", f"{monitor_height} cm", f"{monitor_for_actual_chair} cm", f"{monitor_diff:+.1f} cm"),
            ("Monitor top (vs ideal chair)",   f"{monitor_height} cm", f"{ideal_mon_target} cm",         f"{monitor_height - ideal_mon_target:+.1f} cm"),
        ]
        st.markdown(
            "| Measurement | Measured | Target | Δ |\n"
            "|---|---|---|---|\n"
            + "\n".join(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |" for r in rows)
        )

    if failed_osha_items:
        with st.expander(f"🪑 Chair criteria not met ({len(failed_osha_items)})", expanded=False):
            for item in failed_osha_items:
                st.markdown(f"- {item}")

    if bad_angles:
        with st.expander(f"📏 Joint angles out of range ({len(bad_angles)})", expanded=False):
            for label, val, lo, hi in bad_angles:
                deviation = val - lo if val < lo else val - hi
                st.markdown(f"- **{label}** — measured {val}°, target {lo}°–{hi}° "
                            f"(deviation {deviation:+}°)")

    # ---- Auto recommendations -----------------------------------
    st.markdown("### Recommendations")
    recs = []

    if chair_diff > 2:
        recs.append(f"Lower the chair toward **{ideal_chair} cm**.")
    elif chair_diff < -2:
        recs.append(f"Raise the chair toward **{ideal_chair} cm**; if feet then dangle, add a footrest.")

    if desk_diff > 2:
        recs.append(f"Lower the desk toward **{ideal_desk_target} cm** (with the chair at its ideal height). "
                    "If non-adjustable, consider a keyboard tray or chair height + footrest combination.")
    elif desk_diff < -2:
        recs.append(f"Raise the desk toward **{ideal_desk_target} cm** with risers, or replace with a height-adjustable model.")

    if monitor_diff > 4:
        recs.append(f"Lower the monitor; aim for the top edge at **{ideal_mon_target} cm**.")
    elif monitor_diff < -4:
        recs.append(f"Raise the monitor (stand or stack of books) to bring the top edge to **{ideal_mon_target} cm**.")

    if failed_osha_items:
        recs.append(f"Address the {len(failed_osha_items)} EN 1335 / ISO 9241-5 chair criteria not met — see detail above. "
                    "Highest-impact items are usually backrest tilt/lock, lumbar support, and seat depth.")

    if bad_angles:
        recs.append("Re-evaluate posture for joints flagged out of range. Often these are knock-on effects "
                    "of incorrect chair/desk height, so fix those first and re-check.")

    # Break frequency guidance (evidence-based, not fabricated numbers)
    if bmi_band == "obese":
        recs.append(
            "**[BMI-related]** Consider **more frequent postural changes** than "
            "the general 60-minute baseline — the biomechanical and circulatory "
            "literature supports shorter sit intervals in obese populations. "
            "Adopt the 20-20-20 visual rest rule (every 20 min look 6 m away "
            "for 20 sec)."
        )
        recs.append(
            "**[BMI-related]** A **footrest** is often needed to relieve thigh "
            "pressure; prefer a chair with **strong lumbar support**; a "
            "**sit-stand desk** with modest standing periods may help."
        )
    elif bmi_band == "overweight":
        recs.append(
            "**[BMI-related]** Schedule regular postural changes (roughly every "
            "45 minutes) — stand, walk, and apply the 20-20-20 visual rest rule."
        )
        recs.append(
            "**[BMI-related]** Allow modest extra clearance (~2–4 cm) between "
            "abdomen and desk edge so wrists and shoulders can stay neutral."
        )
    else:
        recs.append(
            "Take a microbreak roughly every 30 minutes — stand, walk a few "
            "steps, and apply the 20-20-20 visual rest rule (every 20 min look "
            "6 m away for 20 sec)."
        )

    for r in recs:
        st.markdown(f"- {r}")

    # ---- Risk profile (NEW) ------------------------------------
    st.divider()
    st.markdown(f"### {t['risk_head']}")

    # Build subject context dict — passed to risk model so that all
    # answers in the intake form actually drive the estimates.
    ctx = {
        "bmi_band":       bmi_band,
        "bmi_value":      bmi,
        "sex":            sex,
        "age":            age,
        "hours_computer": hours_computer,
        "hours_mouse":    hours_mouse,
        "hours_sitting":  hours_sitting,
        "diabetes":       diabetes,
        "smoking":        smoking,
        "injury_regions": injury_regions,
        "pregnant":       pregnant       and (sex == "Female"),
        "oral_contra":    oral_contra    and (sex == "Female"),
        # Psychosocial (Karasek Job Demand-Control-Support)
        "psy_demand":     psy_demand,
        "psy_control":    psy_control,
        "psy_support":    psy_support,
        # Lifestyle & modifiable risk / protective factors
        "exercise_freq":     exercise_freq,
        "muscle_hypertrophy": muscle_hypertrophy,
        "sleep_hours":       sleep_hours,
        "non_work_pa_min":   non_work_pa_min,
        "diet_med":          diet_med,
    }

    risk_profile = compute_risk_profile(
        chair_diff=chair_diff,
        desk_diff=desk_diff,
        monitor_diff=monitor_diff,
        osha_pct=(n_pass / n_total),
        angle_results=angle_results,
        n_total_osha=n_total,
        ctx=ctx,
    )

    # Helper: use Greek name when in EL mode, English otherwise
    def _cond_name(c):
        return c["name_gr"] if lang == "el" else c["name_en"]

    if not risk_profile:
        st.markdown(
            f'<div class="finding-ok">{t["risk_no_factors"]}</div>',
            unsafe_allow_html=True,
        )
    else:
        # Disclaimer first — plain language, no jargon
        st.info(t["risk_how_read"])

        # Aggregate unique conditions for a top-of-section summary
        all_condition_keys = []
        for _, conds in risk_profile:
            for c in conds:
                if c not in all_condition_keys:
                    all_condition_keys.append(c)

        st.markdown(
            t["risk_summary_line"].format(
                n_risks=len(risk_profile),
                n_conds=len(all_condition_keys),
            )
        )

        # ---- Aggregate: for each condition, collect ALL risk-factor
        # labels that trigger it. Show each condition ONCE (was
        # duplicating when multiple triggers linked to the same
        # condition, per user feedback Sept 2026).
        cond_to_triggers = {}
        for risk_label, condition_keys in risk_profile:
            for ck in condition_keys:
                cond_to_triggers.setdefault(ck, []).append(risk_label)

        # Sort conditions by severity — highest risk first
        def _cond_sort_key(ck):
            cat = weighted_risk_analysis(ck, ctx)["category"]
            return {"High": 0, "Moderate": 1, "Low": 2}.get(cat, 3)

        sorted_conditions = sorted(cond_to_triggers.keys(), key=_cond_sort_key)

        # Language tables (defined once)
        _CAT_TXT = {
            "el": {"Low": "Χαμηλός κίνδυνος",
                   "Moderate": "Μεσαίος κίνδυνος",
                   "High": "Υψηλός κίνδυνος"},
            "en": {"Low": "Low risk", "Moderate": "Moderate risk",
                   "High": "High risk"},
        }[lang]
        _TIER_TXT = {
            "el": {"small": "🟢 Μικρή επιβάρυνση",
                   "moderate": "🟠 Μεσαία επιβάρυνση",
                   "strong": "🔴 Μεγάλη επιβάρυνση"},
            "en": {"small": "🟢 Small factor",
                   "moderate": "🟠 Moderate factor",
                   "strong": "🔴 Strong factor"},
        }[lang]
        _triggered_by  = "Ενεργοποιείται από:" if lang == "el" else "Triggered by:"
        _protective_lb = "Προστατευτικοί παράγοντες:" if lang == "el" else "Protective factors:"

        # ---- One expander per condition, with all triggers listed ----
        for ck in sorted_conditions:
            c        = CONDITIONS[ck]
            triggers = cond_to_triggers[ck]
            analysis = weighted_risk_analysis(ck, ctx)
            n_f      = len(analysis["factors"])
            n_word   = "παράγοντες παρόντες" if lang == "el" else "factors present"
            cat_lbl  = _CAT_TXT.get(analysis["category"], analysis["category"])

            with st.expander(
                f"⚠ {_cond_name(c)} — {cat_lbl} · {n_f} {n_word}",
                expanded=(analysis["category"] in ("High", "Moderate")),
            ):
                # -- List which environmental risk factors triggered this --
                st.markdown(f"**{_triggered_by}**")
                for tr in triggers:
                    st.markdown(f"- {tr}")

                # -- Present factors block --
                if analysis["factors"]:
                    st.markdown("")
                    st.markdown(f"**{t['risk_factors_present']}**")
                    for ff in analysis["factors"]:
                        or_pct = int(round((ff["or"] - 1) * 100)) if ff["or"] > 1.0 else 0
                        if lang == "el":
                            risk_txt = (
                                f"αυξάνει τον κίνδυνο περίπου {or_pct}%"
                                if or_pct > 0 else ""
                            )
                            if ff["ci"] and or_pct > 0:
                                lo_pct = int(round((ff["ci"][0] - 1) * 100))
                                hi_pct = int(round((ff["ci"][1] - 1) * 100))
                                risk_txt += (
                                    f" (η μελέτη δίνει μεταξύ {lo_pct}% και {hi_pct}%)"
                                )
                        else:
                            risk_txt = (
                                f"raises the risk by about {or_pct}%"
                                if or_pct > 0 else ""
                            )
                            if ff["ci"] and or_pct > 0:
                                lo_pct = int(round((ff["ci"][0] - 1) * 100))
                                hi_pct = int(round((ff["ci"][1] - 1) * 100))
                                risk_txt += (
                                    f" (the study range is {lo_pct}%–{hi_pct}%)"
                                )

                        tier_txt   = _TIER_TXT.get(ff["tier"], ff["tier"])
                        source_txt = (
                            f"Πηγή: {ff['source']}" if lang == "el"
                            else f"Source: {ff['source']}"
                        )

                        st.markdown(
                            f"<div style='padding:8px 12px; margin:5px 0; "
                            f"background:#f8fafc; border-radius:8px; "
                            f"border-left:4px solid {ff['color']}; font-size:13.5px;'>"
                            f"<b>{ff['label']}</b>"
                            f"<div style='font-size:12.5px; color:#334155; "
                            f"margin-top:4px; line-height:1.5;'>"
                            f"<b>{tier_txt}</b>"
                            + (f" — {risk_txt}" if risk_txt else "")
                            + f"</div>"
                            f"<div style='font-size:11px; color:#64748b; "
                            f"margin-top:4px; font-style:italic;'>{source_txt}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                # -- Protective factors --
                if analysis["protective_notes"]:
                    st.markdown("")
                    st.markdown(f"**{_protective_lb}**")
                    for pn in analysis["protective_notes"]:
                        st.markdown(
                            f"<div style='padding:4px 10px; margin:3px 0; "
                            f"background:#d1fae5; border-radius:6px; "
                            f"border-left:3px solid #10b981; font-size:12px;'>"
                            f"✓ {pn}</div>",
                            unsafe_allow_html=True,
                        )

        # ---- Compact summary strip (one row per condition) ----------
        st.markdown("")
        st.markdown(f"#### {t['risk_summary_head']}")
        st.caption(t["risk_summary_caption"])
        _CAT_TXT2 = {
            "el": {"Low": "Χαμηλός", "Moderate": "Μεσαίος", "High": "Υψηλός"},
            "en": {"Low": "Low", "Moderate": "Moderate", "High": "High"},
        }[lang]
        _f_word = "παράγοντες" if lang == "el" else "factors"

        for ck in sorted_conditions:
            c = CONDITIONS[ck]
            analysis = weighted_risk_analysis(ck, ctx)
            n_f = len(analysis["factors"])
            cat_label = _CAT_TXT2.get(analysis["category"], analysis["category"])
            st.markdown(
                f"<div style='display:flex; align-items:center; gap:12px; "
                f"padding:10px 14px; margin-bottom:6px; background:white; "
                f"border-radius:10px; border-left:6px solid {analysis['category_color']};'>"
                f"<div style='flex:1;'><b>{_cond_name(c)}</b></div>"
                f"<div style='background:{analysis['category_color']}; color:white; "
                f"padding:4px 10px; border-radius:6px; font-size:12px; "
                f"font-weight:700;'>{cat_label} · {n_f} {_f_word}</div></div>",
                unsafe_allow_html=True,
            )

    # ---- Send results to ErgoFit backend ------------------------
    st.divider()
    st.markdown(f"### {t['submit_head']}")
    st.markdown(t["submit_notice"])

    consent = st.checkbox(
        t["submit_consent"],
        value=False,
        key="submit_consent",
    )

    if st.button(t["submit_btn"], disabled=not consent, type="primary"):
        # Build payload — flatten all key fields for the Sheet
        submission_payload = {
            "tool":              "ErgoFit",
            "timestamp_utc":     datetime.utcnow().isoformat(timespec="seconds"),
            "client_code":       st.query_params.get("client", ""),
            "subject_id":        sub_label,
            "assessment_date":   assess_date.isoformat(),
            # Demographics
            "age":               age,
            "sex":               sex,
            "stature_cm":        height,
            "weight_kg":         weight,
            "bmi":               bmi,
            "bmi_category":      bmi_cat,
            # Occupational
            "hours_computer":    hours_computer,
            "hours_mouse":       hours_mouse,
            "hours_sitting":     hours_sitting,
            # Health / lifestyle
            "diabetes":          diabetes,
            "smoking":           smoking,
            "pregnant":          pregnant,
            "oral_contra":       oral_contra,
            # Prior injuries per region (internal keys — not translated)
            "injury_neck":       injury_regions.get("neck", False),
            "injury_shoulder":   injury_regions.get("shoulder", False),
            "injury_elbow":      injury_regions.get("elbow", False),
            "injury_wrist_hand": injury_regions.get("wrist", False),
            "injury_lower_back": injury_regions.get("back", False),
            "injury_leg":        injury_regions.get("leg", False),
            # Direct anthropometry (0 = not measured, using estimate)
            "popliteal_direct_cm":     popliteal_h_direct,
            "seated_elbow_direct_cm":  seated_elbow_h_direct,
            "seated_eye_direct_cm":    seated_eye_h_direct,
            # Psychosocial (Karasek JDCS)
            "psy_demand":        psy_demand,
            "psy_control":       psy_control,
            "psy_support":       psy_support,
            # Lifestyle / protective factors
            "exercise_freq":     exercise_freq,
            "muscle_hypertrophy":muscle_hypertrophy,
            "sleep_hours":       sleep_hours,
            "non_work_pa_min":   non_work_pa_min,
            "diet_med":          diet_med,
            # Workstation measurements
            "chair_height_cm":   chair_height,
            "desk_height_cm":    desk_height,
            "monitor_top_cm":    monitor_height,
            "chair_diff_cm":     round(chair_diff, 1),
            "desk_diff_cm":      round(desk_diff, 1),
            "monitor_diff_cm":   round(monitor_diff, 1),
            # Component scores (kept as raw counts, no arbitrary composite)
            "workstation_pass":  ws_pass,
            "workstation_total": 3,
            "chair_pass":        n_pass,
            "chair_total":       n_total,
            "angles_pass":       n_ok,
            "angles_total":      n_total_angles,
            # ROSA (Sonne 2012) — validated instrument
            "rosa_chair":        rosa["chair_rosa"],
            "rosa_section B":    rosa["section_b"],
            "rosa_section C":    rosa["section_c"],
            "rosa_mon_peri":     rosa["mon_peri"],
            "rosa_final":        rosa["final"],
            "rosa_action":       rosa["action"],
            # Risk-factor profile — condition → count of elevated factors
            "risk_conditions":   ", ".join(
                f"{CONDITIONS[ck]['name_en']}("
                f"{elevated_factors(ck, ctx)[0]} factors)"
                for ck in (all_condition_keys if risk_profile else [])
            ),
        }

        _spinner_txt = "Αποστολή..." if lang == "el" else "Sending..."
        with st.spinner(_spinner_txt):
            ok, msg = submit_to_backend(submission_payload)

        if ok:
            st.success(t["submit_ok"].format(msg=msg))
        else:
            st.error(t["submit_fail"].format(msg=msg))

    # ---- Footer -------------------------------------------------
    st.divider()
    st.caption(t["footer_report"].format(date=assess_date.strftime("%d %b %Y")))
    st.caption(t["footer_legal"])