from __future__ import annotations

import base64
import json
from datetime import date
from pathlib import Path

import streamlit as st

from ergofit.assessment.engine import build_findings, evidence_ids_for_context
from ergofit.assessment.recommendations import build_recommendations
from ergofit.backend import (
    list_assessments_webapp,
    load_assessment_webapp,
    save_assessment_webapp,
)
from ergofit.i18n import get_text
from ergofit.slovenian import translate
from ergofit.science.anthropometry import bmi, reference_from_stature
from ergofit.science.evidence_registry import EVIDENCE, get_many
from ergofit.science.rosa import compute_rosa
from ergofit.science.standards import (
    CHAIR_FIT_ITEMS,
    CHAIR_FIT_LABELS_EL,
    CHAIR_FIT_LABELS_SL,
    EN1335_LABELS_EL,
    EN1335_LABELS_SL,
    EN1335_TYPE_A_REFERENCE,
    POSTURE_LABELS_EL,
    POSTURE_LABELS_SL,
    POSTURE_REFERENCES,
)
from ergofit.ui.components import evidence_card, finding_card, group_evidence_by_region, recommendation_card
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
        ["el", "en", "sl"],
        format_func=lambda x: {"el": "🇬🇷 Ελληνικά", "en": "🇬🇧 English", "sl": "🇸🇮 Slovenščina"}[x],
        horizontal=True,
    )
    quick_mode = st.toggle(
        "⚡ Quick Mode" if st.session_state.lang == "en"
        else "⚡ Hitra ocena" if st.session_state.lang == "sl"
        else "⚡ Γρήγορη αξιολόγηση",
        value=False,
    )
    st.caption(
        "Quick Mode hides direct anthropometry, psychosocial context and advanced mechanical exposures."
        if st.session_state.lang == "en"
        else "Hitra ocena skrije neposredne antropometrične meritve, psihosocialni kontekst in napredne mehanske izpostavljenosti."
        if st.session_state.lang == "sl"
        else "Η Γρήγορη αξιολόγηση κρύβει τις άμεσες σωματομετρικές μετρήσεις, το ψυχοκοινωνικό πλαίσιο και τις προχωρημένες μηχανικές εκθέσεις."
    )
    st.divider()
    st.markdown("**ErgoFit Intelligence v2**")
    st.caption(
        "Evidence architecture: exposure → symptoms → intervention. No disease probability score."
        if st.session_state.lang == "en"
        else "Arhitektura dokazov: izpostavljenost → simptomi → ukrep. Orodje ne izračunava verjetnosti bolezni."
        if st.session_state.lang == "sl"
        else "Αρχιτεκτονική τεκμηρίωσης: έκθεση → συμπτώματα → παρέμβαση. Δεν υπολογίζεται πιθανότητα νόσου."
    )

lang = st.session_state.lang
t = get_text(lang)

def _google_sheets_config():
    try:
        cfg = dict(st.secrets.get("google_sheets", {}))
    except Exception:
        cfg = {}
    webapp_url = str(cfg.get("webapp_url", "") or "").strip()
    token = str(cfg.get("token", "") or "").strip()
    ready = bool(webapp_url and token)
    return ready, webapp_url, token

sheets_ready, sheets_webapp_url, sheets_token = _google_sheets_config()

hero(t["hero_title"], t["hero_sub"])

with st.expander(t["purpose"], expanded=False):
    st.markdown(t["purpose_body"])


def yes_no_unknown(label: str, key: str, help_text: str | None = None):
    options = [None, True, False]
    return st.selectbox(
        label,
        options,
        format_func=lambda v: (
            ("— Ni ocenjeno —" if lang == "sl" else "— Not assessed —") if v is None and lang in {"en", "sl"} else
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
    labels_sl = {
        -1: "<30 min neprekinjeno ali <1 h/dan (−1)",
        0: "30–60 min neprekinjeno ali 1–4 h/dan (0)",
        1: ">1 h neprekinjeno ali >4 h/dan (+1)",
    }
    labels = labels_el if lang == "el" else (labels_sl if lang == "sl" else labels_en)
    return st.radio(
        "Διάρκεια χρήσης" if lang == "el" else ("Trajanje uporabe" if lang == "sl" else "Duration of use"),
        options,
        format_func=lambda x: labels[x],
        key=key,
    )


def rosa_checkbox(label_el: str, label_en: str, points: int, key: str) -> int:
    label = translate(lang, label_en, label_el)
    return points if st.checkbox(f"{label} (+{points})", key=key) else 0


def symptom_duration_label(value: str) -> str:
    labels = {
        "not_recorded": "—",
        "<1_week": translate(lang, "<1 week", "<1 εβδομάδα"),
        "1_6_weeks": translate(lang, "1–6 weeks", "1–6 εβδομάδες"),
        "6_12_weeks": translate(lang, "6–12 weeks", "6–12 εβδομάδες"),
        ">12_weeks": translate(lang, ">12 weeks", ">12 εβδομάδες"),
    }
    return labels.get(value, "—")


def symptom_frequency_label(value: str) -> str:
    labels = {
        "not_recorded": "—",
        "occasional": translate(lang, "Occasional", "Περιστασιακά"),
        "1_2_days_week": translate(lang, "1–2 days/week", "1–2 ημέρες/εβδομάδα"),
        "3_5_days_week": translate(lang, "3–5 days/week", "3–5 ημέρες/εβδομάδα"),
        "daily": translate(lang, "Daily / almost daily", "Καθημερινά / σχεδόν καθημερινά"),
    }
    return labels.get(value, "—")


def region_exposure_text(region: str, ctx: dict) -> str:
    factors: list[str] = []
    rosa_final = int((ctx.get("rosa") or {}).get("final", ctx.get("rosa_final", 0)) or 0)
    posture_keys = {item.get("key") for item in (ctx.get("posture_out") or []) if isinstance(item, dict)}
    chair_issues = bool(ctx.get("chair_failed"))

    if region in {"Neck", "Shoulder(s)"}:
        if max(float(ctx.get("computer_hours", 0)), float(ctx.get("mouse_hours", 0))) > 4:
            factors.append(translate(lang, "computer/mouse >4 h", "Η/Υ ή ποντίκι >4 ώρες"))
        if ctx.get("forearm_support") is False:
            factors.append(translate(lang, "limited forearm support", "περιορισμένη στήριξη αντιβραχίων"))
        if region == "Shoulder(s)" and ctx.get("arm_elevation"):
            factors.append(translate(lang, "sustained arm elevation", "παρατεταμένη ανύψωση βραχίονα"))
        if {"shoulders_relaxed", "elbows_close", "forearms_supported"} & posture_keys:
            factors.append(translate(lang, "posture finding", "εύρημα στάσης"))
    elif region == "Elbow / forearm / wrist / hand":
        if ctx.get("high_repetition"):
            factors.append(translate(lang, "high repetition", "υψηλή επανάληψη"))
        if ctx.get("hand_force"):
            factors.append(translate(lang, "hand force", "δύναμη χεριού"))
        if ctx.get("forearm_rotation"):
            factors.append(translate(lang, "forearm rotation", "στροφή αντιβραχίου"))
        if ctx.get("forearm_support") is False:
            factors.append(translate(lang, "limited forearm support", "περιορισμένη στήριξη αντιβραχίων"))
    elif region == "Low back":
        if float(ctx.get("sitting_hours", 0)) >= 6:
            factors.append(translate(lang, "high sitting exposure*", "υψηλή καθιστική έκθεση*"))
        if ctx.get("long_sitting_bout") in {"60–120 min", ">120 min"}:
            factors.append(translate(lang, "long static bouts", "μεγάλα στατικά διαστήματα"))
        if chair_issues:
            factors.append(translate(lang, "chair-fit findings", "ευρήματα προσαρμογής καρέκλας"))
        if {"dynamic_posture", "back_supported"} & posture_keys:
            factors.append(translate(lang, "posture/movement finding", "εύρημα στάσης/κίνησης"))
    elif region == "Lower limbs":
        if {"feet_supported", "leg_clearance"} & posture_keys:
            factors.append(translate(lang, "support/clearance finding", "εύρημα στήριξης/ελεύθερου χώρου"))

    if rosa_final >= 5 and region in {"Neck", "Shoulder(s)", "Elbow / forearm / wrist / hand", "Low back"}:
        factors.append(translate(lang, "ROSA action level", "ROSA σε επίπεδο δράσης"))

    if not factors:
        return translate(lang, "No specific ergonomic factor identified", "Δεν εντοπίστηκε ειδικός εργονομικός παράγοντας")
    return " · ".join(dict.fromkeys(factors))


def region_action_text(region: str, item: dict, ctx: dict) -> str:
    severity = int(item.get("severity", 0) or 0)
    has_symptom = severity > 0
    work_impact = (
        item.get("interference") is True
        or item.get("work_modification") is True
        or int(item.get("absence_days_4w", 0) or 0) > 0
    )
    persistent_or_recurrent = (
        item.get("duration") == ">12_weeks"
        or item.get("previous_episode") is True
        or item.get("frequency") == "daily"
    )
    exposure_present = not region_exposure_text(region, ctx).startswith(
        translate(lang, "No specific", "Δεν εντοπίστηκε")
    )

    if has_symptom and (work_impact or persistent_or_recurrent):
        return (
            translate(lang, "Ergonomic intervention + follow-up; consider clinical/occupational-health review if persistent or worsening", "Εργονομική παρέμβαση + επανέλεγχος· εξέταση από κατάλληλο επαγγελματία υγείας αν επιμένει ή επιδεινώνεται")
        )
    if has_symptom and exposure_present:
        return translate(lang, "Ergonomic review + symptom monitoring", "Εργονομικός έλεγχος + παρακολούθηση συμπτωμάτων")
    if has_symptom:
        return translate(lang, "Monitor symptoms and reassess if they persist/worsen", "Παρακολούθηση συμπτωμάτων και επανέλεγχος αν επιμένουν/επιδεινώνονται")
    if exposure_present:
        return translate(lang, "Prevention / exposure management", "Πρόληψη / διαχείριση έκθεσης")
    return translate(lang, "Maintain current conditions", "Διατήρηση καλών συνθηκών")


# ---------------------------------------------------------------------
# Client profile — shared by both assessments
# ---------------------------------------------------------------------
st.markdown("## " + (translate(lang, "1 · Client details", "1 · Στοιχεία πελάτη")))
st.caption(
    translate(lang, "These details identify the person being assessed and are shared by the first and second assessment.", "Τα στοιχεία αυτά αφορούν τον ίδιο πελάτη/εργαζόμενο και χρησιμοποιούνται τόσο στην 1η όσο και στη 2η αξιολόγηση.")
)

p1, p2, p3 = st.columns([1.3, 1.2, 1.2])
subject_id = p1.text_input(
    translate(lang, "Client name or code", "Όνομα ή κωδικός πελάτη"),
    value="",
    placeholder="π.χ. COS-024",
    key="client_subject_id",
)
company = p2.text_input(translate(lang, "Company", "Εταιρεία"), value="", key="client_company")
department = p3.text_input(translate(lang, "Department / area", "Τμήμα / χώρος"), value="", key="client_department")

p1, p2, p3 = st.columns([1.4, 1, 1])
job_title = p1.text_input(translate(lang, "Job title", "Θέση εργασίας"), value="", key="client_job_title")
age = p2.number_input(t["age"], min_value=18, max_value=80, value=35, key="client_age")
sex_options = ["female", "male", "other"]
sex = p3.selectbox(
    t["sex"],
    sex_options,
    format_func=lambda x: {"female": t["female"], "male": t["male"], "other": t["other"]}[x],
    key="client_sex",
)

p1, p2 = st.columns(2)
height = p1.number_input(t["height"], min_value=140.0, max_value=210.0, value=175.0, step=0.5, key="client_height")
weight = p2.number_input(t["weight"], min_value=40.0, max_value=200.0, value=75.0, step=0.5, key="client_weight")
bmi_value = bmi(weight, height)
st.caption(
    f"ITM: {bmi_value:.1f} kg/m² — prikazan kot zdravstveni kontekst, ne kot ergonomska ocena."
    if lang == "sl"
    else f"BMI: {bmi_value:.1f} kg/m² — shown as health context, not as an ergonomic score."
    if lang == "en"
    else f"ΔΜΣ: {bmi_value:.1f} kg/m² — εμφανίζεται ως στοιχείο υγείας και όχι ως εργονομική βαθμολογία."
)

st.divider()
st.markdown("## " + (translate(lang, "2 · Assessment", "2 · Αξιολόγηση")))
assessment_stage = st.radio(
    translate(lang, "Choose assessment", "Επίλεξε αξιολόγηση"),
    ["baseline", "followup"],
    format_func=lambda x: (
        translate(lang, "1st Assessment", "1η Αξιολόγηση")
        if x == "baseline"
        else translate(lang, "2nd Assessment / Reassessment", "2η Αξιολόγηση / Επαναξιολόγηση")
    ),
    horizontal=True,
    key="assessment_stage",
)

baseline_report = None
baseline_assessment = {}
parent_assessment_id = ""
interventions_notes = ""

if assessment_stage == "followup":
    st.markdown("### " + (translate(lang, "Connection with the 1st assessment", "Σύνδεση με την 1η αξιολόγηση")))

    if sheets_ready:
        if subject_id.strip():
            try:
                previous = [
                    r for r in list_assessments_webapp(
                        sheets_webapp_url,
                        sheets_token,
                        subject_id.strip(),
                    )
                    if str(r.get("assessment_stage", "")) == "baseline"
                ]
            except Exception as exc:
                previous = []
                st.error(
                    f"Google Sheets ni bilo mogoče prebrati: {exc}"
                    if lang == "sl"
                    else f"Could not read Google Sheets: {exc}"
                    if lang == "en"
                    else f"Δεν ήταν δυνατή η ανάγνωση του Google Sheets: {exc}"
                )

            if previous:
                options = [str(r.get("assessment_id", "")) for r in previous]
                labels = {
                    str(r.get("assessment_id", "")): (
                        f"{r.get('assessment_date', '—')} · ROSA {r.get('rosa_final', '—')} · {r.get('assessment_id', '')}"
                    )
                    for r in previous
                }
                selected_baseline = st.selectbox(
                    translate(lang, "Select the 1st assessment", "Επίλεξε την 1η αξιολόγηση"),
                    options,
                    format_func=lambda x: labels.get(x, x),
                    key="selected_baseline_assessment",
                )
                try:
                    baseline_report = load_assessment_webapp(
                        sheets_webapp_url,
                        sheets_token,
                        selected_baseline,
                    )
                except Exception as exc:
                    baseline_report = None
                    st.error(
                        f"Izbrane ocene ni bilo mogoče naložiti: {exc}"
                        if lang == "sl"
                        else f"Could not load the selected assessment: {exc}"
                        if lang == "en"
                        else f"Δεν ήταν δυνατή η φόρτωση της επιλεγμένης αξιολόγησης: {exc}"
                    )
                if baseline_report:
                    baseline_assessment = baseline_report.get("assessment", {}) or {}
                    parent_assessment_id = selected_baseline
                    st.success(
                        translate(lang, "The 1st assessment was loaded automatically. The final section will compare it with the reassessment.", "Η 1η αξιολόγηση φορτώθηκε αυτόματα. Στην τελική ενότητα θα συγκριθεί με την επαναξιολόγηση.")
                    )
            else:
                st.info(
                    translate(lang, "No 1st assessment was found for this client code.", "Δεν βρέθηκε 1η αξιολόγηση για αυτόν τον κωδικό πελάτη.")
                )
        else:
            st.info(
                translate(lang, "Enter the client name/code above first.", "Συμπλήρωσε πρώτα το όνομα ή τον κωδικό πελάτη.")
            )
    else:
        st.warning(
            translate(lang, "Google Sheets automatic connection is not active in the deployed app yet. Until it is activated, the 1st assessment can be loaded from its JSON backup.", "Η αυτόματη σύνδεση του deployed app με το Google Sheets δεν έχει ενεργοποιηθεί ακόμη. Μέχρι να ενεργοποιηθεί, η 1η αξιολόγηση μπορεί να φορτωθεί από το αντίγραφο JSON.")
        )
        baseline_file = st.file_uploader(
            translate(lang, "1st assessment JSON", "Αρχείο 1ης αξιολόγησης (JSON)"),
            type=["json"],
            key="baseline_report_upload",
        )
        if baseline_file is not None:
            try:
                baseline_report = json.loads(baseline_file.getvalue().decode("utf-8"))
                if not isinstance(baseline_report, dict) or "assessment" not in baseline_report:
                    raise ValueError("invalid report structure")
                baseline_assessment = baseline_report.get("assessment", {}) or {}
                parent_assessment_id = str(
                    baseline_assessment.get("assessment_id", "")
                    or baseline_report.get("assessment_id", "")
                    or ""
                )
            except Exception:
                baseline_report = None
                baseline_assessment = {}
                st.error(
                    translate(lang, "The file could not be read as a valid ErgoFit assessment.", "Το αρχείο δεν αναγνωρίστηκε ως έγκυρη αξιολόγηση ErgoFit.")
                )

    interventions_notes = st.text_area(
        translate(lang, "Interventions implemented between the two assessments", "Παρεμβάσεις που εφαρμόστηκαν μεταξύ 1ης και 2ης αξιολόγησης"),
        placeholder=(
            translate(lang, "e.g. chair adjustment, monitor repositioning, task changes, active breaks...", "π.χ. ρύθμιση καρέκλας, αλλαγή θέσης οθόνης, αλλαγές στην οργάνωση της εργασίας, ενεργά διαλείμματα...")
        ),
        key="interventions_notes",
    )

stage_heading = (
    translate(lang, "1st Assessment", "1η Αξιολόγηση")
    if assessment_stage == "baseline"
    else translate(lang, "2nd Assessment / Reassessment", "2η Αξιολόγηση / Επαναξιολόγηση")
)
st.markdown(f"### {stage_heading}")
st.caption(
    translate(lang, "Complete all sections below for this assessment.", "Συμπλήρωσε όλες τις παρακάτω ενότητες για τη συγκεκριμένη αξιολόγηση.")
)

# Ordered workflow; Streamlit evaluates all tabs so later tabs can consume earlier values.
tabs = st.tabs([
    t["tab_profile"], t["tab_symptoms"], t["tab_workstation"], t["tab_chair"],
    t["tab_posture"], t["tab_rosa"], t["tab_evidence"], t["tab_summary"],
])

# ---------------------------------------------------------------------
# 1. Health context & anthropometry
# ---------------------------------------------------------------------
with tabs[0]:
    st.subheader(t["profile_title"])

    assessment_date = st.date_input(t["assessment_date"], value=date.today(), key="assessment_date")

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
    st.markdown("#### " + (translate(lang, "Body-fit references", "Σωματομετρικές τιμές αναφοράς")))
    a1, a2, a3 = st.columns(3)
    _src = lambda s: (
        s if lang == "en"
        else ("neposredna meritev" if s == "direct" else "ocena") if lang == "sl"
        else ("άμεση μέτρηση" if s == "direct" else "εκτίμηση")
    )
    a1.metric(translate(lang, "Popliteal height", "Ύψος πίσω από το γόνατο"), f"{anthro.popliteal_cm:.1f} cm", _src(anthro.source_popliteal))
    a2.metric(translate(lang, "Seated elbow height", "Ύψος αγκώνα από την έδρα"), f"{anthro.seated_elbow_cm:.1f} cm", _src(anthro.source_elbow))
    a3.metric(translate(lang, "Seated eye height", "Ύψος ματιών από την έδρα"), f"{anthro.seated_eye_cm:.1f} cm", _src(anthro.source_eye))

    c1, c2, c3 = st.columns(3)
    diabetes = c1.checkbox(t["diabetes"])
    smoking = c2.checkbox(t["smoking"])
    sleep_problem = c3.checkbox(t["sleep_problem"])

    c1, c2 = st.columns(2)
    exercise = c1.checkbox(t["exercise"])
    pa_minutes = c2.number_input(t["pa_minutes"], min_value=0, max_value=1500, value=120, step=10)
    st.caption(
        translate(lang, "Physical activity and exercise are recorded as wellbeing/intervention context. They do not subtract points from a disease score.", "Η φυσική δραστηριότητα και η άσκηση καταγράφονται ως στοιχεία ευεξίας και παρέμβασης. Δεν αφαιρούν πόντους από κάποια βαθμολογία κινδύνου νόσου.")
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
        placeholder=translate(lang, "Choose options", "Επίλεξε περιοχές"),
    )

    symptom_details: dict[str, dict] = {}
    if symptom_regions:
        st.markdown("#### " + (translate(lang, "Symptoms by body region", "Συμπτώματα ανά περιοχή σώματος")))
        st.caption(
            translate(lang, "Record intensity and work interference separately for each selected region.", "Κατέγραψε ξεχωριστά την ένταση και το αν επηρεάζεται η εργασία για κάθε περιοχή που επέλεξες.")
        )
        for region in symptom_regions:
            region_label = region_labels[region]
            st.markdown(f"**{region_label}**")

            severity = st.slider(
                f"{t['severity']} — {region_label}",
                0, 10, 0,
                key=f"severity_{region}",
            )

            c1, c2 = st.columns(2)
            duration = c1.selectbox(
                translate(lang, "How long has this problem been present?", "Πόσο καιρό υπάρχει αυτό το πρόβλημα;"),
                ["not_recorded", "<1_week", "1_6_weeks", "6_12_weeks", ">12_weeks"],
                format_func=lambda v: {
                    "not_recorded": translate(lang, "— Not recorded —", "— Δεν καταγράφηκε —"),
                    "<1_week": translate(lang, "<1 week", "<1 εβδομάδα"),
                    "1_6_weeks": translate(lang, "1–6 weeks", "1–6 εβδομάδες"),
                    "6_12_weeks": translate(lang, "6–12 weeks", "6–12 εβδομάδες"),
                    ">12_weeks": translate(lang, ">12 weeks", ">12 εβδομάδες"),
                }[v],
                key=f"duration_{region}",
            )
            frequency = c2.selectbox(
                translate(lang, "How often is it present?", "Πόσο συχνά εμφανίζεται;"),
                ["not_recorded", "occasional", "1_2_days_week", "3_5_days_week", "daily"],
                format_func=lambda v: {
                    "not_recorded": translate(lang, "— Not recorded —", "— Δεν καταγράφηκε —"),
                    "occasional": translate(lang, "Occasionally", "Περιστασιακά"),
                    "1_2_days_week": translate(lang, "1–2 days/week", "1–2 ημέρες/εβδομάδα"),
                    "3_5_days_week": translate(lang, "3–5 days/week", "3–5 ημέρες/εβδομάδα"),
                    "daily": translate(lang, "Daily / almost daily", "Καθημερινά / σχεδόν καθημερινά"),
                }[v],
                key=f"frequency_{region}",
            )

            c1, c2 = st.columns(2)
            previous_episode = c1.selectbox(
                translate(lang, "Previous similar episode?", "Έχει υπάρξει παρόμοιο επεισόδιο στο παρελθόν;"),
                [None, True, False],
                format_func=lambda v: "—" if v is None else (
                    t["yes"] if v else t["no"]
                ),
                key=f"previous_episode_{region}",
            )
            interference = c2.selectbox(
                translate(lang, "Does it interfere with work?", "Επηρεάζει την εργασία;"),
                [None, True, False],
                format_func=lambda v: "—" if v is None else (
                    t["yes"] if v else t["no"]
                ),
                key=f"interference_{region}",
            )

            c1, c2 = st.columns(2)
            work_modification = c1.selectbox(
                translate(lang, "Do you change pace/task/posture because of it?", "Αλλάζεις ρυθμό, εργασία ή στάση εξαιτίας του συμπτώματος;"),
                [None, True, False],
                format_func=lambda v: "—" if v is None else (
                    t["yes"] if v else t["no"]
                ),
                key=f"work_modification_{region}",
            )
            absence_days_4w = c2.number_input(
                translate(lang, "Work absence due to this symptom in the last 4 weeks (days)", "Απουσία από την εργασία λόγω του συμπτώματος τις τελευταίες 4 εβδομάδες (ημέρες)"),
                min_value=0,
                max_value=28,
                value=0,
                step=1,
                key=f"absence_days_{region}",
            )

            symptom_details[region] = {
                "label": region_label,
                "severity": severity,
                "duration": duration,
                "frequency": frequency,
                "previous_episode": previous_episode,
                "interference": interference,
                "work_modification": work_modification,
                "absence_days_4w": absence_days_4w,
            }
            st.caption(
                translate(lang, "These fields describe the symptom history and functional impact. They are not converted into a personal disease-probability score.", "Τα πεδία αυτά περιγράφουν την πορεία του συμπτώματος και τη λειτουργική του επίδραση. Δεν μετατρέπονται σε προσωπική πιθανότητα νόσου.")
            )
            st.divider()

    symptom_severity = max((d["severity"] for d in symptom_details.values()), default=0)
    symptom_interference = any(d["interference"] for d in symptom_details.values()) if symptom_details else False

    digital_eye_strain = st.checkbox(translate(lang, "Digital eye strain / visual fatigue", "Κόπωση ματιών από τη χρήση της οθόνης"))

    st.markdown("#### " + (translate(lang, "Work exposure", "Εργασιακή έκθεση")))
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
        st.markdown("#### " + (translate(lang, "Advanced upper-limb / shoulder exposure", "Προχωρημένη έκθεση άνω άκρου / ώμου")))
        st.caption(
            translate(lang, "Only flag these when the actual task exposure exists. They should not be inferred from ordinary computer use.", "Ενεργοποίησέ τα μόνο όταν υπάρχει πραγματική έκθεση στη συγκεκριμένη εργασία. Δεν πρέπει να συμπεραίνονται από απλή χρήση υπολογιστή.")
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
        translate(lang, "Measured values are compared with body-fit/design references. Differences are prompts for observation, not validated disease thresholds.", "Οι μετρήσεις συγκρίνονται με σωματομετρικές και σχεδιαστικές τιμές αναφοράς. Οι αποκλίσεις αποτελούν ενδείξεις για περαιτέρω παρατήρηση και όχι επικυρωμένα όρια κινδύνου νόσου.")
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
        translate(lang, "Seat/body reference", "Αναφορά ύψους έδρας"),
        f"{anthro.popliteal_cm:.1f} cm",
        anthro.source_popliteal if lang == "en" else (
            "neposredna meritev" if anthro.source_popliteal == "direct" else "ocena"
        ) if lang == "sl" else (
            "άμεση μέτρηση" if anthro.source_popliteal == "direct" else "εκτίμηση"
        )
    )
    r2.metric(
        translate(lang, "Work-surface/elbow reference", "Αναφορά επιφάνειας εργασίας / αγκώνα"),
        f"{anthro.desk_reference_cm:.1f} cm",
        translate(lang, "body-fit reference", "σωματομετρική αναφορά")
    )
    st.info(
        translate(lang, "Monitor v2 uses actual viewing distance + vertical position rather than a universal 'eye level − 5 cm' formula.", "Στη v2 η οθόνη αξιολογείται με την πραγματική απόσταση θέασης και την κατακόρυφη θέση της και όχι με έναν καθολικό τύπο «ύψος ματιών − 5 cm».")
    )

    with st.expander(translate(lang, "DSE environment", "Περιβάλλον εργασίας με οθόνη"), expanded=False):
        e1, e2 = st.columns(2)
        lighting_ok = yes_no_unknown(translate(lang, "Lighting is adequate", "Ο φωτισμός είναι επαρκής"), "lighting_ok")
        noise_ok = yes_no_unknown(translate(lang, "Noise is acceptable for the task", "Ο θόρυβος είναι αποδεκτός για τη συγκεκριμένη εργασία"), "noise_ok")
        thermal_ok = yes_no_unknown(translate(lang, "Thermal comfort is acceptable", "Η θερμική άνεση είναι αποδεκτή"), "thermal_ok")
        software_ok = yes_no_unknown(translate(lang, "Software/interface supports the task without avoidable strain", "Το λογισμικό/η διεπαφή υποστηρίζει την εργασία χωρίς περιττή επιβάρυνση"), "software_ok")
        st.caption(
            translate(lang, "These fields support a broader EU display-screen assessment and are kept separate from musculoskeletal disease scoring.", "Τα πεδία αυτά υποστηρίζουν μια πληρέστερη αξιολόγηση εργασίας με οθόνη σύμφωνα με την ευρωπαϊκή προσέγγιση και παραμένουν ξεχωριστά από οποιαδήποτε βαθμολόγηση μυοσκελετικής νόσου.")
        )

# ---------------------------------------------------------------------
# 4. Chair fit / adjustability
# ---------------------------------------------------------------------
with tabs[3]:
    st.subheader(t["chair_title"])
    st.info(t["chair_screen_note"])
    st.caption(
        translate(lang, "Reference: EN 1335 / ISO 9241-5 design principles. Full conformity requires the official standard and its complete test method.", "Αναφορά: αρχές σχεδιασμού EN 1335 / ISO 9241-5. Η πλήρης συμμόρφωση απαιτεί το επίσημο πρότυπο και την ολοκληρωμένη μέθοδο δοκιμής του.")
    )
    chair_completed = st.toggle(translate(lang, "Assessment completed", "Ο έλεγχος καρέκλας ολοκληρώθηκε"), value=False, key="chair_completed")
    chair_results: dict[str, bool] = {}
    if chair_completed:
        ca, cb = st.columns(2)
        for idx, (key, label) in enumerate(CHAIR_FIT_ITEMS):
            with (ca if idx < (len(CHAIR_FIT_ITEMS)+1)//2 else cb):
                display_label = (
                    CHAIR_FIT_LABELS_EL.get(key, label) if lang == "el"
                    else CHAIR_FIT_LABELS_SL.get(key, label) if lang == "sl"
                    else label
                )
                chair_results[key] = st.checkbox(display_label, value=False, key=f"chair_{key}")
        chair_failed = [key for key, ok in chair_results.items() if not ok]
        st.metric(translate(lang, "Items confirmed", "Κριτήρια που πληρούνται"), f"{len(CHAIR_FIT_ITEMS)-len(chair_failed)} / {len(CHAIR_FIT_ITEMS)}")
        st.caption(
            translate(lang, "No compliance percentage or clinical risk band is generated.", "Δεν παράγεται ποσοστό συμμόρφωσης ή κλινική κατηγορία κινδύνου.")
        )
    else:
        chair_failed = []
        st.caption(
            translate(lang, "Mark the section as completed before chair findings are included in the report.", "Σημείωσε ότι ο έλεγχος ολοκληρώθηκε ώστε τα ευρήματα της καρέκλας να συμπεριληφθούν στην αναφορά.")
        )

    with st.expander(
        translate(lang, "EN 1335 Type A reference dimensions — audit note", "Διαστάσεις αναφοράς EN 1335 Type A — σημείωση ελέγχου"),
        expanded=False,
    ):
        for k, v in EN1335_TYPE_A_REFERENCE.items():
            label = (
                EN1335_LABELS_EL.get(k, k) if lang == "el"
                else EN1335_LABELS_SL.get(k, k) if lang == "sl"
                else k.replace("_", " ")
            )
            st.write(f"- **{label}:** {v}")
        st.caption(
            translate(lang, "Displayed for reference only; the screen above is not a product-certification procedure.", "Οι τιμές εμφανίζονται μόνο ως αναφορά. Η παραπάνω ενότητα δεν αποτελεί διαδικασία πιστοποίησης προϊόντος.")
        )

# ---------------------------------------------------------------------
# 5. Posture & movement
# ---------------------------------------------------------------------
with tabs[4]:
    st.subheader(t["posture_title"])
    st.info(t["posture_note"])
    st.caption(
        translate(lang, "Greek version: terminology and criteria follow ELINYAE office/DSE guidance. English version follows OSHA Computer Workstations guidance.", "Η αξιολόγηση βασίζεται στις οδηγίες του ΕΛΙΝΥΑΕ για εργασία με οθόνες και εργονομικό σχεδιασμό. Δεν χρησιμοποιείται ένα μοναδικό «ιδανικό» σύνολο γωνιών για όλους.")
    )

    posture_completed = st.toggle(
        translate(lang, "Assessment completed", "Η παρατήρηση στάσης ολοκληρώθηκε"),
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
            display_posture_label = translate(lang, label_en, label_el)
            result = yes_no_unknown(display_posture_label, f"posture_{key}")
            posture_results[key] = result
            if result is False:
                posture_out.append({
                    "key": key,
                    "label": display_posture_label,
                    "value": "needs_review",
                    "reference": "ELINYAE" if lang == "el" else ("EU/EN-ISO" if lang == "sl" else "OSHA"),
                })

        dynamic = posture_results.get("dynamic_posture")
        movement_variability = "good" if dynamic is True else ("limited" if dynamic is False else "not_assessed")

        if movement_variability == "limited":
            st.warning(
                translate(lang, "Prolonged static posture was flagged. Postural variation should be increased.", "Εντοπίστηκε παρατεταμένη στατική στάση. Χρειάζεται μεγαλύτερη εναλλαγή θέσεων και κίνηση κατά τη διάρκεια της εργασίας.")
            )

        with st.expander(
            translate(lang, "Optional angle recording", "Προαιρετική καταγραφή γωνίας αγκώνα"),
            expanded=False,
        ):
            elbow_angle_observed = st.number_input(
                translate(lang, "Observed elbow angle (°)", "Μετρημένη γωνία αγκώνα (°)"),
                min_value=0,
                max_value=180,
                value=0,
                step=5,
                help=(
                    translate(lang, "0 = not measured. OSHA uses 90–120° as a neutral reference.", "0 = δεν μετρήθηκε. Το ΕΛΙΝΥΑΕ αναφέρει περίπου 90° ή ελαφρά μεγαλύτερη γωνία κατά τη χρήση πληκτρολογίου.")
                ),
            )
            if elbow_angle_observed > 0:
                st.caption(
                    f"Zabeleženo: {elbow_angle_observed}°. Vrednost je dokumentirana in se ne pretvarja v oceno tveganja bolezni."
                    if lang == "sl"
                    else f"Recorded: {elbow_angle_observed}°. This value is documented, not converted into a disease-risk score."
                    if lang == "en"
                    else f"Καταγράφηκαν {elbow_angle_observed}°. Η μέτρηση τεκμηριώνεται αλλά δεν μετατρέπεται σε βαθμολογία κινδύνου νόσου."
                )
    else:
        movement_variability = "not_assessed"
        st.caption(
            translate(lang, "Mark the section as completed before posture findings are included in the report.", "Σημείωσε ότι η παρατήρηση στάσης ολοκληρώθηκε ώστε τα σχετικά ευρήματα να συμπεριληφθούν στην αναφορά.")
        )

# ---------------------------------------------------------------------
# 6. ROSA
# ---------------------------------------------------------------------
with tabs[5]:
    st.subheader(t["rosa_title"])
    st.info(t["rosa_note"])
    st.caption(
        "Scoring follows the ROSA worksheet structure developed by Sonne, Villalta & Andrews. "
        translate(lang, "The visual worksheet shown below is the TuMeke rendition based on ROSA.", "Η βαθμολόγηση ακολουθεί τη δομή του ROSA των Sonne, Villalta & Andrews. ")
        "Ο οπτικός οδηγός που εμφανίζεται παρακάτω είναι η έκδοση worksheet της TuMeke που βασίζεται στο ROSA."
    )

    ROSA_BANNER_PATH = ASSETS / "rosa_banner.jpg"
    ROSA_PDF_PATH = ASSETS / "ROSA.pdf"

    with st.expander(
        translate(lang, "Visual ROSA worksheet & icons", "Οπτικός οδηγός ROSA με τα εικονίδια"),
        expanded=True,
    ):
        # Keep ROSA media fully local to the deployed app. This avoids broken
        # external URLs and avoids PIL decoding inside st.image.
        if ROSA_BANNER_PATH.exists() and ROSA_PDF_PATH.exists():
            try:
                banner_b64 = base64.b64encode(ROSA_BANNER_PATH.read_bytes()).decode("ascii")
                pdf_bytes = ROSA_PDF_PATH.read_bytes()
                pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")

                st.markdown(
                    f"""
                    <a href="data:application/pdf;base64,{pdf_b64}" target="_blank"
                       style="display:block;text-decoration:none;">
                      <img
                        src="data:image/jpeg;base64,{banner_b64}"
                        alt="ErgoFit ROSA checklist"
                        style="width:100%;height:auto;display:block;border-radius:12px;border:1px solid #d9dde6;"
                      />
                    </a>
                    """,
                    unsafe_allow_html=True,
                )

                st.download_button(
                    translate(lang, "Download ROSA worksheet PDF", "Λήψη του ROSA worksheet σε PDF"),
                    data=pdf_bytes,
                    file_name="ROSA.pdf",
                    mime="application/pdf",
                    key="download_rosa_pdf",
                )
            except Exception:
                st.warning(
                    translate(lang, "The ROSA visual guide could not be loaded. The assessment below remains available.", "Ο οπτικός οδηγός ROSA δεν μπόρεσε να φορτωθεί. Η αξιολόγηση από κάτω παραμένει διαθέσιμη.")
                )
        else:
            st.warning(
                translate(lang, "ROSA media files are unavailable.", "Τα αρχεία του οπτικού οδηγού ROSA δεν είναι διαθέσιμα.")
            )

        st.caption(
            translate(lang, "Click the banner to open the worksheet, or use the PDF download button. The controls below follow the same scoring structure.", "Πάτησε πάνω στην εικόνα για να ανοίξεις το worksheet ή χρησιμοποίησε το κουμπί λήψης PDF. Τα πεδία από κάτω ακολουθούν την ίδια δομή βαθμολόγησης.")
        )

    rosa_completed = st.toggle(
        translate(lang, "Assessment completed", "Η αξιολόγηση ROSA ολοκληρώθηκε"),
        value=False,
        key="rosa_completed",
    )

    if rosa_completed:
        # -----------------------------
        # Section A — Chair
        # -----------------------------
        st.markdown(translate(lang, "### A · Chair", "### A · Καρέκλα"))

        st.markdown(translate(lang, "#### A.1 · Chair height", "#### A.1 · Ύψος καρέκλας"))
        a1_choice = st.radio(
            translate(lang, "Select the picture/condition that best matches the worker", "Επίλεξε την εικόνα/κατάσταση που ταιριάζει περισσότερο στον εργαζόμενο"),
            ["neutral", "too_low", "too_high", "no_foot_contact"],
            format_func=lambda v: {
                "neutral": translate(lang, "Knees at about 90° (+1)", "Γόνατα περίπου στις 90° (+1)"),
                "too_low": translate(lang, "Chair too low: knee angle <90° (+2)", "Η καρέκλα είναι πολύ χαμηλά: γωνία γόνατος <90° (+2)"),
                "too_high": translate(lang, "Chair too high: knee angle >90° (+2)", "Η καρέκλα είναι πολύ ψηλά: γωνία γόνατος >90° (+2)"),
                "no_foot_contact": translate(lang, "No foot contact with the floor (+3)", "Τα πέλματα δεν ακουμπούν στο δάπεδο (+3)"),
            }[v],
            key="rosa_a1_primary",
        )
        a1_primary = {"neutral": 1, "too_low": 2, "too_high": 2, "no_foot_contact": 3}[a1_choice]
        a1_extra = 0
        if st.checkbox(
            translate(lang, "Insufficient space under the desk / cannot comfortably move the legs (+1)", "Ανεπαρκής χώρος κάτω από το γραφείο / δεν υπάρχει επαρκής χώρος κίνησης των ποδιών (+1)"),
            key="rosa_a1_cramp",
        ):
            a1_extra += 1
        if st.checkbox(
            translate(lang, "Chair height is non-adjustable (+1)", "Το ύψος της καρέκλας δεν ρυθμίζεται (+1)"),
            key="rosa_a1_nonadj",
        ):
            a1_extra += 1
        a1 = a1_primary + a1_extra

        st.markdown(translate(lang, "#### A.2 · Seat pan depth", "#### A.2 · Βάθος έδρας"))
        a2_primary = st.radio(
            translate(lang, "Select seat-depth condition", "Επίλεξε την κατάσταση που περιγράφει το βάθος της έδρας"),
            [1, 2, 3],
            format_func=lambda v: {
                1: translate(lang, "About 3 in / 7–8 cm between the back of the knee and seat edge (+1)", "Περίπου 7–8 cm κενό μεταξύ του πίσω μέρους του γόνατος και της άκρης της έδρας (+1)"),
                2: translate(lang, "Too long: less than ~7–8 cm of space (+2)", "Πολύ βαθιά έδρα: κενό μικρότερο από περίπου 7–8 cm (+2)"),
                3: translate(lang, "Too short: more than ~7–8 cm of space (+2)", "Πολύ ρηχή έδρα: κενό μεγαλύτερο από περίπου 7–8 cm (+2)"),
            }[v],
            key="rosa_a2_primary",
        )
        # ROSA gives both too-long and too-short conditions a score of 2.
        a2 = 1 if a2_primary == 1 else 2
        if st.checkbox(
            translate(lang, "Seat depth is non-adjustable (+1)", "Το βάθος της έδρας δεν ρυθμίζεται (+1)"),
            key="rosa_a2_nonadj",
        ):
            a2 += 1

        st.markdown(translate(lang, "#### A.3 · Armrests", "#### A.3 · Μπράτσα καρέκλας"))
        a3_primary = st.radio(
            translate(lang, "Select armrest condition", "Επίλεξε την κατάσταση που περιγράφει τα μπράτσα"),
            [1, 2],
            format_func=lambda v: {
                1: translate(lang, "Elbows supported in line with the shoulders; shoulders relaxed (+1)", "Οι αγκώνες στηρίζονται κοντά στο σώμα και οι ώμοι είναι χαλαροί (+1)"),
                2: translate(lang, "Armrests too high or too low; shoulders shrugged or arms unsupported (+2)", "Τα μπράτσα είναι πολύ ψηλά ή πολύ χαμηλά: οι ώμοι ανυψώνονται ή τα χέρια δεν στηρίζονται (+2)"),
            }[v],
            key="rosa_a3_primary",
        )
        a3 = a3_primary
        if st.checkbox(
            translate(lang, "Armrest surface is hard/damaged (+1)", "Η επιφάνεια των μπράτσων είναι σκληρή ή φθαρμένη (+1)"),
            key="rosa_a3_hard",
        ):
            a3 += 1
        if st.checkbox(
            translate(lang, "Armrests are too far apart (+1)", "Τα μπράτσα απέχουν υπερβολικά μεταξύ τους (+1)"),
            key="rosa_a3_wide",
        ):
            a3 += 1
        if st.checkbox(
            translate(lang, "Armrests are non-adjustable (+1)", "Τα μπράτσα δεν ρυθμίζονται (+1)"),
            key="rosa_a3_nonadj",
        ):
            a3 += 1

        st.markdown(translate(lang, "#### A.4 · Back support", "#### A.4 · Στήριξη πλάτης"))
        a4_choice = st.radio(
            translate(lang, "Select back-support condition", "Επίλεξε την κατάσταση που περιγράφει τη στήριξη της πλάτης"),
            ["adequate", "no_lumbar", "bad_angle", "no_back_support"],
            format_func=lambda v: {
                "adequate": translate(lang, "Adequate lumbar support; backrest about 95–110° (+1)", "Επαρκής οσφυϊκή στήριξη και κλίση πλάτης περίπου 95–110° (+1)"),
                "no_lumbar": translate(lang, "No lumbar support OR lumbar support not positioned in the small of the back (+2)", "Δεν υπάρχει οσφυϊκή στήριξη ή δεν είναι σωστά τοποθετημένη στην οσφυϊκή περιοχή (+2)"),
                "bad_angle": translate(lang, "Backrest angled too far back (>110°) or too far forward (<95°) (+2)", "Η πλάτη είναι υπερβολικά πίσω (>110°) ή υπερβολικά μπροστά (<95°) (+2)"),
                "no_back_support": translate(lang, "No back support / stool / worker leaning forward without support (+3)", "Χωρίς στήριξη πλάτης, π.χ. σκαμπό ή εργασία με τον κορμό μπροστά χωρίς στήριξη (+3)"),
            }[v],
            key="rosa_a4_primary",
        )
        a4 = {"adequate": 1, "no_lumbar": 2, "bad_angle": 2, "no_back_support": 3}[a4_choice]
        if st.checkbox(
            translate(lang, "Work surface too high; shoulders shrugged (+1)", "Η επιφάνεια εργασίας είναι πολύ ψηλά και προκαλεί ανύψωση των ώμων (+1)"),
            key="rosa_a4_highdesk",
        ):
            a4 += 1
        if st.checkbox(
            translate(lang, "Backrest is non-adjustable (+1)", "Η πλάτη της καρέκλας δεν ρυθμίζεται (+1)"),
            key="rosa_a4_nonadj",
        ):
            a4 += 1

        dur_chair = duration_selector("dur_chair")

        a_cols = st.columns(5)
        a_cols[0].metric("A.1", a1)
        a_cols[1].metric("A.2", a2)
        a_cols[2].metric("A.3", a3)
        a_cols[3].metric("A.4", a4)
        a_cols[4].metric(translate(lang, "Duration", "Διάρκεια"), f"{dur_chair:+d}")

        st.divider()

        # -----------------------------
        # Section B — Monitor & Phone
        # -----------------------------
        st.markdown(translate(lang, "### B · Monitor & phone", "### B · Οθόνη & τηλέφωνο"))

        st.markdown(translate(lang, "#### B.1 · Monitor", "#### B.1 · Οθόνη"))
        b1_primary = st.radio(
            translate(lang, "Select monitor-height condition", "Επίλεξε την κατάσταση που περιγράφει καλύτερα το ύψος της οθόνης"),
            [1, 2, 3],
            format_func=lambda v: {
                1: translate(lang, "Arm's-length distance (about 40–75 cm) and screen at eye level (+1)", "Απόσταση περίπου όσο το μήκος του χεριού (40–75 cm) και οθόνη στο ύψος των ματιών (+1)"),
                2: translate(lang, "Monitor too low (below ~30° viewing angle) (+2)", "Η οθόνη είναι πολύ χαμηλά (κάτω από περίπου 30°) (+2)"),
                3: translate(lang, "Monitor too high, producing neck extension (+3)", "Η οθόνη είναι πολύ ψηλά και προκαλεί έκταση του αυχένα (+3)"),
            }[v],
            key="rosa_b1_primary",
        )
        b1 = b1_primary
        if st.checkbox(translate(lang, "Monitor too far away (+1)", "Η οθόνη βρίσκεται πολύ μακριά (+1)"), key="rosa_b1_far"):
            b1 += 1
        if st.checkbox(translate(lang, "Neck rotation >30° (+1)", "Στροφή αυχένα >30° (+1)"), key="rosa_b1_twist"):
            b1 += 1
        if st.checkbox(translate(lang, "Glare on screen (+1)", "Θάμβωση / αντανακλάσεις στην οθόνη (+1)"), key="rosa_b1_glare"):
            b1 += 1
        if st.checkbox(translate(lang, "Documents used without a document holder (+1)", "Χρήση εγγράφων χωρίς βάση στήριξης εγγράφων (+1)"), key="rosa_b1_docs"):
            b1 += 1
        dur_monitor = duration_selector("dur_monitor")

        st.markdown(translate(lang, "#### B.2 · Phone", "#### B.2 · Τηλέφωνο"))
        b2 = 1
        st.caption(
            translate(lang, "Baseline: headset or one-hand phone use with a neutral neck posture (+1). Add any conditions that apply.", "Βασική συνθήκη: headset ή χρήση τηλεφώνου με το ένα χέρι και ουδέτερη θέση αυχένα (+1). Πρόσθεσε όσα από τα παρακάτω ισχύουν.")
        )
        if st.checkbox(translate(lang, "Phone is too far to reach (>30 cm) (+2)", "Το τηλέφωνο βρίσκεται πολύ μακριά (>30 cm) (+2)"), key="rosa_b2_far"):
            b2 += 2
        if st.checkbox(translate(lang, "Phone held between neck and shoulder (+2)", "Το τηλέφωνο συγκρατείται μεταξύ αυχένα και ώμου (+2)"), key="rosa_b2_hold"):
            b2 += 2
        if st.checkbox(translate(lang, "No hands-free option available (+1)", "Δεν υπάρχει δυνατότητα hands-free / ακουστικών (+1)"), key="rosa_b2_hands"):
            b2 += 1
        dur_phone = duration_selector("dur_phone")

        st.divider()

        # -----------------------------
        # Section C — Mouse & Keyboard
        # -----------------------------
        st.markdown(translate(lang, "### C · Mouse & keyboard", "### C · Ποντίκι & πληκτρολόγιο"))

        st.markdown(translate(lang, "#### C.1 · Mouse", "#### C.1 · Ποντίκι"))
        c1r = 1
        st.caption(
            translate(lang, "Baseline: mouse in line with the shoulder (+1). Add any conditions that apply.", "Βασική συνθήκη: το ποντίκι βρίσκεται στην ίδια γραμμή με τον ώμο (+1). Πρόσθεσε όσα από τα παρακάτω ισχύουν.")
        )
        if st.checkbox(translate(lang, "Reaching to use the mouse (+2)", "Χρειάζεται τέντωμα του χεριού για χρήση του ποντικιού (+2)"), key="rosa_c1_reach"):
            c1r += 2
        if st.checkbox(translate(lang, "Mouse and keyboard are on different surfaces/heights (+2)", "Ποντίκι και πληκτρολόγιο βρίσκονται σε διαφορετικές επιφάνειες/ύψη (+2)"), key="rosa_c1_diff"):
            c1r += 2
        if st.checkbox(translate(lang, "Pinch grip on mouse (+1)", "Το ποντίκι χρησιμοποιείται με λαβή τύπου pinch grip (+1)"), key="rosa_c1_pinch"):
            c1r += 1
        if st.checkbox(translate(lang, "Palmrest in front of the mouse (+1)", "Υπάρχει στήριγμα παλάμης μπροστά από το ποντίκι (+1)"), key="rosa_c1_palm"):
            c1r += 1
        dur_mouse = duration_selector("dur_mouse")

        st.markdown(translate(lang, "#### C.2 · Keyboard", "#### C.2 · Πληκτρολόγιο"))
        c2r = 1
        st.caption(
            translate(lang, "Baseline: wrists straight and shoulders relaxed (+1). Add any conditions that apply.", "Βασική συνθήκη: οι καρποί είναι ευθείς/ουδέτεροι και οι ώμοι χαλαροί (+1). Πρόσθεσε όσα από τα παρακάτω ισχύουν.")
        )
        if st.checkbox(
            translate(lang, "Wrist extension / positive keyboard angle (>15° wrist extension) (+2)", "Έκταση καρπού / θετική κλίση πληκτρολογίου (>15° έκταση καρπού) (+2)"),
            key="rosa_c2_ext",
        ):
            c2r += 2
        if st.checkbox(translate(lang, "Wrist deviation while typing (+1)", "Απόκλιση καρπού κατά την πληκτρολόγηση (+1)"), key="rosa_c2_dev"):
            c2r += 1
        if st.checkbox(translate(lang, "Keyboard too high; shoulders shrugged (+1)", "Το πληκτρολόγιο είναι πολύ ψηλά και οι ώμοι ανυψώνονται (+1)"), key="rosa_c2_high"):
            c2r += 1
        if st.checkbox(translate(lang, "Reaching to overhead items (+1)", "Χρειάζεται προσέγγιση αντικειμένων πάνω από το ύψος των ώμων (+1)"), key="rosa_c2_over"):
            c2r += 1
        if st.checkbox(translate(lang, "Keyboard platform is non-adjustable (+1)", "Η βάση/επιφάνεια του πληκτρολογίου δεν ρυθμίζεται (+1)"), key="rosa_c2_nonadj"):
            c2r += 1
        dur_keyboard = duration_selector("dur_keyboard")

        rosa = compute_rosa(
            a1, a2, a3, a4, dur_chair,
            b1, b2, dur_monitor, dur_phone,
            c1r, c2r, dur_mouse, dur_keyboard,
        )

        st.divider()
        st.markdown("### " + (translate(lang, "ROSA results", "Αποτελέσματα ROSA")))
        r1, r2, r3 = st.columns(3)
        r1.metric(translate(lang, "Chair ROSA", "ROSA καρέκλας"), f"{rosa['chair']} / 10")
        r2.metric(translate(lang, "Monitor & peripherals", "Οθόνη & περιφερειακά"), f"{rosa['monitor_peripherals']} / 10")
        r3.metric(translate(lang, "ROSA final", "Τελικό ROSA"), f"{rosa['final']} / 10")

        st.caption(
            f"Razdelek B: {rosa['section_b']} · Razdelek C: {rosa['section_c']}"
            if lang == "sl"
            else f"Section B: {rosa['section_b']} · Section C: {rosa['section_c']}"
            if lang == "en"
            else f"Ενότητα B: {rosa['section_b']} · Ενότητα C: {rosa['section_c']}"
        )

        if rosa["final"] >= 5:
            st.error(
                translate(lang, "ROSA action level reached (≥5): further ergonomic investigation/intervention indicated.", "Επιτεύχθηκε το επίπεδο δράσης ROSA (≥5): ενδείκνυται περαιτέρω εργονομική διερεύνηση και παρέμβαση.")
            )
        else:
            st.success(
                translate(lang, "ROSA below the validated action level of 5. This is not a clinical 'low disease risk' category.", "Το ROSA βρίσκεται κάτω από το τεκμηριωμένο επίπεδο δράσης 5. Αυτό δεν σημαίνει κλινικά «χαμηλό κίνδυνο νόσου».")
            )
    else:
        rosa = {
            "chair": 0, "section_b": 0, "section_c": 0,
            "monitor_peripherals": 0, "final": 0, "action": "not_assessed"
        }
        st.caption(
            translate(lang, "Mark ROSA as completed before a score is included in the report.", "Σημείωσε ότι η αξιολόγηση ROSA ολοκληρώθηκε ώστε η βαθμολογία να συμπεριληφθεί στην αναφορά.")
        )

# ---------------------------------------------------------------------
# Build context, findings and recommendations before evidence/summary tabs.
# ---------------------------------------------------------------------
ctx = {
    "subject_id": subject_id,
    "company": company,
    "department": department,
    "job_title": job_title,
    "client_name_or_code": subject_id,
    "assessment_stage": assessment_stage,
    "parent_assessment_id": parent_assessment_id,
    "interventions_notes": interventions_notes,
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

    with st.expander(
        translate(lang, "Findings from this assessment", "Ευρήματα αυτής της αξιολόγησης"),
        expanded=False,
    ):
        if findings:
            for f in findings:
                finding_card(f, lang)
                st.write("")
        else:
            st.success(
                translate(lang, "No priority exposure finding was generated from the entered data.", "Δεν προέκυψε εύρημα έκθεσης υψηλής προτεραιότητας από τα δεδομένα που καταχωρίστηκαν.")
            )

    st.markdown(
        "### " + (
            translate(lang, "Research evidence by body region", "Επιστημονικά ευρήματα ανά περιοχή σώματος")
        )
    )
    st.caption(
        translate(lang, "Each section keeps evidence for the same body region together. Every study starts with a plain-language explanation; statistical details are optional.", "Οι έρευνες για την ίδια περιοχή σώματος εμφανίζονται μαζί. Κάθε μελέτη ξεκινά με απλή εξήγηση και οι στατιστικές λεπτομέρειες ανοίγουν μόνο αν τις χρειάζεσαι.")
    )

    if relevant_evidence:
        for region_label, region_items in group_evidence_by_region(relevant_evidence, lang):
            st.markdown(f"## {region_label}")
            for e in region_items:
                evidence_card(e, lang)
                st.write("")
    else:
        st.caption(
            translate(lang, "No evidence cards are triggered until relevant exposure/symptom information is entered.", "Δεν εμφανίζονται σχετικές μελέτες μέχρι να καταχωριστούν στοιχεία έκθεσης ή συμπτωμάτων.")
        )

    with st.expander(
        translate(lang, "Full v2 evidence library", "Πλήρης βιβλιοθήκη επιστημονικής τεκμηρίωσης v2"),
        expanded=False,
    ):
        st.caption(
            translate(lang, "The full library is also organised by body region. Research estimates are not combined into a single disease-risk score.", "Η πλήρης βιβλιοθήκη είναι επίσης οργανωμένη ανά περιοχή σώματος. Τα αποτελέσματα των μελετών δεν συνδυάζονται σε μία ενιαία βαθμολογία κινδύνου νόσου.")
        )
        for region_label, region_items in group_evidence_by_region(list(EVIDENCE.values()), lang):
            st.markdown(f"### {region_label}")
            for e in region_items:
                evidence_card(e, lang)
                st.write("")

# ---------------------------------------------------------------------
# 8. Summary & Results
# ---------------------------------------------------------------------
with tabs[7]:
    st.subheader(t["summary_title"])

    subject_display = subject_id.strip() or (translate(lang, "Unidentified worker", "Χωρίς αναγνωριστικό"))
    stage_label = (
        translate(lang, "1st Assessment", "1η Αξιολόγηση")
        if assessment_stage == "baseline"
        else translate(lang, "2nd Assessment / Reassessment", "2η Αξιολόγηση / Επαναξιολόγηση")
    )

    st.markdown(
        f"""<div class="ef-summary">
        <div class="ef-kicker">{translate(lang, "ASSESSMENT SUMMARY", "ΣΥΝΟΨΗ ΑΞΙΟΛΟΓΗΣΗΣ")}</div>
        <h3 style="margin:.25rem 0!important">{subject_display}</h3>
        <div><b>{translate(lang, "Stage", "Στάδιο")}:</b> {stage_label} &nbsp;·&nbsp; <b>{translate(lang, "Date", "Ημερομηνία")}:</b> {assessment_date}</div>
        <div style="margin-top:8px;color:#5b6475">
        {translate(lang, "This report summarises identified ergonomic exposures, reported symptoms, ROSA results and preventive actions. It does not calculate an individual probability of disease.", "Η αναφορά συνοψίζει τους εργονομικούς παράγοντες έκθεσης, τα αναφερόμενα συμπτώματα, το ROSA και τα προτεινόμενα μέτρα πρόληψης/βελτίωσης. Δεν υπολογίζει προσωπική πιθανότητα εμφάνισης πάθησης.")}
        </div></div>""",
        unsafe_allow_html=True,
    )

    priority_count = sum(f.status == "priority" for f in findings)
    attention_count = sum(f.status == "attention" for f in findings)
    symptom_count = sum(int(item.get("severity", 0) or 0) > 0 for item in symptom_details.values())

    st.markdown("### " + (translate(lang, "Overall picture", "Συνολική εικόνα")))
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("ROSA", f"{rosa['final']} / 10" if rosa["final"] > 0 else (translate(lang, "Not assessed", "Δεν αξιολογήθηκε")))
    m2.metric(
        translate(lang, "High-priority issues", "Θέματα άμεσης προτεραιότητας"),
        priority_count,
    )
    m3.metric(
        translate(lang, "Issues needing attention", "Θέματα που χρειάζονται προσοχή"),
        attention_count,
    )
    m4.metric(
        translate(lang, "Symptomatic regions", "Περιοχές με συμπτώματα"),
        symptom_count,
    )

    if rosa["final"] >= 5:
        st.warning(
            translate(lang, "ROSA reached the validated action level (≥5), so further ergonomic investigation and intervention are indicated.", "Το ROSA έφτασε το τεκμηριωμένο επίπεδο δράσης (≥5), επομένως ενδείκνυται περαιτέρω εργονομική διερεύνηση και παρέμβαση.")
        )
    elif rosa["final"] > 0:
        st.info(
            translate(lang, "ROSA is below the action level of 5. This does not mean that all ergonomic issues or symptoms are absent.", "Το ROSA βρίσκεται κάτω από το επίπεδο δράσης 5. Αυτό δεν σημαίνει ότι απουσιάζουν όλα τα εργονομικά ζητήματα ή τα συμπτώματα.")
        )

    st.markdown("### " + (translate(lang, "Musculoskeletal profile & proposed action", "Μυοσκελετικό προφίλ & προτεινόμενη ενέργεια")))
    st.caption(
        translate(lang, "The proposed action combines reported symptoms, functional/work impact and relevant ergonomic findings. It is a workflow recommendation, not a diagnosis or individual prognosis.", "Η προτεινόμενη ενέργεια συνδυάζει τα αναφερόμενα συμπτώματα, τη λειτουργική/εργασιακή επίδραση και τα σχετικά εργονομικά ευρήματα. Αποτελεί πρόταση διαχείρισης και όχι διάγνωση ή ατομική πρόγνωση.")
    )
    if symptom_details:
        profile_rows = []
        for region, item in symptom_details.items():
            label = item.get("label", region)
            severity = int(item.get("severity", 0) or 0)
            duration = symptom_duration_label(item.get("duration", "not_recorded"))
            frequency = symptom_frequency_label(item.get("frequency", "not_recorded"))
            interference = item.get("interference")
            work_modification = item.get("work_modification")
            absence_days = int(item.get("absence_days_4w", 0) or 0)

            work_bits = []
            if interference is True:
                work_bits.append(translate(lang, "affects work", "επηρεάζει την εργασία"))
            elif interference is False:
                work_bits.append(translate(lang, "no reported interference", "δεν αναφέρθηκε επίδραση"))
            if work_modification is True:
                work_bits.append(translate(lang, "task/pace modified", "αλλαγή ρυθμού/εργασίας"))
            if absence_days > 0:
                work_bits.append(
                    f"{absence_days} dni odsotnosti/4 tedne"
                    if lang == "sl"
                    else f"{absence_days} absence day(s)/4 weeks"
                    if lang == "en"
                    else f"{absence_days} ημέρες απουσίας/4 εβδομάδες"
                )

            symptom_text = f"{severity}/10"
            if duration != "—":
                symptom_text += f" · {duration}"
            if frequency != "—":
                symptom_text += f" · {frequency}"

            profile_rows.append({
                (translate(lang, "Region", "Περιοχή")): label,
                (translate(lang, "Symptoms", "Συμπτώματα")): symptom_text,
                (translate(lang, "Work impact", "Επίδραση στην εργασία")): " · ".join(work_bits) if work_bits else "—",
                (translate(lang, "Ergonomic exposure/findings", "Εργονομική έκθεση / ευρήματα")): region_exposure_text(region, ctx),
                (translate(lang, "Proposed action", "Προτεινόμενη ενέργεια")): region_action_text(region, item, ctx),
            })
        st.dataframe(profile_rows, use_container_width=True, hide_index=True)
        st.caption(
            translate(lang, "*The ≥6 h/day sitting flag is an operational screening flag, not a validated causal threshold.", "*Η ένδειξη ≥6 ώρες/ημέρα καθιστικής εργασίας είναι λειτουργική ένδειξη screening και όχι επικυρωμένο αιτιώδες όριο.")
        )
    else:
        st.caption(translate(lang, "No musculoskeletal symptoms were reported.", "Δεν αναφέρθηκαν μυοσκελετικά συμπτώματα."))

    if digital_eye_strain:
        st.markdown(
            translate(lang, "- **Digital eye strain / visual fatigue reported**", "- **Αναφέρθηκε κόπωση ματιών από τη χρήση της οθόνης**")
        )

    st.markdown("### " + (translate(lang, "Identified ergonomic factors", "Εντοπισμένοι εργονομικοί παράγοντες")))
    if findings:
        priority_findings = [f for f in findings if f.status == "priority"]
        attention_findings = [f for f in findings if f.status == "attention"]
        information_findings = [f for f in findings if f.status == "information"]

        if priority_findings:
            st.markdown("#### " + (translate(lang, "Immediate priority", "Άμεση προτεραιότητα")))
            for f in priority_findings:
                finding_card(f, lang)
                st.write("")
        if attention_findings:
            st.markdown("#### " + (translate(lang, "Needs attention", "Χρειάζεται προσοχή")))
            for f in attention_findings:
                finding_card(f, lang)
                st.write("")
        if information_findings:
            with st.expander(translate(lang, "Additional context", "Πρόσθετες πληροφορίες"), expanded=False):
                for f in information_findings:
                    finding_card(f, lang)
                    st.write("")
    else:
        st.success(
            translate(lang, "No priority ergonomic exposure was identified from the entered information.", "Δεν εντοπίστηκε εργονομικός παράγοντας υψηλής προτεραιότητας από τα στοιχεία που καταχωρίστηκαν.")
        )

    st.markdown("### " + (translate(lang, "Preventive and improvement measures", "Μέτρα πρόληψης και βελτίωσης")))
    now_recs = [r for r in recommendations if r.priority == "now"]
    soon_recs = [r for r in recommendations if r.priority == "soon"]
    maintain_recs = [r for r in recommendations if r.priority == "maintain"]

    if now_recs:
        st.markdown("#### " + (translate(lang, "Implement first", "Να εφαρμοστούν πρώτα")))
        for r in now_recs:
            recommendation_card(r, lang)
            st.write("")
    if soon_recs:
        st.markdown("#### " + (translate(lang, "Next actions", "Επόμενες ενέργειες")))
        for r in soon_recs:
            recommendation_card(r, lang)
            st.write("")
    if maintain_recs:
        with st.expander(translate(lang, "Good practices to maintain", "Καλές πρακτικές που πρέπει να διατηρηθούν"), expanded=False):
            for r in maintain_recs:
                recommendation_card(r, lang)
                st.write("")

    # -------------------------------------------------------------
    # Before / after comparison for follow-up assessments
    # -------------------------------------------------------------
    comparison_payload = None
    if assessment_stage == "followup":
        st.divider()
        st.markdown("### " + (translate(lang, "Before vs after interventions", "Σύγκριση πριν και μετά τις παρεμβάσεις")))

        if baseline_report is None:
            st.warning(
                translate(lang, "Upload the initial assessment JSON in the Worker tab to generate the before/after comparison.", "Ανέβασε το JSON της αρχικής αξιολόγησης στην καρτέλα «Εργαζόμενος» για να δημιουργηθεί η σύγκριση πριν/μετά.")
            )
        else:
            baseline_findings = baseline_report.get("findings", []) or []
            baseline_priority = sum(f.get("status") == "priority" for f in baseline_findings if isinstance(f, dict))
            baseline_attention = sum(f.get("status") == "attention" for f in baseline_findings if isinstance(f, dict))
            baseline_rosa_obj = baseline_assessment.get("rosa", {}) or {}
            baseline_rosa = int(baseline_rosa_obj.get("final", baseline_assessment.get("rosa_final", 0)) or 0)

            st.caption(
                translate(lang, "The comparison evaluates change in ergonomic exposure indicators, symptoms and ROSA. It does not estimate a change in personal disease probability.", "Η σύγκριση αξιολογεί τη μεταβολή σε εργονομικούς δείκτες έκθεσης, συμπτώματα και ROSA. Δεν εκτιμά μεταβολή στην προσωπική πιθανότητα εμφάνισης πάθησης.")
            )

            c1, c2, c3 = st.columns(3)
            c1.metric(
                translate(lang, "ROSA after", "ROSA μετά"),
                f"{rosa['final']} / 10",
                (f"{rosa['final'] - baseline_rosa:+d} vs before" if lang == "en" else f"{rosa['final'] - baseline_rosa:+d} glede na prej" if lang == "sl" else f"{rosa['final'] - baseline_rosa:+d} σε σχέση με πριν"),
                delta_color="inverse",
            )
            c2.metric(
                translate(lang, "High-priority issues after", "Θέματα άμεσης προτεραιότητας μετά"),
                priority_count,
                (f"{priority_count - baseline_priority:+d} vs before" if lang == "en" else f"{priority_count - baseline_priority:+d} glede na prej" if lang == "sl" else f"{priority_count - baseline_priority:+d} σε σχέση με πριν"),
                delta_color="inverse",
            )
            c3.metric(
                translate(lang, "Attention issues after", "Θέματα που χρειάζονται προσοχή μετά"),
                attention_count,
                (f"{attention_count - baseline_attention:+d} vs before" if lang == "en" else f"{attention_count - baseline_attention:+d} glede na prej" if lang == "sl" else f"{attention_count - baseline_attention:+d} σε σχέση με πριν"),
                delta_color="inverse",
            )

            if interventions_notes.strip():
                st.markdown("#### " + (translate(lang, "Interventions implemented", "Παρεμβάσεις που εφαρμόστηκαν")))
                st.write(interventions_notes.strip())

            baseline_symptoms = baseline_assessment.get("symptom_details", {}) or {}
            current_symptoms = symptom_details or {}
            all_regions = list(dict.fromkeys(list(baseline_symptoms.keys()) + list(current_symptoms.keys())))
            if all_regions:
                st.markdown("#### " + (translate(lang, "Change in symptoms", "Μεταβολή συμπτωμάτων")))
                for region in all_regions:
                    before = baseline_symptoms.get(region, {}) or {}
                    after = current_symptoms.get(region, {}) or {}
                    label = after.get("label") or before.get("label") or region
                    before_score = int(before.get("severity", 0) or 0)
                    after_score = int(after.get("severity", 0) or 0)
                    before_work = bool(before.get("interference", False))
                    after_work = bool(after.get("interference", False))
                    before_duration = symptom_duration_label(before.get("duration", "not_recorded"))
                    after_duration = symptom_duration_label(after.get("duration", "not_recorded"))
                    before_frequency = symptom_frequency_label(before.get("frequency", "not_recorded"))
                    after_frequency = symptom_frequency_label(after.get("frequency", "not_recorded"))
                    change = after_score - before_score

                    if change < 0:
                        change_text = (translate(lang, "improved", "βελτίωση"))
                    elif change > 0:
                        change_text = (translate(lang, "increased symptoms", "αύξηση συμπτωμάτων"))
                    else:
                        change_text = (translate(lang, "no change", "χωρίς μεταβολή"))

                    comparison_text = (
                        f"""**{label}**  
Prej: {before_score}/10 · Potem: {after_score}/10 · **{change_text}**  
Trajanje: {before_duration} → {after_duration} · Pogostost: {before_frequency} → {after_frequency}  
Vpliv na delo: {'Da' if before_work else 'Ne'} → {'Da' if after_work else 'Ne'}"""
                        if lang == "sl"
                        else
                        f"""**{label}**  
Before: {before_score}/10 · After: {after_score}/10 · **{change_text}**  
Duration: {before_duration} → {after_duration} · Frequency: {before_frequency} → {after_frequency}  
Work impact: {'Yes' if before_work else 'No'} → {'Yes' if after_work else 'No'}"""
                        if lang == "en"
                        else
                        f"""**{label}**  
Πριν: {before_score}/10 · Μετά: {after_score}/10 · **{change_text}**  
Διάρκεια: {before_duration} → {after_duration} · Συχνότητα: {before_frequency} → {after_frequency}  
Επίδραση στην εργασία: {'Ναι' if before_work else 'Όχι'} → {'Ναι' if after_work else 'Όχι'}"""
                    )
                    st.markdown(comparison_text)

            # Compare selected ergonomic indicators with a known direction of improvement.
            harmful_flags = [
                ("digital_eye_strain", translate(lang, "Digital eye strain", "Κόπωση ματιών από τη χρήση οθόνης")),
                ("high_repetition", translate(lang, "High hand/wrist repetition", "Υψηλή επανάληψη κινήσεων χεριού/καρπού")),
                ("hand_force", translate(lang, "Forceful hand/finger exertion", "Έντονη άσκηση δύναμης με χέρι/δάκτυλα")),
                ("forearm_rotation", translate(lang, "Forearm rotation exposure", "Παρατεταμένη/επαναλαμβανόμενη στροφή αντιβραχίου")),
                ("arm_elevation", translate(lang, "Sustained arm elevation", "Παρατεταμένη ανύψωση βραχίονα")),
                ("glare", translate(lang, "Glare/reflections", "Θάμβωση/αντανακλάσεις")),
            ]
            beneficial_flags = [
                ("active_breaks", translate(lang, "Active breaks / postural changes", "Ενεργά διαλείμματα / αλλαγές στάσης")),
                ("keyboard_close", translate(lang, "Keyboard/mouse close to the body", "Πληκτρολόγιο/ποντίκι κοντά στο σώμα")),
                ("forearm_support", translate(lang, "Forearm support", "Στήριξη αντιβραχίων")),
            ]

            improvements = []
            remaining = []
            new_issues = []

            for key, label in harmful_flags:
                before = bool(baseline_assessment.get(key, False))
                after = bool(ctx.get(key, False))
                if before and not after:
                    improvements.append(label)
                elif (not before) and after:
                    new_issues.append(label)
                elif before and after:
                    remaining.append(label)

            for key, label in beneficial_flags:
                before = bool(baseline_assessment.get(key, False))
                after = bool(ctx.get(key, False))
                if (not before) and after:
                    improvements.append(label)
                elif not after:
                    remaining.append(label)

            baseline_chair_issues = len(baseline_assessment.get("chair_failed", []) or [])
            current_chair_issues = len(chair_failed or [])
            if current_chair_issues < baseline_chair_issues:
                improvements.append(
                    f"Težave s prilagoditvijo/nastavljivostjo stola: {baseline_chair_issues} → {current_chair_issues}"
                    if lang == "sl"
                    else f"Chair fit/adjustability issues: {baseline_chair_issues} → {current_chair_issues}"
                    if lang == "en"
                    else f"Ζητήματα προσαρμογής/ρύθμισης καρέκλας: {baseline_chair_issues} → {current_chair_issues}"
                )
            elif current_chair_issues > 0:
                remaining.append(
                    f"{current_chair_issues} težav s prilagoditvijo/nastavljivostjo stola"
                    if lang == "sl"
                    else f"{current_chair_issues} chair fit/adjustability issue(s)"
                    if lang == "en"
                    else f"{current_chair_issues} ζητήματα προσαρμογής/ρύθμισης καρέκλας"
                )

            baseline_posture_issues = len(baseline_assessment.get("posture_out", []) or [])
            current_posture_issues = len(posture_out or [])
            if current_posture_issues < baseline_posture_issues:
                improvements.append(
                    f"Ugotovitve glede drže: {baseline_posture_issues} → {current_posture_issues}"
                    if lang == "sl"
                    else f"Posture findings: {baseline_posture_issues} → {current_posture_issues}"
                    if lang == "en"
                    else f"Ευρήματα στάσης: {baseline_posture_issues} → {current_posture_issues}"
                )
            elif current_posture_issues > 0:
                remaining.append(
                    f"{current_posture_issues} ugotovitev glede drže"
                    if lang == "sl"
                    else f"{current_posture_issues} posture finding(s)"
                    if lang == "en"
                    else f"{current_posture_issues} ευρήματα στάσης"
                )

            st.markdown("#### " + (translate(lang, "Observed improvements", "Βελτιώσεις που καταγράφηκαν")))
            if improvements:
                for item in dict.fromkeys(improvements):
                    st.markdown(f"- ✅ {item}")
            else:
                st.caption(translate(lang, "No clear improvement was identified in the selected comparison indicators.", "Δεν εντοπίστηκε σαφής βελτίωση στους συγκεκριμένους δείκτες σύγκρισης."))

            if new_issues:
                st.markdown("#### " + (translate(lang, "New issues identified", "Νέα ζητήματα που εντοπίστηκαν")))
                for item in dict.fromkeys(new_issues):
                    st.markdown(f"- 🆕 {item}")

            if remaining:
                st.markdown("#### " + (translate(lang, "Issues still requiring attention", "Ζητήματα που εξακολουθούν να χρειάζονται προσοχή")))
                for item in dict.fromkeys(remaining):
                    st.markdown(f"- ⚠️ {item}")

            comparison_payload = {
                "baseline_assessment_date": baseline_assessment.get("assessment_date"),
                "baseline_rosa": baseline_rosa,
                "followup_rosa": rosa["final"],
                "baseline_priority_findings": baseline_priority,
                "followup_priority_findings": priority_count,
                "baseline_attention_findings": baseline_attention,
                "followup_attention_findings": attention_count,
                "interventions_notes": interventions_notes,
                "improvements": list(dict.fromkeys(improvements)),
                "new_issues": list(dict.fromkeys(new_issues)),
                "remaining_issues": list(dict.fromkeys(remaining)),
            }

            st.info(
                translate(lang, "A follow-up assessment is most useful when it is performed after the agreed measures have had enough time to be implemented and used in normal work.", "Η επανεκτίμηση έχει μεγαλύτερη αξία όταν γίνεται αφού τα συμφωνημένα μέτρα έχουν εφαρμοστεί και έχουν χρησιμοποιηθεί για επαρκές διάστημα στην κανονική εργασία.")
            )

    report_payload = {
        "version": "2.2.0-alpha",
        "intended_purpose": "Office ergonomic decision support; not diagnosis or individual disease-probability prediction",
        "assessment": ctx,
        "findings": [f.to_dict() for f in findings],
        "recommendations": [r.to_dict() for r in recommendations],
        "evidence": [e.to_dict() for e in relevant_evidence],
        "comparison": comparison_payload,
    }
    report_json = json.dumps(report_payload, ensure_ascii=False, indent=2)

    st.divider()
    st.markdown("### " + (translate(lang, "Save assessment", "Αποθήκευση αξιολόγησης")))

    if sheets_ready:
        st.caption(
            (
                "Prva ocena bo ustvarila zapis stranke in prvo vrstico bloka Pred/Po v Google Sheets."
                if assessment_stage == "baseline"
                else "Druga ocena bo povezana z isto stranko, izpolnila drugo vrstico in samodejno izračunala tretjo vrstico z razlikami."
            )
            if lang == "sl"
            else (
                "The 1st assessment will create the client record and the first line of the before/after block in Google Sheets."
                if assessment_stage == "baseline"
                else "The 2nd assessment will be linked to the same client, fill the second line and automatically calculate the third difference line."
            )
            if lang == "en"
            else (
                "Η 1η αξιολόγηση θα δημιουργήσει την εγγραφή του πελάτη και την πρώτη γραμμή του μπλοκ Πριν/Μετά στο Google Sheets."
                if assessment_stage == "baseline"
                else "Η 2η αξιολόγηση θα συνδεθεί με τον ίδιο πελάτη, θα συμπληρώσει τη δεύτερη γραμμή και θα υπολογίσει αυτόματα την τρίτη γραμμή με τις διαφορές."
            )
        )
        consent = st.checkbox(
            translate(lang, "I confirm that I am authorised to store these assessment data.", "Επιβεβαιώνω ότι έχω την κατάλληλη εξουσιοδότηση για την αποθήκευση αυτών των δεδομένων αξιολόγησης."),
            key="sheets_storage_consent",
        )
        if st.button(
            translate(lang, "Save to Google Sheets", "Αποθήκευση στο Google Sheets"),
            type="primary",
            disabled=(not consent or not subject_id.strip()),
            key="save_to_google_sheets",
        ):
            ok, msg, saved_id = save_assessment_webapp(
                sheets_webapp_url,
                sheets_token,
                report_payload,
            )
            if ok:
                st.session_state["last_saved_assessment_id"] = saved_id
                st.success(
                    (
                        f"Uspešno shranjeno · {saved_id}. Stranka in 1. ocena sta bili dodani v Google Sheets."
                        if assessment_stage == "baseline"
                        else f"Uspešno shranjeno · {saved_id}. 2. ocena in vrstica razlik Pred/Po sta bili posodobljeni."
                    )
                    if lang == "sl"
                    else (
                        f"Saved successfully · {saved_id}. The client and 1st assessment were added to Google Sheets."
                        if assessment_stage == "baseline"
                        else f"Saved successfully · {saved_id}. The 2nd assessment and the before/after difference row were updated."
                    )
                    if lang == "en"
                    else (
                        f"Η αξιολόγηση αποθηκεύτηκε επιτυχώς · {saved_id}. Ο πελάτης και η 1η αξιολόγηση καταχωρίστηκαν στο Google Sheets."
                        if assessment_stage == "baseline"
                        else f"Η αξιολόγηση αποθηκεύτηκε επιτυχώς · {saved_id}. Η 2η αξιολόγηση και η γραμμή διαφορών Πριν/Μετά ενημερώθηκαν."
                    )
                )
            else:
                st.error(msg)
    else:
        st.warning(
            translate(lang, "The Google Sheet and Apps Script bridge are ready. Add the Web App URL and token to Streamlit Secrets to activate automatic saving.", "Το Google Sheet και η γέφυρα Apps Script είναι έτοιμα. Πρόσθεσε το Web App URL και το token στα Streamlit Secrets για να ενεργοποιηθεί η αυτόματη αποθήκευση.")
        )

    with st.expander(translate(lang, "Backup / export", "Αντίγραφο ασφαλείας / εξαγωγή"), expanded=False):
        st.download_button(
            t["download_json"],
            data=report_json.encode("utf-8"),
            file_name=f"ergofit_v2_{subject_id.strip() or 'assessment'}_{assessment_stage}.json",
            mime="application/json",
        )
        st.caption(t["print_note"])

st.divider()
st.caption(
    translate(lang, "ErgoFit Intelligence v2 · Scientific architecture: evidence registry + separate exposure/symptom/intervention domains · Alpha build", "ErgoFit Intelligence v2 · Επιστημονική αρχιτεκτονική: μητρώο τεκμηρίωσης + ξεχωριστοί τομείς έκθεσης/συμπτωμάτων/παρεμβάσεων · Έκδοση alpha")
)
