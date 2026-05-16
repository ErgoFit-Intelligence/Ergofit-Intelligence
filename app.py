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
from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


# ====================================================================
# Page setup
# ====================================================================
st.set_page_config(
    page_title="Ergonomic Assessment Tool",
    page_icon="🪑",
    layout="wide",
)


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

    /* ───────────────────── Green section divider above tabs ───────────────────── */
    .tabs-divider {
        margin: 26px 0 0;
        padding: 14px 22px;
        background: linear-gradient(180deg, #ecfdf5 0%, #d1fae5 100%);
        border: 1px solid #99f6e4;
        border-bottom: none;
        border-radius: 14px 14px 0 0;
        color: #064e3b !important;
        font-weight: 700;
        font-size: 12px;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .tabs-divider .brand-dot {
        width: 8px; height: 8px; border-radius: 50%;
        background: #0d9488; box-shadow: 0 0 0 4px rgba(13, 148, 136, 0.18);
        flex-shrink: 0;
    }
    .tabs-divider + div .stTabs [data-baseweb="tab-list"] {
        border-radius: 0 0 14px 14px;
        border-top-left-radius: 0 !important;
        border-top-right-radius: 0 !important;
        background: #f0fdf4;
        border-color: #99f6e4;
        border-top: 0;
        margin-top: 0;
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
                <span>ErgoFit&nbsp;·&nbsp;Intelligence</span>
            </div>
            <h1>Ergonomic Assessment Tool</h1>
            <div class="subtitle">
                The ergonomic tool that helps you work without pain.
            </div>
        </div>
        {_logo_img_html}
    </div>
    """,
    unsafe_allow_html=True,
)


# ====================================================================
# Subject — comprehensive intake panel (above tabs, always visible)
# ====================================================================
st.markdown(
    """
    <div class="section-head">
        <div class="icon-pill">👤</div>
        <div class="label">Subject profile</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True):

    # ---- Identity ----
    st.markdown('<div class="subgroup-head">Identity</div>', unsafe_allow_html=True)
    row1_id, row1_date = st.columns([3, 1])
    with row1_id:
        subject_id = st.text_input("Subject ID / name (optional)", value="")
    with row1_date:
        assess_date = st.date_input("Assessment date", value=date.today())

    # ---- Demographics ----
    st.markdown('<div class="subgroup-head">Demographics</div>', unsafe_allow_html=True)
    row2_age, row2_sex, row2_h, row2_w = st.columns(4)
    with row2_age:
        age = st.number_input(
            "Age (years)", min_value=18, max_value=100, value=35, step=1,
        )
    with row2_sex:
        sex = st.selectbox(
            "Sex",
            ["Female", "Male", "Combined average"],
        )
    with row2_h:
        height = st.selectbox(
            "Stature (cm)", options=list(range(140, 211)), index=30,
        )
    with row2_w:
        weight = st.selectbox(
            "Weight (kg)", options=list(range(40, 181)), index=30,
        )

    is_male   = (sex == "Male")
    is_female = (sex == "Female")

    # ---- Occupational exposure ----
    st.markdown('<div class="subgroup-head">Occupational exposure</div>', unsafe_allow_html=True)
    row3_c, row3_m, row3_s = st.columns(3)
    with row3_c:
        hours_computer = st.number_input(
            "Computer hours / day", min_value=0.0, max_value=16.0, value=8.0, step=0.5,
        )
    with row3_m:
        hours_mouse = st.number_input(
            "Mouse hours / day", min_value=0.0, max_value=16.0, value=4.0, step=0.5,
        )
    with row3_s:
        hours_sitting = st.number_input(
            "Total sitting hours / day", min_value=0.0, max_value=16.0, value=8.0, step=0.5,
        )

    # ---- Health & lifestyle ----
    st.markdown('<div class="subgroup-head">Health &amp; lifestyle</div>', unsafe_allow_html=True)
    row4_db, row4_sm = st.columns(2)
    with row4_db:
        diabetes = st.checkbox("Diabetes mellitus")
    with row4_sm:
        smoking = st.selectbox(
            "Smoking status",
            ["Never", "Former", "Current"],
        )

    # ---- Prior musculoskeletal injuries by region ----
    st.markdown(
        '<div class="subgroup-head">Prior musculoskeletal injuries (by region)</div>'
        '<div class="female-only-hint">Tick every region where you have had a previous injury, sprain, or chronic pain. Recurrence and chronic-pain risk is elevated for that specific region.</div>',
        unsafe_allow_html=True,
    )
    inj_row1 = st.columns(3)
    with inj_row1[0]:
        inj_neck     = st.checkbox("Neck")
    with inj_row1[1]:
        inj_shoulder = st.checkbox("Shoulder")
    with inj_row1[2]:
        inj_elbow    = st.checkbox("Elbow")
    inj_row2 = st.columns(3)
    with inj_row2[0]:
        inj_wrist    = st.checkbox("Wrist / hand")
    with inj_row2[1]:
        inj_back     = st.checkbox("Lower back / lumbar")
    with inj_row2[2]:
        inj_leg      = st.checkbox("Leg / lower extremity")

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
        '<div class="subgroup-head">Female-specific</div>'
        '<div class="female-only-hint">These fields are automatically disabled for males.</div>',
        unsafe_allow_html=True,
    )
    row5_p, row5_oc = st.columns(2)
    with row5_p:
        pregnant = st.checkbox("Currently pregnant", disabled=is_male)
    with row5_oc:
        oral_contra = st.checkbox("Oral contraceptive use", disabled=is_male)

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
    """Generate a side-view SVG of the seated worker.

    Scales body proportions by stature_cm (Drillis & Contini ratios) and
    body-width by weight (light visual cue for BMI). Chair / desk / monitor
    are drawn at their measured heights. Each item is colour-coded:
        green  → within tolerance
        amber  → just outside (≤ 2× tolerance)
        red    → significantly outside
    Head tilts up/down for monitor too high/low; feet dangle if chair too high.
    """
    OK    = "#10b981"
    WARN  = "#f59e0b"
    BAD   = "#dc2626"
    BODY  = "#1e293b"
    SKIN  = "#fde6c8"
    LINE  = "#94a3b8"
    BG    = "#f0fdfa"
    FLOOR = "#cbd5e1"

    def col(diff, tol):
        a = abs(diff)
        if a <= tol:        return OK
        if a <= tol * 2:    return WARN
        return BAD

    chair_c   = col(chair_diff,   2)
    desk_c    = col(desk_diff,    2)
    monitor_c = col(monitor_diff, 4)

    # Body proportions (Drillis & Contini fractions of stature)
    head_d    = 0.130 * stature_cm
    trunk     = 0.288 * stature_cm
    upper_arm = 0.186 * stature_cm
    forearm   = 0.146 * stature_cm
    thigh     = 0.245 * stature_cm

    # Body width scales mildly with weight (visual hint only)
    body_w = max(8, min(18, 8 + (weight_kg - 60) * 0.10))

    # SVG layout: 560 × 520, 1 cm ≈ 1.7 svg units
    scale   = 1.7
    floor_y = 470

    def y(cm): return floor_y - cm * scale

    # Person sits at x = 170 (facing right toward desk)
    pelvis_x = 170
    pelvis_y = y(chair_h)
    shoulder_x = pelvis_x
    shoulder_y = pelvis_y - trunk * scale

    head_r = (head_d * scale) / 2
    head_cx = shoulder_x
    head_cy = shoulder_y - head_r - 4

    # Head tilt for monitor misalignment
    head_tilt = 0
    if   monitor_diff >  4: head_tilt = -15   # too high → look up
    elif monitor_diff < -4: head_tilt =  18   # too low  → look down

    # Thigh horizontal forward
    knee_x = pelvis_x + thigh * scale
    knee_y = pelvis_y
    # Shin to floor (or dangling if chair too high)
    foot_x = knee_x
    foot_y = floor_y
    feet_dangle = False
    if chair_diff > 4:
        feet_dangle = True
        foot_y = pelvis_y + 0.246 * stature_cm * scale  # shin length below knee, possibly above floor

    # Arms: shoulder → elbow → hand-at-desk
    desk_y_svg = y(desk_h)
    elbow_x = shoulder_x + upper_arm * scale * 0.45
    elbow_y = shoulder_y + upper_arm * scale * 0.80
    hand_x  = elbow_x + forearm * scale * 0.95
    hand_y  = desk_y_svg

    # Desk surface
    desk_x_start = knee_x + 18
    desk_w = 200

    # Monitor (base on desk, top at monitor_h)
    mon_top_y    = y(monitor_h)
    mon_h_svg    = max(35, (monitor_h - desk_h) * scale * 0.55)
    mon_w        = 90
    mon_x        = desk_x_start + 50
    mon_bot_y    = mon_top_y + mon_h_svg

    # Build SVG
    svg = f"""
<svg viewBox="0 0 560 520" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;">
  <defs>
    <linearGradient id="bg" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="{BG}"/>
      <stop offset="1" stop-color="#ffffff"/>
    </linearGradient>
  </defs>
  <rect width="560" height="520" fill="url(#bg)" rx="14"/>

  <!-- Floor -->
  <line x1="20" y1="{floor_y}" x2="540" y2="{floor_y}" stroke="{FLOOR}" stroke-width="3"/>
  <line x1="20" y1="{floor_y+1}" x2="540" y2="{floor_y+1}" stroke="{LINE}" stroke-width="1" stroke-dasharray="4 6" opacity="0.6"/>

  <!-- Chair backrest -->
  <rect x="{pelvis_x - 38}" y="{pelvis_y - 55}" width="9" height="55"
        fill="{chair_c}" rx="2"/>
  <!-- Chair seat -->
  <rect x="{pelvis_x - 30}" y="{pelvis_y}" width="76" height="7"
        fill="{chair_c}" rx="2"/>
  <!-- Chair pedestal & base -->
  <line x1="{pelvis_x + 8}" y1="{pelvis_y + 7}" x2="{pelvis_x + 8}" y2="{floor_y - 6}"
        stroke="{LINE}" stroke-width="3"/>
  <ellipse cx="{pelvis_x + 8}" cy="{floor_y - 4}" rx="32" ry="5" fill="{LINE}"/>

  <!-- Desk -->
  <rect x="{desk_x_start}" y="{desk_y_svg}" width="{desk_w}" height="7"
        fill="{desk_c}" rx="2"/>
  <line x1="{desk_x_start + desk_w - 6}" y1="{desk_y_svg + 7}"
        x2="{desk_x_start + desk_w - 6}" y2="{floor_y}"
        stroke="{LINE}" stroke-width="2.5"/>

  <!-- Monitor -->
  <rect x="{mon_x}" y="{mon_top_y}" width="{mon_w}" height="{mon_h_svg}"
        fill="white" stroke="{monitor_c}" stroke-width="3" rx="4"/>
  <line x1="{mon_x + mon_w/2}" y1="{mon_bot_y}" x2="{mon_x + mon_w/2}" y2="{desk_y_svg}"
        stroke="{monitor_c}" stroke-width="2.5"/>
  <line x1="{mon_x + mon_w/2 - 18}" y1="{desk_y_svg}" x2="{mon_x + mon_w/2 + 18}" y2="{desk_y_svg}"
        stroke="{monitor_c}" stroke-width="2.5"/>

  <!-- Spine -->
  <line x1="{pelvis_x}" y1="{pelvis_y}" x2="{shoulder_x}" y2="{shoulder_y}"
        stroke="{BODY}" stroke-width="{body_w/1.8}" stroke-linecap="round"/>
  <!-- Trunk shading -->
  <ellipse cx="{pelvis_x}" cy="{(pelvis_y+shoulder_y)/2}"
           rx="{body_w/2 + 1}" ry="{(pelvis_y-shoulder_y)/2 - 4}"
           fill="{BODY}" opacity="0.15"/>

  <!-- Arms -->
  <line x1="{shoulder_x}" y1="{shoulder_y}" x2="{elbow_x}" y2="{elbow_y}"
        stroke="{BODY}" stroke-width="5" stroke-linecap="round"/>
  <line x1="{elbow_x}" y1="{elbow_y}" x2="{hand_x}" y2="{hand_y}"
        stroke="{BODY}" stroke-width="5" stroke-linecap="round"/>
  <circle cx="{hand_x}" cy="{hand_y}" r="4" fill="{BODY}"/>

  <!-- Thigh + shin -->
  <line x1="{pelvis_x}" y1="{pelvis_y}" x2="{knee_x}" y2="{knee_y}"
        stroke="{BODY}" stroke-width="6" stroke-linecap="round"/>
  <line x1="{knee_x}" y1="{knee_y}" x2="{foot_x}" y2="{foot_y}"
        stroke="{BODY}" stroke-width="5" stroke-linecap="round"/>
  {(f'<line x1="{foot_x-6}" y1="{foot_y}" x2="{foot_x+14}" y2="{foot_y}" stroke="{BODY}" stroke-width="4" stroke-linecap="round"/>') if not feet_dangle else ''}

  <!-- Head -->
  <g transform="rotate({head_tilt} {head_cx} {head_cy})">
    <circle cx="{head_cx}" cy="{head_cy}" r="{head_r}"
            fill="{SKIN}" stroke="{BODY}" stroke-width="2"/>
    <!-- nose -->
    <circle cx="{head_cx + head_r * 0.75}" cy="{head_cy + 2}" r="2" fill="{BODY}"/>
  </g>

  <!-- Labels -->
  <text x="{pelvis_x - 80}" y="{pelvis_y - 65}" font-size="11" font-weight="700"
        font-family="Inter, sans-serif" fill="{chair_c}">CHAIR {chair_h:.0f} cm</text>
  <text x="{desk_x_start + 6}" y="{desk_y_svg - 8}" font-size="11" font-weight="700"
        font-family="Inter, sans-serif" fill="{desk_c}">DESK {desk_h:.0f} cm</text>
  <text x="{mon_x}" y="{mon_top_y - 6}" font-size="11" font-weight="700"
        font-family="Inter, sans-serif" fill="{monitor_c}">MONITOR top {monitor_h:.0f} cm</text>

  {(f'<text x="{foot_x - 30}" y="{floor_y + 18}" font-size="10" fill="{BAD}" font-weight="700" font-family="Inter, sans-serif">Feet do not reach floor</text>') if feet_dangle else ''}
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
# Anthropometric ratios from ANSUR I
# ====================================================================
if sex_anthro == "Female-typical":
    r_popliteal, r_elbow_sit, r_eye_sit = 0.239, 0.135, 0.453
elif sex_anthro == "Male-typical":
    r_popliteal, r_elbow_sit, r_eye_sit = 0.247, 0.131, 0.451
else:
    r_popliteal, r_elbow_sit, r_eye_sit = 0.243, 0.133, 0.452

ideal_chair       = round(r_popliteal * height, 1)
seated_elbow_gap  = round(r_elbow_sit  * height, 1)
seated_eye_gap    = round(r_eye_sit    * height, 1)
ideal_desk_target = round(ideal_chair + seated_elbow_gap, 1)
ideal_mon_target  = round(ideal_chair + seated_eye_gap,   1)


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
    "dvt":                  ["leg"],
    "sleep_apnea":          [],   # injury-based factor not applicable
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
            ("Herzberg et al., 2024 — BMI & rotator cuff meta-analysis (n=525K)",
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
            ("Landesa-Piñeiro & Leirós-Rodríguez, 2022 — Prevalence systematic review",
             "10.3233/BMR-210053"),
            ("Sayampanathan et al., 2020 — Risk factors meta-analysis",
             "10.1016/j.jse.2019.11.004"),
        ],
    },

    # ----- 6. Obstructive sleep apnea --------------------------------
    "sleep_apnea": {
        "name_en": "Obstructive sleep apnea (OSA)",
        "name_gr": "Σύνδρομο υπνικής άπνοιας",
        "description": (
            "Repeated airway collapse during sleep; reduces daytime alertness "
            "and worsens posture/ergonomics at workstation. Strongly tied to BMI, "
            "less so to sex (female obesity carries higher relative risk)."
        ),
        "base_pct": 14.0,                            # adult community prevalence (moderate AHI threshold)
        "factors": {
            "bmi":            {"normal": 1.0, "overweight": 2.18, "obese": 4.84},  # Esmaeili 2025 IPD meta
            "age_over_60":     1.50,
            "sex_male":        1.50,                                               # men more affected overall
        },
        "sources": [
            ("Esmaeili et al., 2025 — IPD meta-analysis of 12,860 adults",
             "10.1016/j.eclinm.2025.103221"),
        ],
    },

    # ----- 7. Chronic venous insufficiency ---------------------------
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

    # ----- 8. Deep Vein Thrombosis (DVT) -----------------------------
    "dvt": {
        "name_en": "Deep vein thrombosis (DVT)",
        "name_gr": "Εν τω βάθει φλεβική θρόμβωση",
        "description": (
            "Blood clot formation in deep leg veins from prolonged "
            "immobility, BMI, oral contraceptives, smoking. Can be "
            "life-threatening if dislodged (pulmonary embolism)."
        ),
        "base_pct": 0.5,                             # annual incidence general population is low
        "factors": {
            "bmi":                {"normal": 1.0, "overweight": 1.50, "obese": 2.50},
            "sitting_hours_high":  2.00,                                               # "e-thrombosis" risk
            "smoking_current":     1.30,
            "oral_contra":         3.00,
            "pregnancy":           4.00,
            "age_over_60":         2.00,
        },
        "sources": [
            ("Ramaswamy & Patra, 2023 — e-Thrombosis review (prolonged sitting)",
             "10.1007/s12024-023-00704-4"),
        ],
    },
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
    c = CONDITIONS[condition_key]
    risk = float(c["base_pct"])
    f = c.get("factors", {})

    # --- BMI ---------------------------------------------------------
    if "bmi" in f:
        risk *= f["bmi"].get(ctx.get("bmi_band", "normal"), 1.0)

    # --- Occupational exposure ---------------------------------------
    if "computer_hours_high" in f and ctx.get("hours_computer", 0) >= 4:
        risk *= f["computer_hours_high"]
    if "mouse_hours_high" in f and ctx.get("hours_mouse", 0) >= 4:
        risk *= f["mouse_hours_high"]
    if "sitting_hours_high" in f and ctx.get("hours_sitting", 0) >= 6:
        risk *= f["sitting_hours_high"]

    # --- Sex ---------------------------------------------------------
    if "sex_female" in f and ctx.get("sex") == "Female":
        risk *= f["sex_female"]
    if "sex_male"   in f and ctx.get("sex") == "Male":
        risk *= f["sex_male"]

    # --- Age ---------------------------------------------------------
    age = ctx.get("age", 35)
    if "age_over_30"   in f and age > 30: risk *= f["age_over_30"]
    if "age_over_45"   in f and age > 45: risk *= f["age_over_45"]
    if "age_over_60"   in f and age > 60: risk *= f["age_over_60"]
    if "age_35_to_54"  in f and 35 <= age <= 54: risk *= f["age_35_to_54"]

    # --- Comorbidities & lifestyle -----------------------------------
    if "diabetes"        in f and ctx.get("diabetes", False):                 risk *= f["diabetes"]
    if "smoking_current" in f and ctx.get("smoking")  == "Current":           risk *= f["smoking_current"]

    # --- Prior injury — region-specific ------------------------------
    if "prior_injury" in f:
        regions   = ctx.get("injury_regions", {}) or {}
        relevant  = CONDITION_INJURY_REGIONS.get(condition_key, [])
        if any(regions.get(r, False) for r in relevant):
            risk *= f["prior_injury"]

    # --- Female-only -------------------------------------------------
    is_female = (ctx.get("sex") == "Female")
    if "pregnancy"  in f and is_female and ctx.get("pregnant",   False):      risk *= f["pregnancy"]
    if "oral_contra" in f and is_female and ctx.get("oral_contra", False):    risk *= f["oral_contra"]

    return min(round(risk, 1), 95.0)


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
            f"Chair fails > 40% of OSHA design criteria — overall poor seating",
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
            ["back_pain", "neck_strain", "venous_insufficiency", "dvt"],
        ))

    # --- Comorbidities & lifestyle -----------------------------------
    if ctx.get("diabetes", False):
        profile.append((
            "Diabetes mellitus — multiplies upper-limb tendinopathy and CTS risk",
            ["cts"],
        ))
    if ctx.get("smoking") == "Current":
        profile.append((
            "Current smoking — elevates LBP, tendinopathy, and DVT risk",
            ["back_pain", "epicondylitis_lat", "dvt"],
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
        "leg":      ("Prior leg / lower-extremity injury — elevated venous and DVT risk",
                     ["venous_insufficiency", "dvt"]),
    }
    for region, (label, conds) in region_to_label_conds.items():
        if regions.get(region, False):
            profile.append((label, conds))

    # --- Female-only ------------------------------------------------
    if ctx.get("sex") == "Female":
        if ctx.get("pregnant", False):
            profile.append((
                "Pregnancy — elevated CTS, de Quervain, venous insufficiency, DVT risk",
                ["cts", "venous_insufficiency", "dvt"],
            ))
        if ctx.get("oral_contra", False):
            profile.append((
                "Oral contraceptive use — combined with prolonged sitting amplifies DVT risk",
                ["dvt", "venous_insufficiency"],
            ))

    # --- BMI-related risk factors ------------------------------------
    if bmi_band == "overweight":
        profile.append((
            f"Overweight body composition{bmi_label} — elevated load on spine, joints, wrists",
            ["back_pain", "cts", "tendinitis_shoulder", "venous_insufficiency", "sleep_apnea"],
        ))
    elif bmi_band == "obese":
        profile.append((
            f"Obese body composition{bmi_label} — substantially elevated load on spine, joints, circulatory system",
            ["back_pain", "cts", "tendinitis_shoulder",
             "venous_insufficiency", "dvt", "sleep_apnea"],
        ))

    return profile


# ====================================================================
# Tabs — wrapped in a green "assessment sections" panel
# ====================================================================
st.markdown(
    """
    <div class="tabs-divider">
        <span class="brand-dot"></span>
        <span>Assessment Sections</span>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_ideal, tab_assessment, tab_osha, tab_angles, tab_summary = st.tabs([
    "🪑 Ideal Workstation Setup",
    "📐 Workstation Assessment",
    "✅ OSHA Chair Checklist",
    "📏 Joint Comfort Angles",
    "📋 Summary",
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
    monitor_for_actual_chair = round(chair_height + seated_eye_gap,   1)

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
    st.subheader("Chair design checklist")
    st.caption("Tick each item the chair satisfies.")

    OSHA_ITEMS = [
        ("adjust",       "Παρέχει εύκολες ρυθμίσεις"),
        ("back_tilt",    "Κλίση πλάτης ρυθμιζόμενη (συνιστώμενο εύρος 90°–120°)"),
        ("back_lock",    "Η πλάτη σταθεροποιείται σε κάθε επιλεγμένη θέση"),
        ("back_height",  "Το ύψος της πλάτης είναι κατάλληλο για τη χρήση (~23 cm χαμηλή πλάτη για ελευθερία κίνησης / ~64.5 cm μεσαία πλάτη / ~90 cm υψηλή πλάτη για πλήρη υποστήριξη)"),
        ("back_width",   "Το πλάτος της πλάτης της καρέκλας είναι ≥ 31 cm"),
        ("lumbar",       "Η πλάτη της καρέκλας υποστηρίζει την φυσική κυρτότητα της οσφυϊκής χώρας (lumbar support)"),
        ("back_angle",   "Η γωνία μεταξύ καθίσματος και πλάτης της καρέκλας είναι 90°–120°"),
        ("rounded",      "Τα άκρα της πλάτης και της έδρας είναι περιμετρικά στρογγυλεμένα"),
        ("seat_height",  "Το ύψος της έδρας είναι ρυθμιζόμενο (συνιστώμενο εύρος 42.4–52.3 cm από το έδαφος)"),
        ("seat_depth",   "Το βάθος της έδρας είναι ρυθμιζόμενο (συνιστώμενο εύρος 38–45 cm)"),
        ("seat_width",   "Το πλάτος της έδρας είναι ≥ 45 cm"),
        ("seat_tilt",    "Η έδρα έχει κλίση 0°–7° σε σχέση με το οριζόντιο επίπεδο"),
        ("seat_front",   "Το μπροστινό μέρος της έδρας έχει ελαφριά κλίση και είναι στρογγυλεμένο (waterfall type)"),
        ("seat_concave", "Η επιφάνεια της έδρας έχει ελαφρύ κοίλωμα για ομοιόμορφη στήριξη"),
        ("seat_elastic", "Το υλικό της έδρας και της πλάτης έχει κατάλληλη ελαστικότητα (cushioning)"),
        ("seat_fabric",  "Επένδυση ανθεκτική, μη ολισθηρή, υδατοδιαπερατή (αναπνέει)"),
        ("arm_height",   "Το ύψος των υποβραχιόνιων ρυθμίζεται (αποδεκτό ~25 cm από την έδρα)"),
        ("arm_distance", "Η απόσταση μεταξύ των δύο υποβραχιόνιων ρυθμίζεται (> 40 cm)"),
        ("arm_width",    "Πλάτος υποβραχιόνων ≥ 5 cm"),
        ("base",         "Βάση με ≥ 5 ακτίνες, ροδάκια απρόσκοπτης κύλισης"),
        ("swivel",       "Το κάθισμα περιστρέφεται περί του άξονά του (swivel)"),
    ]

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

    st.metric("Compliance score", f"{n_pass} / {n_total}",
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
    st.subheader("Joint comfort angles (sitting / driving posture)")
    st.caption("Enter observed angles; comfort range shown next to each.")

    JOINT_ITEMS = [
        ("trunk_vert",     "1. Κορμός — κατακόρυφος άξονας (γωνία κλίσης κορμού)",                     10,  20, 15),
        ("trunk_thigh",    "2. Κορμός — μηρός (γωνία ισχίου)",                                         90, 110, 100),
        ("thigh_shin",     "3. Μηρός — κνήμη (γωνία γόνατος)",                                         95, 120, 105),
        ("shin_foot",      "4. Κνήμη — πέλμα (γωνία ποδοκνημικής)",                                    90, 110, 100),
        ("upper_frontal",  "5. Βραχίονας — κατακόρυφος, μετωπιαίο επίπεδο (απαγωγή ώμου)",              0,  30, 10),
        ("upper_sagittal", "6. Βραχίονας — κατακόρυφος, προσθοπίσθιο επίπεδο (κάμψη ώμου)",            10,  35, 20),
        ("upper_lower",    "7. Βραχίονας — αντιβράχιο (γωνία αγκώνα)",                                 80, 160, 100),
    ]

    angle_results = {}
    for key, label, lo, hi, default in JOINT_ITEMS:
        c_label, c_input, c_status = st.columns([3, 1, 2])
        with c_label:
            st.write(f"**{label}**")
            st.caption(f"Comfort range: {lo}° – {hi}°")
        with c_input:
            angle = st.number_input(
                "Angle (°)",
                min_value=0, max_value=180, value=default, step=5,
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
    st.metric("Joints in comfort range", f"{n_ok} / {n_total_angles}")

    if n_ok < n_total_angles:
        with st.expander("Joints out of range", expanded=False):
            for label, (status, val, (lo, hi)) in angle_results.items():
                if status == "warn":
                    st.write(f"- {label}: **{val}°** (target {lo}°–{hi}°)")


# --------------------------------------------------------------------
# Tab 4 — Polished Summary
# --------------------------------------------------------------------
with tab_summary:

    sub_label = subject_id.strip() if subject_id.strip() else "Unidentified subject"

    # ---- Compute composite scoring -------------------------------
    ws_pass = sum([
        abs(chair_diff)   <= 2,
        abs(desk_diff)    <= 2,
        abs(monitor_diff) <= 4,
    ])
    ws_pct    = ws_pass / 3 * 100
    osha_pct  = (n_pass / n_total) * 100
    angle_pct = (n_ok / n_total_angles) * 100
    overall   = (ws_pct + osha_pct + angle_pct) / 3

    if   overall >= 90: band_color, band_label = "#10b981", "Excellent"
    elif overall >= 75: band_color, band_label = "#84cc16", "Good"
    elif overall >= 60: band_color, band_label = "#f59e0b", "Needs improvement"
    else:               band_color, band_label = "#ef4444", "Significant issues"

    def _quad_color(pct, good_thr, warn_thr):
        if pct >= good_thr: return "#10b981"
        if pct >= warn_thr: return "#f59e0b"
        return "#ef4444"

    ws_color    = _quad_color(ws_pct,    67, 33)
    osha_color  = _quad_color(osha_pct,  85, 60)
    angle_color = _quad_color(angle_pct, 71, 43)

    # ---- Top banner ---------------------------------------------
    st.markdown(
        f"""
        <div class="summary-banner">
            <h2>Ergonomic Assessment Report</h2>
            <div class="meta">
                <strong>{sub_label}</strong> &nbsp;·&nbsp; {assess_date.strftime("%d %b %Y")}
                &nbsp;·&nbsp; Stature {height} cm &nbsp;·&nbsp; Weight {weight} kg
                &nbsp;·&nbsp; BMI {bmi} ({bmi_cat}) &nbsp;·&nbsp; {sex}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- Big overall score card ---------------------------------
    st.markdown(
        f"""
        <div class="score-card" style="border-left: 8px solid {band_color};">
            <div>
                <div class="score-number" style="color: {band_color};">{overall:.0f}<span style="font-size: 32px;">%</span></div>
                <div class="score-label">Overall ergonomic compliance</div>
            </div>
            <div class="score-band" style="background: {band_color};">{band_label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- Three quadrant cards -----------------------------------
    q1, q2, q3 = st.columns(3)

    def _quad(title, value, subtitle, color):
        return f"""
        <div class="quad-card" style="border-top: 4px solid {color};">
            <div class="quad-title">{title}</div>
            <div class="quad-value" style="color: {color};">{value}</div>
            <div class="quad-sub">{subtitle}</div>
        </div>
        """

    q1.markdown(_quad("Anthropometric fit", f"{ws_pass}/3",
                      "Chair · Desk · Monitor", ws_color),
                unsafe_allow_html=True)
    q2.markdown(_quad("OSHA chair compliance", f"{n_pass}/{n_total}",
                      f"{osha_pct:.0f}% of criteria met", osha_color),
                unsafe_allow_html=True)
    q3.markdown(_quad("Joint comfort angles", f"{n_ok}/{n_total_angles}",
                      "joints in comfort range", angle_color),
                unsafe_allow_html=True)

    st.write("")

    # ---- Biomechanical load multipliers (BMI-adjusted) ----------
    st.markdown("### ⚖️ Biomechanical load multipliers (BMI-adjusted)")

    if bmi_band == "normal":
        st.markdown(
            f'<div class="finding-ok">✓ BMI is in the normal range '
            f'({bmi} kg/m² — {bmi_cat}). No load amplification factors applied.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption(
            f"BMI {bmi} kg/m² ({bmi_cat}) — the following multipliers are applied to baseline "
            "biomechanical loads for the assessed individual."
        )

        def _factor_color(f):
            if f >= 1.20: return "#ef4444"   # red
            if f >= 1.10: return "#f59e0b"   # amber
            if f >  1.00: return "#84cc16"   # lime
            return "#10b981"                  # green

        def _factor_card(title, factor, subtitle):
            color = _factor_color(factor)
            pct = (factor - 1.0) * 100
            return f"""
            <div style="
                padding: 14px 12px; background: white; border-radius: 10px;
                box-shadow: 0 1px 2px rgba(0,0,0,0.06);
                text-align: center; height: 100%;
                border-top: 4px solid {color};
            ">
                <div style="font-size: 10px; color: #6b7280;
                            text-transform: uppercase; letter-spacing: 0.5px;
                            font-weight: 600;">{title}</div>
                <div style="font-size: 26px; font-weight: 700; color: {color};
                            margin: 4px 0 2px;">×{factor:.2f}</div>
                <div style="font-size: 11px; color: #4b5563;">+{pct:.0f}% vs baseline</div>
                <div style="font-size: 11px; color: #6b7280; margin-top: 4px;
                            font-style: italic;">{subtitle}</div>
            </div>
            """

        f1, f2, f3, f4, f5 = st.columns(5)
        f1.markdown(_factor_card("Spine (L4/L5)",
                                 load["spine_l4l5"],
                                 "Disc compressive load"),
                    unsafe_allow_html=True)
        f2.markdown(_factor_card("Neck / trapezius",
                                 load["neck_fatigue"],
                                 "Sustained muscle fatigue"),
                    unsafe_allow_html=True)
        f3.markdown(_factor_card("Seat pressure",
                                 load["seat_pressure"],
                                 "Ischial pressure concentration"),
                    unsafe_allow_html=True)
        f4.markdown(_factor_card("Shoulder load",
                                 load["shoulder_load"],
                                 "Elevated reach demand"),
                    unsafe_allow_html=True)
        f5.markdown(_factor_card("Edema risk",
                                 load["edema_risk"],
                                 "Lower-limb fluid retention"),
                    unsafe_allow_html=True)

        # Spatial adjustments + recommended break frequency
        st.markdown("")
        info_lines = [
            f"📏 **Reach envelope adjustment:** +{load['reach_extra_cm']} cm extra clearance "
            "from desk edge (abdominal mass).",
            f"⏱️ **Recommended microbreak frequency:** every **{load['break_minutes']} minutes** "
            "(vs 60 min baseline).",
        ]
        if "com_forward_pct" in load:
            info_lines.append(
                f"⚖️ **Centre of mass:** shifted forward by ≈ {load['com_forward_pct']}% of "
                "trunk height — increases postural muscle work."
            )

        for line in info_lines:
            st.markdown(line)

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
        findings.append(f"{len(failed_osha_items)} OSHA chair criteria not met "
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
        with st.expander(f"🪑 OSHA items not met ({len(failed_osha_items)})", expanded=False):
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
        recs.append(f"Address the {len(failed_osha_items)} OSHA chair criteria not met — see detail above. "
                    "Highest-impact items are usually backrest tilt/lock, lumbar support, and seat depth.")

    if bad_angles:
        recs.append("Re-evaluate posture for joints flagged out of range. Often these are knock-on effects "
                    "of incorrect chair/desk height, so fix those first and re-check.")

    # BMI-aware break frequency
    if bmi_band == "obese":
        recs.append(
            f"**[BMI-adjusted]** Schedule a microbreak every **{load['break_minutes']} minutes** "
            "(more frequent than baseline) due to elevated edema and circulatory risk — "
            "stand, walk, calf pumps, look 6 m away for 20 sec (20-20-20)."
        )
        recs.append(
            "**[BMI-adjusted]** Footrest is **mandatory** to relieve thigh pressure; "
            "use a chair with **reinforced lumbar support**; "
            "consider a **sit-stand desk** with limited standing periods."
        )
    elif bmi_band == "overweight":
        recs.append(
            f"**[BMI-adjusted]** Schedule a microbreak every **{load['break_minutes']} minutes** — "
            "stand, walk, look 6 m away for 20 sec (20-20-20)."
        )
        recs.append(
            "**[BMI-adjusted]** Allow **2-4 cm extra clearance** between abdomen and desk edge "
            "to maintain neutral wrist/shoulder posture."
        )
    else:
        recs.append(
            "Schedule a microbreak every 30 minutes — stand, walk a few steps, "
            "look at something at least 6 m away for 20 seconds (20-20-20 rule)."
        )

    for r in recs:
        st.markdown(f"- {r}")

    # ---- Risk profile (NEW) ------------------------------------
    st.divider()
    st.markdown("### 🩺 Risk profile — conditions linked to identified risk factors")

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

    if not risk_profile:
        st.markdown(
            '<div class="finding-ok">✓ No major risk factors identified that are linked '
            'to specific musculoskeletal conditions for this assessment.</div>',
            unsafe_allow_html=True,
        )
    else:
        # Disclaimer first — important framing
        st.info(
            "**How to read this section.** Percentages below are **indicative personal estimates** "
            "computed from your intake answers (age, sex, BMI, daily hours of computer / mouse / sitting, "
            "diabetes, smoking, prior injury, pregnancy, oral contraceptives), multiplying the "
            "general-population baseline prevalence by the relative risks reported in the cited "
            "meta-analyses. They are NOT a clinical diagnosis."
        )

        # Aggregate unique conditions for a top-of-section summary
        all_condition_keys = []
        for _, conds in risk_profile:
            for c in conds:
                if c not in all_condition_keys:
                    all_condition_keys.append(c)

        st.markdown(
            f"**{len(risk_profile)} risk factor(s)** identified, linked to "
            f"**{len(all_condition_keys)} condition(s)** in the literature."
        )

        # Per-risk-factor breakdown
        for risk_label, condition_keys in risk_profile:
            with st.expander(f"⚠ {risk_label}", expanded=True):
                for ck in condition_keys:
                    c = CONDITIONS[ck]
                    personal_pct = estimated_personal_pct(ck, ctx)
                    st.markdown(
                        f"**{c['name_en']}** &nbsp;·&nbsp; *{c['name_gr']}*\n\n"
                        f"{c['description']}\n\n"
                        f"📊 General-population baseline: **{c['base_pct']}%**  \n"
                        f"🎯 Indicative personal-risk estimate (multi-factor): "
                        f"**≈ {personal_pct}%**"
                    )
                    st.markdown("")

        # Optional consolidated condition list at the end
        with st.expander("All linked conditions (consolidated list)", expanded=False):
            for ck in all_condition_keys:
                c = CONDITIONS[ck]
                personal_pct = estimated_personal_pct(ck, ctx)
                st.markdown(
                    f"- **{c['name_en']}** ({c['name_gr']}) — "
                    f"baseline {c['base_pct']}% · personal estimate **≈ {personal_pct}%**"
                )

        # ---- Pie chart of indicative personal risks --------------
        st.markdown("")
        st.markdown("#### 🥧 Indicative personal-risk distribution")
        st.caption(
            "Each segment represents one condition associated with the assessment "
            "findings. Segment size reflects the indicative personal-risk percentage "
            "(BMI-adjusted)."
        )

        chart_rows = []
        for ck in all_condition_keys:
            c = CONDITIONS[ck]
            chart_rows.append({
                "Condition": c["name_en"],
                "Greek":     c["name_gr"],
                "Risk %":    estimated_personal_pct(ck, ctx),
            })
        chart_df = pd.DataFrame(chart_rows)

        pie = (
            alt.Chart(chart_df)
            .mark_arc(innerRadius=60, stroke="#fff", strokeWidth=2)
            .encode(
                theta=alt.Theta(field="Risk %", type="quantitative"),
                color=alt.Color(
                    field="Condition", type="nominal",
                    legend=alt.Legend(title="Conditions", orient="right"),
                ),
                tooltip=[
                    alt.Tooltip("Condition:N", title="Condition"),
                    alt.Tooltip("Greek:N",     title="Ελληνικά"),
                    alt.Tooltip("Risk %:Q",    title="Indicative risk", format=".1f"),
                ],
            )
            .properties(height=380)
        )
        st.altair_chart(pie, use_container_width=True)

        st.caption(
            "⚠️ The percentages are indicative ergonomic-risk estimates, not clinical "
            "probabilities. They serve as a planning tool to prioritise interventions."
        )

    # ---- Footer -------------------------------------------------
    st.divider()
    st.caption(
        f"Report generated {assess_date.strftime('%d %b %Y')} · "
        "Save as PDF: Ctrl+P → 'Save as PDF'."
    )