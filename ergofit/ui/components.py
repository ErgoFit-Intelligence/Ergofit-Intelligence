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
}


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
    effect = e.effect_text()
    if lang == "el" and e.estimate is None:
        effect = labels["no_effect"]
    outcome = e.outcome.replace("_", " ") if lang == "en" else OUTCOME_LABELS_EL.get(e.outcome, e.outcome.replace("_", " "))
    title = e.title if lang == "en" else EVIDENCE_TITLE_EL.get(e.title, e.title)
    st.markdown(
        f"""
        <div class="ef-card">
          <div class="ef-kicker">{html.escape(outcome)}</div>
          <h4>{html.escape(title)}</h4>
          <div class="ef-effect">{html.escape(effect)}</div>
          <div><b>{labels["population"]}:</b> {html.escape(e.population)}</div>
          <div><b>{labels["design"]}:</b> {html.escape(e.study_type)} · {html.escape(e.temporal_design)}</div>
          <div><b>{labels["certainty"]}:</b> {html.escape(e.certainty)}</div>
          <div><b>{labels["applicability"]}:</b> {html.escape(e.office_applicability)}</div>
          <div style="margin-top:7px;color:#5b6475">{html.escape(e.notes)}</div>
          <div class="ef-source"><a href="{html.escape(e.source_url)}" target="_blank">{html.escape(e.source_label)}</a></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
