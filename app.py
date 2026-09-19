from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import streamlit as st

from ergofit.assessment.engine import build_findings, evidence_ids_for_context
from ergofit.assessment.recommendations import build_recommendations
from ergofit.backend import submit_payload
from ergofit.i18n import get_text
from ergofit.science.anthropometry import bmi, reference_from_stature
from ergofit.science.evidence_registry import EVIDENCE, get_many
from ergofit.science.rosa import compute_rosa
from ergofit.science.standards import (
    CHAIR_FIT_ITEMS,
    CHAIR_FIT_LABELS_EL,
    EN1335_LABELS_EL,
    EN1335_TYPE_A_REFERENCE,
    POSTURE_LABELS_EL,
    POSTURE_REFERENCES,
)
from ergofit.ui.components import evidence_card, finding_card, recommendation_card
from ergofit.ui.theme import apply_theme, hero


ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"

st.set_page_config(
    page_title="ErgoFit Intelligence v2",
    page_icon="🪑",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme(ASSETS)

if "lang" not in st.session_state:
    st.session_state.lang = "el"

with st.sidebar:
    st.session_state.lang = st.radio(
        "Γλώσσα / Language",
        ["el", "en"],
        format_func=lambda x: "🇬🇷 Ελληνικά" if x == "el" else "🇬🇧 English",
        horizontal=True,
    )
    quick_mode = st.toggle("⚡ Quick Mode" if st.session_state.lang == "en" else "⚡ Γρήγορη αξιολόγηση", value=False)
    st.caption(
        "Quick Mode hides direct anthropometry, psychosocial context and advanced mechanical exposures."
        if st.session_state.lang == "en"
        else "Η Γρήγορη αξιολόγηση κρύβει τις άμεσες σωματομετρικές μετρήσεις, το ψυχοκοινωνικό πλαίσιο και τις προχωρημένες μηχανικές εκθέσεις."
    )
    st.divider()
    st.markdown("**ErgoFit Intelligence v2**")
    st.caption(
        "Evidence architecture: exposure → symptoms → intervention. No disease probability score."
        if st.session_state.lang == "en"
        else "Αρχιτεκτονική τεκμηρίωσης: έκθεση → συμπτώματα → παρέμβαση. Δεν υπολογίζεται πιθανότητα νόσου."
    )

lang = st.session_state.lang
t = get_text(lang)
hero(t["hero_title"], t["hero_sub"])

with st.expander(t["purpose"], expanded=False):
    st.markdown(t["purpose_body"])


def yes_no_unknown(label: str, key: str, help_text: str | None = None):
    options = [None, True, False]
    return st.selectbox(
        label,
        options,
        format_func=lambda v: (
            "— Not assessed —" if v is None and lang == "en" else
            "— Δεν αξιολογήθηκε —" if v is None else
            t["yes"] if v is True else t["no"]
        ),
        key=key,
        help=help_text,
    )


def duration_selector(key: str):
    options = [-1, 0, 1]
    labels_el = {
        -1: "<30΄ συνεχόμενα ή <1 h/ημέρα (−1)",
        0: "30–60΄ συνεχόμενα ή 1–4 h/ημέρα (0)",
        1: ">1 h συνεχόμενα ή >4 h/ημέρα (+1)",
    }
    labels_en = {
        -1: "<30 min continuous or <1 h/day (−1)",
        0: "30–60 min continuous or 1–4 h/day (0)",
        1: ">1 h continuous or >4 h/day (+1)",
    }
    labels = labels_el if lang == "el" else labels_en
    return st.radio(
        "Διάρκεια χρήσης" if lang == "el" else "Duration of use",
        options,
        format_func=lambda x: labels[x],
        key=key,
    )


def rosa_checkbox(label_el: str, label_en: str, points: int, key: str) -> int:
    label = label_el if lang == "el" else label_en
    return points if st.checkbox(f"{label} (+{points})", key=key) else 0


# Ordered workflow; Streamlit evaluates all tabs so later tabs can consume earlier values.
tabs = st.tabs([
    t["tab_profile"], t["tab_symptoms"], t["tab_workstation"], t["tab_chair"],
    t["tab_posture"], t["tab_rosa"], t["tab_evidence"], t["tab_summary"],
])

# ---------------------------------------------------------------------
# 1. Worker profile
# ---------------------------------------------------------------------
with tabs[0]:
    st.subheader(t["profile_title"])
    c1, c2, c3 = st.columns([2, 1, 1])
    subject_id = c1.text_input(t["subject_id"], value="", placeholder="EF-001")
    assessment_date = c2.date_input(t["assessment_date"], value=date.today())
    age = c3.number_input(t["age"], min_value=18, max_value=80, value=35)

    c1, c2, c3 = st.columns(3)
    sex = c1.selectbox(
        t["sex"],
        ["female", "male", "other"],
        format_func=lambda x: {"female": t["female"], "male": t["male"], "other": t["other"]}[x],
    )
    height = c2.number_input(t["height"], min_value=140.0, max_value=210.0, value=175.0, step=0.5)
    weight = c3.number_input(t["weight"], min_value=40.0, max_value=200.0, value=75.0, step=0.5)
    bmi_value = bmi(weight, height)
    st.caption(
        f"BMI: {bmi_value:.1f} kg/m² — shown as health context, not as an ergonomic score."
        if lang == "en"
        else f"ΔΜΣ: {bmi_value:.1f} kg/m² — εμφανίζεται ως στοιχείο υγείας και όχι ως εργονομική βαθμολογία."
    )

    if quick_mode:
        pop_direct = elbow_direct = eye_direct = 0.0
        st.info(t["estimated_note"])
    else:
        with st.expander(t["direct_anthro"], expanded=False):
            st.caption(t["estimated_note"])
            a1, a2, a3 = st.columns(3)
            pop_direct = a1.number_input(t["popliteal"], min_value=0.0, max_value=65.0, value=0.0, step=0.5, help=t["popliteal_help"])
            elbow_direct = a2.number_input(t["elbow_height"], min_value=0.0, max_value=40.0, value=0.0, step=0.5)
            eye_direct = a3.number_input(t["eye_height"], min_value=0.0, max_value=100.0, value=0.0, step=0.5)

    anthro = reference_from_stature(height, sex, pop_direct, elbow_direct, eye_direct)
    st.markdown("#### " + ("Body-fit references" if lang == "en" else "Σωματομετρικές τιμές αναφοράς"))
    a1, a2, a3 = st.columns(3)
    _src = lambda s: s if lang == "en" else ("άμεση μέτρηση" if s == "direct" else "εκτίμηση")
    a1.metric("Popliteal height" if lang == "en" else "Ύψος πίσω από το γόνατο", f"{anthro.popliteal_cm:.1f} cm", _src(anthro.source_popliteal))
    a2.metric("Seated elbow height" if lang == "en" else "Ύψος αγκώνα από την έδρα", f"{anthro.seated_elbow_cm:.1f} cm", _src(anthro.source_elbow))
    a3.metric("Seated eye height" if lang == "en" else "Ύψος ματιών από την έδρα", f"{anthro.seated_eye_cm:.1f} cm", _src(anthro.source_eye))

    c1, c2, c3 = st.columns(3)
    diabetes = c1.checkbox(t["diabetes"])
    smoking = c2.checkbox(t["smoking"])
    sleep_problem = c3.checkbox(t["sleep_problem"])

    c1, c2 = st.columns(2)
    exercise = c1.checkbox(t["exercise"])
    pa_minutes = c2.number_input(t["pa_minutes"], min_value=0, max_value=1500, value=120, step=10)
    st.caption(
        "Physical activity and exercise are recorded as wellbeing/intervention context. They do not subtract points from a disease score."
        if lang == "en" else
        "Η φυσική δραστηριότητα και η άσκηση καταγράφονται ως στοιχεία ευεξίας και παρέμβασης. Δεν αφαιρούν πόντους από κάποια βαθμολογία κινδύνου νόσου."
    )

# ---------------------------------------------------------------------
# 2. Symptoms & exposure
# ---------------------------------------------------------------------
with tabs[1]:
    st.subheader(t["symptoms_title"])
    region_options = ["Neck", "Shoulder(s)", "Elbow / forearm / wrist / hand", "Low back", "Lower limbs"]
    region_labels = {
        "Neck": t["neck"], "Shoulder(s)": t["shoulder"],
        "Elbow / forearm / wrist / hand": t["upper_limb"],
        "Low back": t["low_back"], "Lower limbs": t["lower_limb"],
    }
    symptom_regions = st.multiselect(
        t["symptom_regions"],
        region_options,
        format_func=lambda x: region_labels[x],
        placeholder="Choose options" if lang == "en" else "Επίλεξε περιοχές",
    )

    symptom_details: dict[str, dict] = {}
    if symptom_regions:
        st.markdown("#### " + ("Symptoms by body region" if lang == "en" else "Συμπτώματα ανά περιοχή σώματος"))
        st.caption(
            "Record intensity and work interference separately for each selected region."
            if lang == "en"
            else "Κατέγραψε ξεχωριστά την ένταση και το αν επηρεάζεται η εργασία για κάθε περιοχή που επέλεξες."
        )
        for region in symptom_regions:
            region_label = region_labels[region]
            st.markdown(f"**{region_label}**")

            severity = st.slider(
                f"{t['severity']} — {region_label}",
                0, 10, 0,
                key=f"severity_{region}",
            )

            st.caption(
                "Does this symptom interfere with work?"
                if lang == "en"
                else "Επηρεάζει αυτό το σύμπτωμα την εργασία;"
            )
            interference = st.radio(
                f"Work interference — {region_label}",
                [False, True],
                format_func=lambda v: ("Yes" if v else "No") if lang == "en" else ("Ναι" if v else "Όχι"),
                horizontal=True,
                label_visibility="collapsed",
                key=f"interference_{region}",
            )

            symptom_details[region] = {
                "label": region_label,
                "severity": severity,
                "interference": interference,
            }
            st.divider()

    symptom_severity = max((d["severity"] for d in symptom_details.values()), default=0)
    symptom_interference = any(d["interference"] for d in symptom_details.values()) if symptom_details else False

    digital_eye_strain = st.checkbox("Digital eye strain / visual fatigue" if lang == "en" else "Κόπωση ματιών από τη χρήση της οθόνης")

    st.markdown("#### " + ("Work exposure" if lang == "en" else "Εργασιακή έκθεση"))
    c1, c2, c3 = st.columns(3)
    computer_hours = c1.number_input(t["computer_hours"], min_value=0.0, max_value=16.0, value=0.0, step=0.5)
    mouse_hours = c2.number_input(t["mouse_hours"], min_value=0.0, max_value=16.0, value=0.0, step=0.5)
    sitting_hours = c3.number_input(t["sitting_hours"], min_value=0.0, max_value=16.0, value=0.0, step=0.5)

    c1, c2 = st.columns(2)
    long_sitting_bout = c1.selectbox(t["uninterrupted"], ["<30 min", "30–60 min", "60–120 min", ">120 min"])
    active_breaks = c2.selectbox(
        t["breaks"], [None, True, False],
        format_func=lambda v: "—" if v is None else (t["yes"] if v else t["no"]),
    )

    if not quick_mode:
        st.markdown("#### " + ("Advanced upper-limb / shoulder exposure" if lang == "en" else "Προχωρημένη έκθεση άνω άκρου / ώμου"))
        st.caption(
            "Only flag these when the actual task exposure exists. They should not be inferred from ordinary computer use."
            if lang == "en" else
            "Ενεργοποίησέ τα μόνο όταν υπάρχει πραγματική έκθεση στη συγκεκριμένη εργασία. Δεν πρέπει να συμπεραίνονται από απλή χρήση υπολογιστή."
        )
        high_repetition = st.checkbox(t["repetition"])
        hand_force = st.checkbox(t["force"])
        forearm_rotation = st.checkbox(t["forearm_rotation"])
        arm_elevation = st.checkbox(t["arm_elevation"])
    else:
        high_repetition = hand_force = forearm_rotation = arm_elevation = False

    if not quick_mode:
        with st.expander(t["psychosocial"], expanded=False):
            job_demand = st.checkbox(t["job_demand"])
            low_control = st.checkbox(t["low_control"])
            low_support = st.checkbox(t["low_support"])
    else:
        job_demand = low_control = low_support = False

# ---------------------------------------------------------------------
# 3. Workstation fit
# ---------------------------------------------------------------------
with tabs[2]:
    st.subheader(t["workstation_title"])
    st.caption(
        "Measured values are compared with body-fit/design references. Differences are prompts for observation, not validated disease thresholds."
        if lang == "en" else
        "Οι μετρήσεις συγκρίνονται με σωματομετρικές και σχεδιαστικές τιμές αναφοράς. Οι αποκλίσεις αποτελούν ενδείξεις για περαιτέρω παρατήρηση και όχι επικυρωμένα όρια κινδύνου νόσου."
    )
    c1, c2, c3 = st.columns(3)
    seat_height = c1.number_input(t["chair_actual"], min_value=0.0, max_value=70.0, value=0.0, step=0.5)
    desk_height = c2.number_input(t["desk_actual"], min_value=0.0, max_value=120.0, value=0.0, step=0.5)
    monitor_distance = c3.number_input(t["monitor_distance"], min_value=0.0, max_value=150.0, value=0.0, step=1.0)

    c1, c2 = st.columns(2)
    monitor_top = c1.selectbox(
        t["monitor_top"],
        ["not_measured", "above", "eye", "slightly_below", "well_below"],
        format_func=lambda x: {
            "not_measured": "—",
            "above": t["monitor_above"], "eye": t["monitor_eye"],
            "slightly_below": t["monitor_below"], "well_below": t["monitor_low"],
        }[x],
    )
    glare = c2.selectbox(
        t["glare"], [None, True, False],
        format_func=lambda v: "—" if v is None else (t["yes"] if v else t["no"]),
    )
    c1, c2 = st.columns(2)
    keyboard_close = yes_no_unknown(t["keyboard_close"], "keyboard_close")
    forearm_support = yes_no_unknown(t["forearm_support"], "forearm_support")

    st.markdown("#### " + t["reference_fit"])
    r1, r2 = st.columns(2)
    r1.metric(
        "Seat/body reference" if lang == "en" else "Αναφορά ύψους έδρας",
        f"{anthro.popliteal_cm:.1f} cm",
        anthro.source_popliteal if lang == "en" else ("άμεση μέτρηση" if anthro.source_popliteal == "direct" else "εκτίμηση")
    )
    r2.metric(
        "Work-surface/elbow reference" if lang == "en" else "Αναφορά επιφάνειας εργασίας / αγκώνα",
        f"{anthro.desk_reference_cm:.1f} cm",
        "body-fit reference" if lang == "en" else "σωματομετρική αναφορά"
    )
    st.info(
        "Monitor v2 uses actual viewing distance + vertical position rather than a universal 'eye level − 5 cm' formula."
        if lang == "en" else
        "Στη v2 η οθόνη αξιολογείται με την πραγματική απόσταση θέασης και την κατακόρυφη θέση της και όχι με έναν καθολικό τύπο «ύψος ματιών − 5 cm»."
    )

    with st.expander("DSE environment" if lang == "en" else "Περιβάλλον εργασίας με οθόνη", expanded=False):
        e1, e2 = st.columns(2)
        lighting_ok = yes_no_unknown("Lighting is adequate" if lang == "en" else "Ο φωτισμός είναι επαρκής", "lighting_ok")
        noise_ok = yes_no_unknown("Noise is acceptable for the task" if lang == "en" else "Ο θόρυβος είναι αποδεκτός για τη συγκεκριμένη εργασία", "noise_ok")
        thermal_ok = yes_no_unknown("Thermal comfort is acceptable" if lang == "en" else "Η θερμική άνεση είναι αποδεκτή", "thermal_ok")
        software_ok = yes_no_unknown("Software/interface supports the task without avoidable strain" if lang == "en" else "Το λογισμικό/η διεπαφή υποστηρίζει την εργασία χωρίς περιττή επιβάρυνση", "software_ok")
        st.caption(
            "These fields support a broader EU display-screen assessment and are kept separate from musculoskeletal disease scoring."
            if lang == "en"
            else "Τα πεδία αυτά υποστηρίζουν μια πληρέστερη αξιολόγηση εργασίας με οθόνη σύμφωνα με την ευρωπαϊκή προσέγγιση και παραμένουν ξεχωριστά από οποιαδήποτε βαθμολόγηση μυοσκελετικής νόσου."
        )

# ---------------------------------------------------------------------
# 4. Chair fit / adjustability
# ---------------------------------------------------------------------
with tabs[3]:
    st.subheader(t["chair_title"])
    st.info(t["chair_screen_note"])
    st.caption(
        "Reference: EN 1335 / ISO 9241-5 design principles. Full conformity requires the official standard and its complete test method."
        if lang == "en"
        else "Αναφορά: αρχές σχεδιασμού EN 1335 / ISO 9241-5. Η πλήρης συμμόρφωση απαιτεί το επίσημο πρότυπο και την ολοκληρωμένη μέθοδο δοκιμής του."
    )
    chair_completed = st.toggle("Assessment completed" if lang == "en" else "Ο έλεγχος καρέκλας ολοκληρώθηκε", value=False, key="chair_completed")
    chair_results: dict[str, bool] = {}
    if chair_completed:
        ca, cb = st.columns(2)
        for idx, (key, label) in enumerate(CHAIR_FIT_ITEMS):
            with (ca if idx < (len(CHAIR_FIT_ITEMS)+1)//2 else cb):
                display_label = label if lang == "en" else CHAIR_FIT_LABELS_EL.get(key, label)
                chair_results[key] = st.checkbox(display_label, value=False, key=f"chair_{key}")
        chair_failed = [key for key, ok in chair_results.items() if not ok]
        st.metric("Items confirmed" if lang == "en" else "Κριτήρια που πληρούνται", f"{len(CHAIR_FIT_ITEMS)-len(chair_failed)} / {len(CHAIR_FIT_ITEMS)}")
        st.caption(
            "No compliance percentage or clinical risk band is generated."
            if lang == "en"
            else "Δεν παράγεται ποσοστό συμμόρφωσης ή κλινική κατηγορία κινδύνου."
        )
    else:
        chair_failed = []
        st.caption(
            "Mark the section as completed before chair findings are included in the report."
            if lang == "en"
            else "Σημείωσε ότι ο έλεγχος ολοκληρώθηκε ώστε τα ευρήματα της καρέκλας να συμπεριληφθούν στην αναφορά."
        )

    with st.expander(
        "EN 1335 Type A reference dimensions — audit note" if lang == "en" else "Διαστάσεις αναφοράς EN 1335 Type A — σημείωση ελέγχου",
        expanded=False,
    ):
        for k, v in EN1335_TYPE_A_REFERENCE.items():
            label = k.replace("_", " ") if lang == "en" else EN1335_LABELS_EL.get(k, k)
            st.write(f"- **{label}:** {v}")
        st.caption(
            "Displayed for reference only; the screen above is not a product-certification procedure."
            if lang == "en"
            else "Οι τιμές εμφανίζονται μόνο ως αναφορά. Η παραπάνω ενότητα δεν αποτελεί διαδικασία πιστοποίησης προϊόντος."
        )

# ---------------------------------------------------------------------
# 5. Posture & movement
# ---------------------------------------------------------------------
with tabs[4]:
    st.subheader(t["posture_title"])
    st.info(t["posture_note"])
    st.caption(
        "Greek version: terminology and criteria follow ELINYAE office/DSE guidance. English version follows OSHA Computer Workstations guidance."
        if lang == "en"
        else "Η αξιολόγηση βασίζεται στις οδηγίες του ΕΛΙΝΥΑΕ για εργασία με οθόνες και εργονομικό σχεδιασμό. Δεν χρησιμοποιείται ένα μοναδικό «ιδανικό» σύνολο γωνιών για όλους."
    )

    posture_completed = st.toggle(
        "Assessment completed" if lang == "en" else "Η παρατήρηση στάσης ολοκληρώθηκε",
        value=False,
        key="posture_completed",
    )
    posture_out: list[dict] = []

    if posture_completed:
        posture_checks = [
            (
                "dynamic_posture",
                "Working posture changes regularly; prolonged static sitting is avoided.",
                "Η στάση του σώματος αλλάζει τακτικά κατά τη διάρκεια της εργασίας και αποφεύγεται η παρατεταμένη στατική καθιστή θέση.",
            ),
            (
                "back_supported",
                "The back is supported and the trunk is not held for prolonged periods in a markedly bent or twisted posture.",
                "Η πλάτη υποστηρίζεται επαρκώς και ο κορμός δεν παραμένει για μεγάλο διάστημα σε έντονη κάμψη ή στροφή.",
            ),
            (
                "shoulders_relaxed",
                "Shoulders are relaxed and not elevated.",
                "Οι ώμοι είναι χαλαροί και δεν παραμένουν ανυψωμένοι.",
            ),
            (
                "elbows_close",
                "Elbows remain close to the body.",
                "Οι αγκώνες παραμένουν κοντά στο σώμα.",
            ),
            (
                "elbow_angle",
                "During keyboard use, elbows are about 90–120°.",
                "Κατά τη χρήση του πληκτρολογίου, οι αγκώνες είναι περίπου στις 90° ή σε ελαφρά μεγαλύτερη γωνία.",
            ),
            (
                "wrists_neutral",
                "Wrists and hands remain straight and in-line with the forearms.",
                "Οι καρποί παραμένουν σε ουδέτερη θέση, χωρίς έκταση ή ωλένια απόκλιση.",
            ),
            (
                "forearms_supported",
                "Forearms are adequately supported without elevating the shoulders.",
                "Οι πήχεις/αντιβράχια στηρίζονται επαρκώς χωρίς να προκαλείται ανύψωση των ώμων.",
            ),
            (
                "feet_supported",
                "Feet are fully supported on the floor or on a stable footrest.",
                "Τα πέλματα στηρίζονται πλήρως στο δάπεδο ή σε σταθερό υποπόδιο.",
            ),
            (
                "leg_clearance",
                "There is adequate clearance for the thighs, knees, legs and feet.",
                "Υπάρχει επαρκής ελεύθερος χώρος για τους μηρούς, τα γόνατα, τις κνήμες και τα πέλματα.",
            ),
        ]

        posture_results: dict[str, bool | None] = {}
        for key, label_en, label_el in posture_checks:
            result = yes_no_unknown(label_en if lang == "en" else label_el, f"posture_{key}")
            posture_results[key] = result
            if result is False:
                posture_out.append({
                    "key": key,
                    "label": label_en if lang == "en" else label_el,
                    "value": "needs_review",
                    "reference": "ELINYAE" if lang == "el" else "OSHA",
                })

        dynamic = posture_results.get("dynamic_posture")
        movement_variability = "good" if dynamic is True else ("limited" if dynamic is False else "not_assessed")

        if movement_variability == "limited":
            st.warning(
                "Prolonged static posture was flagged. Postural variation should be increased."
                if lang == "en"
                else "Εντοπίστηκε παρατεταμένη στατική στάση. Χρειάζεται μεγαλύτερη εναλλαγή θέσεων και κίνηση κατά τη διάρκεια της εργασίας."
            )

        with st.expander(
            "Optional angle recording" if lang == "en" else "Προαιρετική καταγραφή γωνίας αγκώνα",
            expanded=False,
        ):
            elbow_angle_observed = st.number_input(
                "Observed elbow angle (°)" if lang == "en" else "Μετρημένη γωνία αγκώνα (°)",
                min_value=0,
                max_value=180,
                value=0,
                step=5,
                help=(
                    "0 = not measured. OSHA uses 90–120° as a neutral reference."
                    if lang == "en"
                    else "0 = δεν μετρήθηκε. Το ΕΛΙΝΥΑΕ αναφέρει περίπου 90° ή ελαφρά μεγαλύτερη γωνία κατά τη χρήση πληκτρολογίου."
                ),
            )
            if elbow_angle_observed > 0:
                st.caption(
                    f"Recorded: {elbow_angle_observed}°. This value is documented, not converted into a disease-risk score."
                    if lang == "en"
                    else f"Καταγράφηκαν {elbow_angle_observed}°. Η μέτρηση τεκμηριώνεται αλλά δεν μετατρέπεται σε βαθμολογία κινδύνου νόσου."
                )
    else:
        movement_variability = "not_assessed"
        st.caption(
            "Mark the section as completed before posture findings are included in the report."
            if lang == "en"
            else "Σημείωσε ότι η παρατήρηση στάσης ολοκληρώθηκε ώστε τα σχετικά ευρήματα να συμπεριληφθούν στην αναφορά."
        )

# ---------------------------------------------------------------------
# 6. ROSA
# ---------------------------------------------------------------------
with tabs[5]:
    st.subheader(t["rosa_title"])
    st.info(t["rosa_note"])
    st.caption(
        "Scoring follows the ROSA worksheet structure developed by Sonne, Villalta & Andrews. "
        "The visual worksheet shown below is the TuMeke rendition based on ROSA."
        if lang == "en"
        else
        "Η βαθμολόγηση ακολουθεί τη δομή του ROSA των Sonne, Villalta & Andrews. "
        "Ο οπτικός οδηγός που εμφανίζεται παρακάτω είναι η έκδοση worksheet της TuMeke που βασίζεται στο ROSA."
    )

    ROSA_WORKSHEET_IMAGE = "https://raw.githubusercontent.com/ErgoFit-Intelligence/Ergofit-Intelligence/main/assets/rosa_banner.jpg"
    ROSA_WORKSHEET_PDF = "https://7488314.fs1.hubspotusercontent-na1.net/hubfs/7488314/Infosheets/ROSA_Worksheet_TuMeke.pdf"

    with st.expander(
        "Visual ROSA worksheet & icons" if lang == "en" else "Οπτικός οδηγός ROSA με τα εικονίδια",
        expanded=True,
    ):
        # Render via the browser instead of st.image/Pillow. Streamlit executes
        # tab contents eagerly, so a PIL decoding error here would otherwise
        # crash the whole app even when the ROSA tab is not selected.
        st.markdown(
            f"""
            <div style="width:100%; margin:0 0 12px 0;">
              <img
                src="{ROSA_WORKSHEET_IMAGE}?v=2"
                alt="ErgoFit ROSA checklist"
                style="width:100%; height:auto; display:block; border-radius:10px; border:1px solid #d9dde6;"
              />
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"[Open worksheet PDF]({ROSA_WORKSHEET_PDF})"
            if lang == "en"
            else f"[Άνοιγμα του worksheet σε PDF]({ROSA_WORKSHEET_PDF})"
        )
        st.caption(
            "Use the pictures as the primary visual reference; the controls below reproduce the same scoring logic in an interactive format."
            if lang == "en"
            else
            "Χρησιμοποίησε τις εικόνες ως βασικό οπτικό οδηγό. Τα πεδία από κάτω ακολουθούν την ίδια λογική βαθμολόγησης σε διαδραστική μορφή."
        )

    rosa_completed = st.toggle(
        "Assessment completed" if lang == "en" else "Η αξιολόγηση ROSA ολοκληρώθηκε",
        value=False,
        key="rosa_completed",
    )

    if rosa_completed:
        # -----------------------------
        # Section A — Chair
        # -----------------------------
        st.markdown("### A · Chair" if lang == "en" else "### A · Καρέκλα")

        st.markdown("#### A.1 · Chair height" if lang == "en" else "#### A.1 · Ύψος καρέκλας")
        a1_choice = st.radio(
            "Select the picture/condition that best matches the worker" if lang == "en"
            else "Επίλεξε την εικόνα/κατάσταση που ταιριάζει περισσότερο στον εργαζόμενο",
            ["neutral", "too_low", "too_high", "no_foot_contact"],
            format_func=lambda v: {
                "neutral": "Knees at about 90° (+1)" if lang == "en" else "Γόνατα περίπου στις 90° (+1)",
                "too_low": "Chair too low: knee angle <90° (+2)" if lang == "en"
                           else "Η καρέκλα είναι πολύ χαμηλά: γωνία γόνατος <90° (+2)",
                "too_high": "Chair too high: knee angle >90° (+2)" if lang == "en"
                            else "Η καρέκλα είναι πολύ ψηλά: γωνία γόνατος >90° (+2)",
                "no_foot_contact": "No foot contact with the floor (+3)" if lang == "en"
                                   else "Τα πέλματα δεν ακουμπούν στο δάπεδο (+3)",
            }[v],
            key="rosa_a1_primary",
        )
        a1_primary = {"neutral": 1, "too_low": 2, "too_high": 2, "no_foot_contact": 3}[a1_choice]
        a1_extra = 0
        if st.checkbox(
            "Insufficient space under the desk / cannot comfortably move the legs (+1)" if lang == "en"
            else "Ανεπαρκής χώρος κάτω από το γραφείο / δεν υπάρχει επαρκής χώρος κίνησης των ποδιών (+1)",
            key="rosa_a1_cramp",
        ):
            a1_extra += 1
        if st.checkbox(
            "Chair height is non-adjustable (+1)" if lang == "en"
            else "Το ύψος της καρέκλας δεν ρυθμίζεται (+1)",
            key="rosa_a1_nonadj",
        ):
            a1_extra += 1
        a1 = a1_primary + a1_extra

        st.markdown("#### A.2 · Seat pan depth" if lang == "en" else "#### A.2 · Βάθος έδρας")
        a2_primary = st.radio(
            "Select seat-depth condition" if lang == "en" else "Επίλεξε την κατάσταση που περιγράφει το βάθος της έδρας",
            [1, 2, 3],
            format_func=lambda v: {
                1: "About 3 in / 7–8 cm between the back of the knee and seat edge (+1)" if lang == "en"
                   else "Περίπου 7–8 cm κενό μεταξύ του πίσω μέρους του γόνατος και της άκρης της έδρας (+1)",
                2: "Too long: less than ~7–8 cm of space (+2)" if lang == "en"
                   else "Πολύ βαθιά έδρα: κενό μικρότερο από περίπου 7–8 cm (+2)",
                3: "Too short: more than ~7–8 cm of space (+2)" if lang == "en"
                   else "Πολύ ρηχή έδρα: κενό μεγαλύτερο από περίπου 7–8 cm (+2)",
            }[v],
            key="rosa_a2_primary",
        )
        # ROSA gives both too-long and too-short conditions a score of 2.
        a2 = 1 if a2_primary == 1 else 2
        if st.checkbox(
            "Seat depth is non-adjustable (+1)" if lang == "en"
            else "Το βάθος της έδρας δεν ρυθμίζεται (+1)",
            key="rosa_a2_nonadj",
        ):
            a2 += 1

        st.markdown("#### A.3 · Armrests" if lang == "en" else "#### A.3 · Μπράτσα καρέκλας")
        a3_primary = st.radio(
            "Select armrest condition" if lang == "en" else "Επίλεξε την κατάσταση που περιγράφει τα μπράτσα",
            [1, 2],
            format_func=lambda v: {
                1: "Elbows supported in line with the shoulders; shoulders relaxed (+1)" if lang == "en"
                   else "Οι αγκώνες στηρίζονται κοντά στο σώμα και οι ώμοι είναι χαλαροί (+1)",
                2: "Armrests too high or too low; shoulders shrugged or arms unsupported (+2)" if lang == "en"
                   else "Τα μπράτσα είναι πολύ ψηλά ή πολύ χαμηλά: οι ώμοι ανυψώνονται ή τα χέρια δεν στηρίζονται (+2)",
            }[v],
            key="rosa_a3_primary",
        )
        a3 = a3_primary
        if st.checkbox(
            "Armrest surface is hard/damaged (+1)" if lang == "en"
            else "Η επιφάνεια των μπράτσων είναι σκληρή ή φθαρμένη (+1)",
            key="rosa_a3_hard",
        ):
            a3 += 1
        if st.checkbox(
            "Armrests are too far apart (+1)" if lang == "en"
            else "Τα μπράτσα απέχουν υπερβολικά μεταξύ τους (+1)",
            key="rosa_a3_wide",
        ):
            a3 += 1
        if st.checkbox(
            "Armrests are non-adjustable (+1)" if lang == "en"
            else "Τα μπράτσα δεν ρυθμίζονται (+1)",
            key="rosa_a3_nonadj",
        ):
            a3 += 1

        st.markdown("#### A.4 · Back support" if lang == "en" else "#### A.4 · Στήριξη πλάτης")
        a4_choice = st.radio(
            "Select back-support condition" if lang == "en" else "Επίλεξε την κατάσταση που περιγράφει τη στήριξη της πλάτης",
            ["adequate", "no_lumbar", "bad_angle", "no_back_support"],
            format_func=lambda v: {
                "adequate": "Adequate lumbar support; backrest about 95–110° (+1)" if lang == "en"
                            else "Επαρκής οσφυϊκή στήριξη και κλίση πλάτης περίπου 95–110° (+1)",
                "no_lumbar": "No lumbar support OR lumbar support not positioned in the small of the back (+2)" if lang == "en"
                             else "Δεν υπάρχει οσφυϊκή στήριξη ή δεν είναι σωστά τοποθετημένη στην οσφυϊκή περιοχή (+2)",
                "bad_angle": "Backrest angled too far back (>110°) or too far forward (<95°) (+2)" if lang == "en"
                             else "Η πλάτη είναι υπερβολικά πίσω (>110°) ή υπερβολικά μπροστά (<95°) (+2)",
                "no_back_support": "No back support / stool / worker leaning forward without support (+3)" if lang == "en"
                                   else "Χωρίς στήριξη πλάτης, π.χ. σκαμπό ή εργασία με τον κορμό μπροστά χωρίς στήριξη (+3)",
            }[v],
            key="rosa_a4_primary",
        )
        a4 = {"adequate": 1, "no_lumbar": 2, "bad_angle": 2, "no_back_support": 3}[a4_choice]
        if st.checkbox(
            "Work surface too high; shoulders shrugged (+1)" if lang == "en"
            else "Η επιφάνεια εργασίας είναι πολύ ψηλά και προκαλεί ανύψωση των ώμων (+1)",
            key="rosa_a4_highdesk",
        ):
            a4 += 1
        if st.checkbox(
            "Backrest is non-adjustable (+1)" if lang == "en"
            else "Η πλάτη της καρέκλας δεν ρυθμίζεται (+1)",
            key="rosa_a4_nonadj",
        ):
            a4 += 1

        dur_chair = duration_selector("dur_chair")

        a_cols = st.columns(5)
        a_cols[0].metric("A.1", a1)
        a_cols[1].metric("A.2", a2)
        a_cols[2].metric("A.3", a3)
        a_cols[3].metric("A.4", a4)
        a_cols[4].metric("Duration" if lang == "en" else "Διάρκεια", f"{dur_chair:+d}")

        st.divider()

        # -----------------------------
        # Section B — Monitor & Phone
        # -----------------------------
        st.markdown("### B · Monitor & phone" if lang == "en" else "### B · Οθόνη & τηλέφωνο")

        st.markdown("#### B.1 · Monitor" if lang == "en" else "#### B.1 · Οθόνη")
        b1_primary = st.radio(
            "Select monitor-height condition" if lang == "en" else "Επίλεξε την κατάσταση που περιγράφει καλύτερα το ύψος της οθόνης",
            [1, 2, 3],
            format_func=lambda v: {
                1: "Arm's-length distance (about 40–75 cm) and screen at eye level (+1)" if lang == "en"
                   else "Απόσταση περίπου όσο το μήκος του χεριού (40–75 cm) και οθόνη στο ύψος των ματιών (+1)",
                2: "Monitor too low (below ~30° viewing angle) (+2)" if lang == "en"
                   else "Η οθόνη είναι πολύ χαμηλά (κάτω από περίπου 30°) (+2)",
                3: "Monitor too high, producing neck extension (+3)" if lang == "en"
                   else "Η οθόνη είναι πολύ ψηλά και προκαλεί έκταση του αυχένα (+3)",
            }[v],
            key="rosa_b1_primary",
        )
        b1 = b1_primary
        if st.checkbox("Monitor too far away (+1)" if lang == "en" else "Η οθόνη βρίσκεται πολύ μακριά (+1)", key="rosa_b1_far"):
            b1 += 1
        if st.checkbox("Neck rotation >30° (+1)" if lang == "en" else "Στροφή αυχένα >30° (+1)", key="rosa_b1_twist"):
            b1 += 1
        if st.checkbox("Glare on screen (+1)" if lang == "en" else "Θάμβωση / αντανακλάσεις στην οθόνη (+1)", key="rosa_b1_glare"):
            b1 += 1
        if st.checkbox("Documents used without a document holder (+1)" if lang == "en" else "Χρήση εγγράφων χωρίς βάση στήριξης εγγράφων (+1)", key="rosa_b1_docs"):
            b1 += 1
        dur_monitor = duration_selector("dur_monitor")

        st.markdown("#### B.2 · Phone" if lang == "en" else "#### B.2 · Τηλέφωνο")
        b2 = 1
        st.caption(
            "Baseline: headset or one-hand phone use with a neutral neck posture (+1). Add any conditions that apply."
            if lang == "en"
            else "Βασική συνθήκη: headset ή χρήση τηλεφώνου με το ένα χέρι και ουδέτερη θέση αυχένα (+1). Πρόσθεσε όσα από τα παρακάτω ισχύουν."
        )
        if st.checkbox("Phone is too far to reach (>30 cm) (+2)" if lang == "en" else "Το τηλέφωνο βρίσκεται πολύ μακριά (>30 cm) (+2)", key="rosa_b2_far"):
            b2 += 2
        if st.checkbox("Phone held between neck and shoulder (+2)" if lang == "en" else "Το τηλέφωνο συγκρατείται μεταξύ αυχένα και ώμου (+2)", key="rosa_b2_hold"):
            b2 += 2
        if st.checkbox("No hands-free option available (+1)" if lang == "en" else "Δεν υπάρχει δυνατότητα hands-free / ακουστικών (+1)", key="rosa_b2_hands"):
            b2 += 1
        dur_phone = duration_selector("dur_phone")

        st.divider()

        # -----------------------------
        # Section C — Mouse & Keyboard
        # -----------------------------
        st.markdown("### C · Mouse & keyboard" if lang == "en" else "### C · Ποντίκι & πληκτρολόγιο")

        st.markdown("#### C.1 · Mouse" if lang == "en" else "#### C.1 · Ποντίκι")
        c1r = 1
        st.caption(
            "Baseline: mouse in line with the shoulder (+1). Add any conditions that apply."
            if lang == "en"
            else "Βασική συνθήκη: το ποντίκι βρίσκεται στην ίδια γραμμή με τον ώμο (+1). Πρόσθεσε όσα από τα παρακάτω ισχύουν."
        )
        if st.checkbox("Reaching to use the mouse (+2)" if lang == "en" else "Χρειάζεται τέντωμα του χεριού για χρήση του ποντικιού (+2)", key="rosa_c1_reach"):
            c1r += 2
        if st.checkbox("Mouse and keyboard are on different surfaces/heights (+2)" if lang == "en" else "Ποντίκι και πληκτρολόγιο βρίσκονται σε διαφορετικές επιφάνειες/ύψη (+2)", key="rosa_c1_diff"):
            c1r += 2
        if st.checkbox("Pinch grip on mouse (+1)" if lang == "en" else "Το ποντίκι χρησιμοποιείται με λαβή τύπου pinch grip (+1)", key="rosa_c1_pinch"):
            c1r += 1
        if st.checkbox("Palmrest in front of the mouse (+1)" if lang == "en" else "Υπάρχει στήριγμα παλάμης μπροστά από το ποντίκι (+1)", key="rosa_c1_palm"):
            c1r += 1
        dur_mouse = duration_selector("dur_mouse")

        st.markdown("#### C.2 · Keyboard" if lang == "en" else "#### C.2 · Πληκτρολόγιο")
        c2r = 1
        st.caption(
            "Baseline: wrists straight and shoulders relaxed (+1). Add any conditions that apply."
            if lang == "en"
            else "Βασική συνθήκη: οι καρποί είναι ευθείς/ουδέτεροι και οι ώμοι χαλαροί (+1). Πρόσθεσε όσα από τα παρακάτω ισχύουν."
        )
        if st.checkbox(
            "Wrist extension / positive keyboard angle (>15° wrist extension) (+2)" if lang == "en"
            else "Έκταση καρπού / θετική κλίση πληκτρολογίου (>15° έκταση καρπού) (+2)",
            key="rosa_c2_ext",
        ):
            c2r += 2
        if st.checkbox("Wrist deviation while typing (+1)" if lang == "en" else "Απόκλιση καρπού κατά την πληκτρολόγηση (+1)", key="rosa_c2_dev"):
            c2r += 1
        if st.checkbox("Keyboard too high; shoulders shrugged (+1)" if lang == "en" else "Το πληκτρολόγιο είναι πολύ ψηλά και οι ώμοι ανυψώνονται (+1)", key="rosa_c2_high"):
            c2r += 1
        if st.checkbox("Reaching to overhead items (+1)" if lang == "en" else "Χρειάζεται προσέγγιση αντικειμένων πάνω από το ύψος των ώμων (+1)", key="rosa_c2_over"):
            c2r += 1
        if st.checkbox("Keyboard platform is non-adjustable (+1)" if lang == "en" else "Η βάση/επιφάνεια του πληκτρολογίου δεν ρυθμίζεται (+1)", key="rosa_c2_nonadj"):
            c2r += 1
        dur_keyboard = duration_selector("dur_keyboard")

        rosa = compute_rosa(
            a1, a2, a3, a4, dur_chair,
            b1, b2, dur_monitor, dur_phone,
            c1r, c2r, dur_mouse, dur_keyboard,
        )

        st.divider()
        st.markdown("### " + ("ROSA results" if lang == "en" else "Αποτελέσματα ROSA"))
        r1, r2, r3 = st.columns(3)
        r1.metric("Chair ROSA" if lang == "en" else "ROSA καρέκλας", f"{rosa['chair']} / 10")
        r2.metric("Monitor & peripherals" if lang == "en" else "Οθόνη & περιφερειακά", f"{rosa['monitor_peripherals']} / 10")
        r3.metric("ROSA final" if lang == "en" else "Τελικό ROSA", f"{rosa['final']} / 10")

        st.caption(
            f"Section B: {rosa['section_b']} · Section C: {rosa['section_c']}"
            if lang == "en"
            else f"Ενότητα B: {rosa['section_b']} · Ενότητα C: {rosa['section_c']}"
        )

        if rosa["final"] >= 5:
            st.error(
                "ROSA action level reached (≥5): further ergonomic investigation/intervention indicated."
                if lang == "en"
                else "Επιτεύχθηκε το επίπεδο δράσης ROSA (≥5): ενδείκνυται περαιτέρω εργονομική διερεύνηση και παρέμβαση."
            )
        else:
            st.success(
                "ROSA below the validated action level of 5. This is not a clinical 'low disease risk' category."
                if lang == "en"
                else "Το ROSA βρίσκεται κάτω από το τεκμηριωμένο επίπεδο δράσης 5. Αυτό δεν σημαίνει κλινικά «χαμηλό κίνδυνο νόσου»."
            )
    else:
        rosa = {
            "chair": 0, "section_b": 0, "section_c": 0,
            "monitor_peripherals": 0, "final": 0, "action": "not_assessed"
        }
        st.caption(
            "Mark ROSA as completed before a score is included in the report."
            if lang == "en"
            else "Σημείωσε ότι η αξιολόγηση ROSA ολοκληρώθηκε ώστε η βαθμολογία να συμπεριληφθεί στην αναφορά."
        )

# ---------------------------------------------------------------------
# Build context, findings and recommendations before evidence/summary tabs.
# ---------------------------------------------------------------------
ctx = {
    "subject_id": subject_id,
    "assessment_date": str(assessment_date),
    "age": age,
    "sex": sex,
    "height": height,
    "weight": weight,
    "bmi": bmi_value,
    "diabetes": diabetes,
    "smoking": smoking,
    "sleep_problem": sleep_problem,
    "exercise": exercise,
    "pa_minutes": pa_minutes,
    "symptom_regions": symptom_regions,
    "symptom_details": symptom_details,
    "symptom_severity": symptom_severity,
    "symptom_interference": symptom_interference,
    "digital_eye_strain": digital_eye_strain,
    "computer_hours": computer_hours,
    "mouse_hours": mouse_hours,
    "sitting_hours": sitting_hours,
    "long_sitting_bout": long_sitting_bout,
    "active_breaks": active_breaks,
    "high_repetition": high_repetition,
    "hand_force": hand_force,
    "forearm_rotation": forearm_rotation,
    "arm_elevation": arm_elevation,
    "job_demand": job_demand,
    "low_control": low_control,
    "low_support": low_support,
    "seat_height": seat_height,
    "desk_height": desk_height,
    "monitor_distance": monitor_distance,
    "monitor_top": monitor_top,
    "keyboard_close": keyboard_close,
    "forearm_support": forearm_support,
    "glare": glare,
    "lighting_ok": lighting_ok,
    "noise_ok": noise_ok,
    "thermal_ok": thermal_ok,
    "software_ok": software_ok,
    "seat_reference": anthro.popliteal_cm,
    "desk_reference": anthro.desk_reference_cm,
    "anthropometry": {
        "popliteal_cm": anthro.popliteal_cm,
        "seated_elbow_cm": anthro.seated_elbow_cm,
        "seated_eye_cm": anthro.seated_eye_cm,
        "sources": {
            "popliteal": anthro.source_popliteal,
            "elbow": anthro.source_elbow,
            "eye": anthro.source_eye,
        },
    },
    "chair_failed": chair_failed,
    "posture_out": posture_out,
    "movement_variability": movement_variability,
    "rosa_final": rosa["final"],
    "rosa": rosa,
}
findings = build_findings(ctx, lang)
recommendations = build_recommendations(ctx, findings, lang)
relevant_evidence_ids = evidence_ids_for_context(ctx, findings)
relevant_evidence = get_many(relevant_evidence_ids)

# ---------------------------------------------------------------------
# 7. Evidence profile
# ---------------------------------------------------------------------
with tabs[6]:
    st.subheader(t["evidence_title"])
    st.info(t["evidence_note"])
    if findings:
        st.markdown("### " + ("Assessment findings" if lang == "en" else "Ευρήματα αξιολόγησης"))
        for f in findings:
            finding_card(f, lang)
            st.write("")
    else:
        st.success(
            "No priority exposure finding was generated from the entered data."
            if lang == "en"
            else "Δεν προέκυψε εύρημα έκθεσης υψηλής προτεραιότητας από τα δεδομένα που καταχωρίστηκαν."
        )

    st.markdown("### " + ("Evidence linked to this assessment" if lang == "en" else "Επιστημονική τεκμηρίωση που συνδέεται με αυτή την αξιολόγηση"))
    if relevant_evidence:
        for e in relevant_evidence:
            evidence_card(e, lang)
            st.write("")
    else:
        st.caption(
            "No evidence cards are triggered until relevant exposure/symptom information is entered."
            if lang == "en"
            else "Δεν εμφανίζονται κάρτες τεκμηρίωσης μέχρι να καταχωριστούν σχετικά στοιχεία έκθεσης ή συμπτωμάτων."
        )

    with st.expander("Full v2 evidence registry" if lang == "en" else "Πλήρες μητρώο επιστημονικής τεκμηρίωσης v2", expanded=False):
        st.caption(
            "Registry entries are deliberately separated by outcome and population; they are not pooled into a universal points score."
            if lang == "en"
            else "Οι εγγραφές διατηρούνται ξεχωριστές ανά έκβαση και πληθυσμό και δεν συγχωνεύονται σε μία καθολική βαθμολογία πόντων."
        )
        for e in EVIDENCE.values():
            evidence_card(e, lang)
            st.write("")

# ---------------------------------------------------------------------
# 8. Summary & export
# ---------------------------------------------------------------------
with tabs[7]:
    st.subheader(t["summary_title"])
    subject_display = subject_id.strip() or ("Unidentified worker" if lang == "en" else "Χωρίς αναγνωριστικό")
    st.markdown(
        f"""<div class="ef-summary"><div class="ef-kicker">ERGOFIT INTELLIGENCE V2</div>
        <h3 style="margin:.2rem 0!important">{subject_display}</h3>
        <div>{assessment_date} · BMI {bmi_value:.1f} · ROSA {rosa['final']}/10</div>
        <div style="margin-top:8px;color:#5b6475">{"No disease probability is generated. The report separates ergonomic exposure, symptoms, context and intervention evidence." if lang == "en" else "Δεν υπολογίζεται πιθανότητα νόσου. Η αναφορά διαχωρίζει την εργονομική έκθεση, τα συμπτώματα, το πλαίσιο υγείας και την τεκμηρίωση των παρεμβάσεων."}</div></div>""",
        unsafe_allow_html=True,
    )

    s1, s2, s3 = st.columns(3)
    s1.metric("Priority findings" if lang == "en" else "Ευρήματα υψηλής προτεραιότητας", sum(f.status == "priority" for f in findings))
    s2.metric("Attention findings" if lang == "en" else "Ευρήματα που χρειάζονται προσοχή", sum(f.status == "attention" for f in findings))
    if rosa["final"] > 0:
        s3.metric(
            "ROSA",
            f"{rosa['final']} / 10",
            ("Action level" if rosa['final'] >= 5 else "Below action level")
            if lang == "en"
            else ("Επίπεδο δράσης" if rosa['final'] >= 5 else "Κάτω από το επίπεδο δράσης")
        )
    else:
        s3.metric("ROSA", "Not assessed" if lang == "en" else "Δεν αξιολογήθηκε")

    st.markdown("### " + ("Key findings" if lang == "en" else "Κύρια ευρήματα"))
    if findings:
        for f in findings:
            finding_card(f, lang)
            st.write("")
    else:
        st.success(
            "No priority ergonomic exposure was identified from the entered information."
            if lang == "en"
            else "Δεν εντοπίστηκε εργονομική έκθεση υψηλής προτεραιότητας από τα στοιχεία που καταχωρίστηκαν."
        )

    st.markdown("### " + ("Recommendations" if lang == "en" else "Συστάσεις"))
    for r in recommendations:
        recommendation_card(r, lang)
        st.write("")

    report_payload = {
        "version": "2.0.0-alpha",
        "intended_purpose": "Office ergonomic decision support; not diagnosis or individual disease-probability prediction",
        "assessment": ctx,
        "findings": [f.to_dict() for f in findings],
        "recommendations": [r.to_dict() for r in recommendations],
        "evidence": [e.to_dict() for e in relevant_evidence],
    }
    report_json = json.dumps(report_payload, ensure_ascii=False, indent=2)
    st.download_button(
        t["download_json"],
        data=report_json.encode("utf-8"),
        file_name=f"ergofit_v2_{subject_id.strip() or 'assessment'}.json",
        mime="application/json",
    )
    st.caption(t["print_note"])

    st.divider()
    st.markdown("#### " + ("Optional secure backend" if lang == "en" else "Προαιρετική ασφαλής αποθήκευση"))
    try:
        backend_cfg = st.secrets.get("backend", {})
        webhook_url = backend_cfg.get("webhook_url", "") if backend_cfg else ""
    except Exception:
        webhook_url = ""

    if not webhook_url:
        st.info(t["backend_disabled"])
    else:
        consent = st.checkbox(t["consent"], key="backend_consent")
        if st.button(t["submit"], type="primary", disabled=not consent):
            ok, msg = submit_payload(webhook_url, report_payload)
            (st.success if ok else st.error)(msg)

st.divider()
st.caption(
    "ErgoFit Intelligence v2 · Scientific architecture: evidence registry + separate exposure/symptom/intervention domains · Alpha build"
    if lang == "en"
    else "ErgoFit Intelligence v2 · Επιστημονική αρχιτεκτονική: μητρώο τεκμηρίωσης + ξεχωριστοί τομείς έκθεσης/συμπτωμάτων/παρεμβάσεων · Έκδοση alpha"
)
