from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

NAVY = "#10114d"
NAVY_2 = "#1c215e"
GOLD = "#b8923b"
GOLD_LIGHT = "#e7d7ac"
BG = "#f7f8fb"
INK = "#111827"
MUTED = "#5b6475"


def _logo_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def apply_theme(asset_dir: Path) -> None:
    logo = asset_dir / "logo.png"
    logo_uri = _logo_data_uri(logo) if logo.exists() else ""
    st.markdown(
        f"""
        <style>
          :root {{
            --navy:{NAVY}; --navy2:{NAVY_2}; --gold:{GOLD}; --goldlight:{GOLD_LIGHT};
            --ink:{INK}; --muted:{MUTED}; --bg:{BG};
          }}
          html, body, [class*="css"], .stApp {{
            font-family: Inter, Aptos, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            color: var(--ink);
          }}
          [data-testid="stAppViewContainer"] {{ background: linear-gradient(180deg,#fbfbfd 0%,#f4f5f9 100%); }}
          .block-container {{ max-width: 1320px; padding-top: 1.5rem; padding-bottom: 4rem; }}
          h1,h2,h3,h4 {{ color:var(--navy)!important; letter-spacing:-0.02em; }}
          a {{ color:var(--navy2)!important; }}
          .ef-hero {{
            position:relative; overflow:hidden; border-radius:22px; padding:32px 36px;
            background:linear-gradient(135deg,#0d0e42 0%,#151852 60%,#252968 100%);
            border:1px solid rgba(184,146,59,.45); box-shadow:0 18px 50px rgba(16,17,77,.18);
            margin:4px 0 20px; min-height:180px; display:flex; align-items:center; justify-content:space-between; gap:28px;
          }}
          .ef-hero:after {{ content:""; position:absolute; right:-100px; top:-140px; width:420px; height:420px;
            background:radial-gradient(circle,rgba(184,146,59,.24) 0%,rgba(184,146,59,0) 68%); }}
          .ef-hero .copy {{ z-index:2; max-width:760px; }}
          .ef-hero .eyebrow {{ color:{GOLD_LIGHT}; font-size:12px; letter-spacing:.18em; font-weight:800; text-transform:uppercase; }}
          .ef-hero h1 {{ color:white!important; margin:.55rem 0 .45rem!important; font-size:38px!important; }}
          .ef-hero p {{ color:#e9eaf7!important; font-size:16px; line-height:1.55; max-width:760px; }}
          .ef-hero img {{ z-index:2; width:300px; max-width:31vw; height:auto; filter:drop-shadow(0 8px 20px rgba(0,0,0,.28)); }}
          .ef-card {{ background:white; border:1px solid #e7e9ef; border-radius:16px; padding:18px 20px; box-shadow:0 5px 18px rgba(17,24,39,.04); }}
          .ef-card h4 {{ margin:0 0 8px!important; }}
          .ef-pill {{ display:inline-flex; align-items:center; gap:6px; padding:4px 10px; border-radius:999px; font-size:12px; font-weight:800; }}
          .ef-info {{ background:#eef2ff; color:#3730a3; }}
          .ef-attention {{ background:#fff7df; color:#8a5d00; }}
          .ef-priority {{ background:#fff0f0; color:#b42318; }}
          .ef-source {{ margin-top:8px; font-size:12px; color:#667085; }}
          .ef-effect {{ font-size:18px; font-weight:800; color:var(--navy); margin:.25rem 0; }}
          .ef-summary {{ border-left:4px solid var(--gold); background:white; border-radius:12px; padding:16px 18px; margin:10px 0; }}
          .ef-kicker {{ font-size:11px; font-weight:800; letter-spacing:.14em; color:var(--gold); text-transform:uppercase; }}
          .stTabs [data-baseweb="tab-list"] {{ gap:5px; background:#eceef4; border:1px solid #e0e3eb; padding:5px; border-radius:13px; }}
          .stTabs [data-baseweb="tab"] {{ border-radius:9px; padding:9px 14px; color:#4b5563; font-weight:600; }}
          .stTabs [aria-selected="true"] {{ background:white!important; color:var(--navy)!important; box-shadow:0 2px 7px rgba(16,17,77,.1); }}
          [data-testid="stMetric"] {{ background:white; border:1px solid #e7e9ef; padding:14px; border-radius:14px; }}
          [data-testid="stSidebar"] {{ background:#f3f4f8; border-right:1px solid #e0e3eb; }}
          div.stButton > button, div.stDownloadButton > button {{ border-radius:10px; border:1px solid var(--gold); }}
          div.stButton > button[kind="primary"] {{ background:var(--navy); border-color:var(--navy); color:white; }}
          @media (max-width: 820px) {{ .ef-hero {{ padding:25px; }} .ef-hero img {{ display:none; }} .ef-hero h1 {{ font-size:31px!important; }} }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    if logo_uri:
        st.session_state["_ef_logo_uri"] = logo_uri


def hero(title: str, subtitle: str) -> None:
    logo_uri = st.session_state.get("_ef_logo_uri", "")
    img = f'<img src="{logo_uri}" alt="ErgoFit Intelligence">' if logo_uri else ""
    st.markdown(
        f"""
        <div class="ef-hero">
          <div class="copy"><div class="eyebrow">ERGOFIT · INTELLIGENCE · V2</div><h1>{title}</h1><p>{subtitle}</p></div>
          {img}
        </div>
        """,
        unsafe_allow_html=True,
    )
