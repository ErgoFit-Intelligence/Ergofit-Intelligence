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
            pop_direct = a1.number_input(t["popliteal"], min_value=0.0, max_value=65.0, value=0.0, step=0.5)
            elbow_direct = a2.number_input(t["elbow_height"], min_value=0.0, max_value=40.0, value=0.0, step=0.5)
            eye_direct = a3.number_input(t["eye_height"], min_value=0.0, max_value=100.0, value=0.0, step=0.5)

    anthro = reference_from_stature(height, sex, pop_direct, elbow_direct, eye_direct)
    st.markdown("#### " + ("Body-fit references" if lang == "en" else "Σωματομετρικές τιμές αναφοράς"))
    a1, a2, a3 = st.columns(3)
    _src = lambda s: s if lang == "en" else ("άμεση μέτρηση" if s == "direct" else "εκτίμηση")
    a1.metric("Popliteal height" if lang == "en" else "Ύψος ιγνυακής χώρας", f"{anthro.popliteal_cm:.1f} cm", _src(anthro.source_popliteal))
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
    symptom_regions = st.multiselect(t["symptom_regions"], region_options, format_func=lambda x: region_labels[x])
    c1, c2 = st.columns(2)
    symptom_severity = c1.slider(t["severity"], 0, 10, 0)
    symptom_interference = c2.checkbox(t["interference"])
    digital_eye_strain = st.checkbox("Digital eye strain / visual fatigue" if lang == "en" else "Ψηφιακή κόπωση ματιών / οπτική κόπωση")

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
        c1, c2 = st.columns(2)
        high_repetition = c1.checkbox(t["repetition"])
        hand_force = c2.checkbox(t["force"])
        c1, c2 = st.columns(2)
        forearm_rotation = c1.checkbox(t["forearm_rotation"])
        arm_elevation = c2.checkbox(t["arm_elevation"])
    else:
        high_repetition = hand_force = forearm_rotation = arm_elevation = False

    if not quick_mode:
        with st.expander(t["psychosocial"], expanded=False):
            c1, c2, c3 = st.columns(3)
            job_demand = c1.checkbox(t["job_demand"])
            low_control = c2.checkbox(t["low_control"])
            low_support = c3.checkbox(t["low_support"])
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
                chair_results[key] = st.checkbox(display_label, value=True, key=f"chair_{key}")
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
    posture_completed = st.toggle("Assessment completed" if lang == "en" else "Η παρατήρηση στάσης ολοκληρώθηκε", value=False, key="posture_completed")
    posture_out: list[dict] = []
    if posture_completed:
        for key, label, lo, hi, default in POSTURE_REFERENCES:
            c1, c2, c3 = st.columns([3, 1, 2])
            display_label = label if lang == "en" else POSTURE_LABELS_EL.get(key, label)
            c1.markdown(f"**{display_label}**")
            c1.caption(f"Reference: {lo}° to {hi}°" if lang == "en" else f"Τιμή αναφοράς: {lo}° έως {hi}°")
            min_value = -45 if "wrist" in key else 0
            angle = c2.number_input("°", min_value=min_value, max_value=180, value=default, step=5, key=f"posture_{key}", label_visibility="collapsed")
            if lo <= angle <= hi:
                c3.success(f"{angle}° · within reference" if lang == "en" else f"{angle}° · εντός τιμής αναφοράς")
            else:
                c3.warning(f"{angle}° · review" if lang == "en" else f"{angle}° · χρειάζεται έλεγχο")
                posture_out.append({"key": key, "label": display_label, "value": angle, "reference": [lo, hi]})

        movement_variability = st.selectbox(
            "Movement / postural variability" if lang == "en" else "Μεταβλητότητα στάσης / κίνησης",
            ["not_assessed", "good", "limited"],
            format_func=lambda x: {
                "not_assessed": "—",
                "good": "Frequent / good" if lang == "en" else "Συχνή / καλή",
                "limited": "Limited / static" if lang == "en" else "Περιορισμένη / στατική",
            }[x],
        )
        if movement_variability == "limited":
            st.warning(
                "Static posture flagged. Duration and variation should be addressed even when individual angles look acceptable."
                if lang == "en"
                else "Εντοπίστηκε περιορισμένη μεταβλητότητα στάσης. Η διάρκεια και η εναλλαγή θέσεων πρέπει να αξιολογηθούν ακόμη και όταν οι επιμέρους γωνίες είναι αποδεκτές."
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
    st.caption("Source: Sonne, Villalta & Andrews (2012), Applied Ergonomics 43(1):98–108.")

    rosa_completed = st.toggle("Assessment completed" if lang == "en" else "Η αξιολόγηση ROSA ολοκληρώθηκε", value=False, key="rosa_completed")
    if rosa_completed:
        st.markdown("### A · Chair" if lang == "en" else "### A · Καρέκλα")
        a1c, a2c = st.columns(2)
        with a1c:
            st.markdown("**A.1 Chair height**" if lang == "en" else "**A.1 Ύψος καρέκλας**")
            a1 = 1
            a1 += rosa_checkbox("Πολύ χαμηλή", "Too low", 2, "rosa_a1_low")
            a1 += rosa_checkbox("Πολύ υψηλή", "Too high", 2, "rosa_a1_high")
            a1 += rosa_checkbox("Πόδια χωρίς στήριξη", "No foot support", 3, "rosa_a1_nofoot")
            a1 += rosa_checkbox("Περιορισμένος χώρος κάτω από γραφείο", "Insufficient under-desk space", 1, "rosa_a1_cramp")
            a1 += rosa_checkbox("Μη ρυθμιζόμενη", "Non-adjustable", 1, "rosa_a1_nonadj")
            st.markdown("**A.3 Armrests**" if lang == "en" else "**A.3 Μπράτσα καρέκλας**")
            a3 = 1
            a3 += rosa_checkbox("Πολύ ψηλά/χαμηλά", "Too high/low", 2, "rosa_a3_high")
            a3 += rosa_checkbox("Σκληρή/φθαρμένη επιφάνεια", "Hard/damaged surface", 1, "rosa_a3_hard")
            a3 += rosa_checkbox("Πολύ μεγάλη απόσταση", "Too wide apart", 1, "rosa_a3_wide")
            a3 += rosa_checkbox("Μη ρυθμιζόμενα", "Non-adjustable", 1, "rosa_a3_nonadj")
        with a2c:
            st.markdown("**A.2 Seat pan depth**" if lang == "en" else "**A.2 Βάθος έδρας**")
            a2 = 1
            a2 += rosa_checkbox("Πολύ βαθιά έδρα", "Pan too long", 2, "rosa_a2_long")
            a2 += rosa_checkbox("Πολύ ρηχή έδρα", "Pan too short", 2, "rosa_a2_short")
            a2 += rosa_checkbox("Μη ρυθμιζόμενο βάθος", "Depth non-adjustable", 1, "rosa_a2_nonadj")
            st.markdown("**A.4 Back support**" if lang == "en" else "**A.4 Στήριξη πλάτης**")
            a4 = 1
            a4 += rosa_checkbox("Ανεπαρκής οσφυϊκή στήριξη", "No/poor lumbar support", 2, "rosa_a4_lumbar")
            a4 += rosa_checkbox("Υπερβολική/ανεπαρκής κλίση πλάτης", "Backrest angle outside ROSA reference", 2, "rosa_a4_angle")
            a4 += rosa_checkbox("Χωρίς στήριξη πλάτης / σκύψιμο εμπρός", "No back support / leaning forward", 3, "rosa_a4_noback")
            a4 += rosa_checkbox("Επιφάνεια πολύ ψηλά", "Work surface too high", 1, "rosa_a4_highdesk")
            a4 += rosa_checkbox("Πλάτη μη ρυθμιζόμενη", "Backrest non-adjustable", 1, "rosa_a4_nonadj")
        dur_chair = duration_selector("dur_chair")
    
        st.divider()
        st.markdown("### B · Monitor & phone" if lang == "en" else "### B · Οθόνη & τηλέφωνο")
        b1c, b2c = st.columns(2)
        with b1c:
            st.markdown("**B.1 Monitor**" if lang == "en" else "**B.1 Οθόνη**")
            b1 = 1
            b1 += rosa_checkbox("Οθόνη πολύ χαμηλά", "Monitor too low", 2, "rosa_b1_low")
            b1 += rosa_checkbox("Οθόνη πολύ μακριά", "Monitor too far", 1, "rosa_b1_far")
            b1 += rosa_checkbox("Οθόνη πολύ ψηλά", "Monitor too high", 3, "rosa_b1_high")
            b1 += rosa_checkbox("Στροφή αυχένα >30°", "Neck twist >30°", 1, "rosa_b1_twist")
            b1 += rosa_checkbox("Θάμβωση / αντανάκλαση", "Glare", 1, "rosa_b1_glare")
            b1 += rosa_checkbox("Έγγραφα χωρίς βάση στήριξης", "Documents without holder", 1, "rosa_b1_docs")
            dur_monitor = duration_selector("dur_monitor")
        with b2c:
            st.markdown("**B.2 Phone**" if lang == "en" else "**B.2 Τηλέφωνο**")
            b2 = 1
            b2 += rosa_checkbox("Τηλέφωνο μακριά", "Phone too far", 2, "rosa_b2_far")
            b2 += rosa_checkbox("Κράτημα με αυχένα/ώμο", "Neck/shoulder hold", 2, "rosa_b2_hold")
            b2 += rosa_checkbox("Χωρίς δυνατότητα hands-free", "No hands-free option", 1, "rosa_b2_hands")
            dur_phone = duration_selector("dur_phone")
    
        st.divider()
        st.markdown("### C · Mouse & keyboard" if lang == "en" else "### C · Ποντίκι & πληκτρολόγιο")
        c1c, c2c = st.columns(2)
        with c1c:
            st.markdown("**C.1 Mouse**" if lang == "en" else "**C.1 Ποντίκι**")
            c1r = 1
            c1r += rosa_checkbox("Τέντωμα χεριού προς το ποντίκι", "Reaching to mouse", 2, "rosa_c1_reach")
            c1r += rosa_checkbox("Ποντίκι/πληκτρολόγιο σε διαφορετικά επίπεδα", "Mouse/keyboard on different surfaces", 2, "rosa_c1_diff")
            c1r += rosa_checkbox("Λαβή με τα δάκτυλα (pinch grip)", "Pinch grip", 1, "rosa_c1_pinch")
            c1r += rosa_checkbox("Στήριγμα παλάμης μπροστά από το ποντίκι", "Palmrest in front of mouse", 1, "rosa_c1_palm")
            dur_mouse = duration_selector("dur_mouse")
        with c2c:
            st.markdown("**C.2 Keyboard**" if lang == "en" else "**C.2 Πληκτρολόγιο**")
            c2r = 1
            c2r += rosa_checkbox("Έκταση καρπού / θετική κλίση πληκτρολογίου", "Wrist extension / positive keyboard angle", 2, "rosa_c2_ext")
            c2r += rosa_checkbox("Απόκλιση καρπού", "Wrist deviation", 1, "rosa_c2_dev")
            c2r += rosa_checkbox("Πληκτρολόγιο πολύ ψηλά", "Keyboard too high", 1, "rosa_c2_high")
            c2r += rosa_checkbox("Τέντωμα χεριού προς αντικείμενα πάνω από το ύψος των ώμων", "Reaching overhead", 1, "rosa_c2_over")
            c2r += rosa_checkbox("Μη ρυθμιζόμενη βάση πληκτρολογίου", "Platform non-adjustable", 1, "rosa_c2_nonadj")
            dur_keyboard = duration_selector("dur_keyboard")
    
        rosa = compute_rosa(
            a1, a2, a3, a4, dur_chair,
            b1, b2, dur_monitor, dur_phone,
            c1r, c2r, dur_mouse, dur_keyboard,
        )
        r1, r2, r3 = st.columns(3)
        r1.metric("Chair ROSA" if lang == "en" else "ROSA καρέκλας", f"{rosa['chair']} / 10")
        r2.metric("Monitor & peripherals" if lang == "en" else "Οθόνη & περιφερειακά", f"{rosa['monitor_peripherals']} / 10")
        r3.metric("ROSA final" if lang == "en" else "Τελικό ROSA", f"{rosa['final']} / 10")
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
