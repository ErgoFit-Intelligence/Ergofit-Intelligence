from __future__ import annotations

import html
import streamlit as st

from ergofit.models import EvidenceItem, Finding, Recommendation


STATUS_LABELS = {
    "information": "Information",
    "attention": "Attention",
    "priority": "Priority",
}


def finding_card(f: Finding) -> None:
    cls = {"information": "ef-info", "attention": "ef-attention", "priority": "ef-priority"}.get(f.status, "ef-info")
    st.markdown(
        f"""<div class="ef-card"><span class="ef-pill {cls}">{STATUS_LABELS.get(f.status, f.status)}</span>
        <h4>{html.escape(f.title)}</h4><div>{html.escape(f.detail)}</div></div>""",
        unsafe_allow_html=True,
    )


def evidence_card(e: EvidenceItem) -> None:
    effect = e.effect_text()
    st.markdown(
        f"""
        <div class="ef-card">
          <div class="ef-kicker">{html.escape(e.outcome.replace('_',' '))}</div>
          <h4>{html.escape(e.title)}</h4>
          <div class="ef-effect">{html.escape(effect)}</div>
          <div><b>Population:</b> {html.escape(e.population)}</div>
          <div><b>Design:</b> {html.escape(e.study_type)} · {html.escape(e.temporal_design)}</div>
          <div><b>Certainty:</b> {html.escape(e.certainty)}</div>
          <div><b>Applicability to office workers:</b> {html.escape(e.office_applicability)}</div>
          <div style="margin-top:7px;color:#5b6475">{html.escape(e.notes)}</div>
          <div class="ef-source"><a href="{html.escape(e.source_url)}" target="_blank">{html.escape(e.source_label)}</a></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def recommendation_card(r: Recommendation) -> None:
    cls = "ef-priority" if r.priority == "now" else ("ef-attention" if r.priority == "soon" else "ef-info")
    label = {"now": "Act now", "soon": "Next step", "maintain": "Maintain / context"}.get(r.priority, r.priority)
    st.markdown(
        f"""
        <div class="ef-card"><span class="ef-pill {cls}">{label}</span>
          <h4>{html.escape(r.title)}</h4>
          <div>{html.escape(r.action)}</div>
          <div style="margin-top:8px;color:#5b6475"><b>Why:</b> {html.escape(r.rationale)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
