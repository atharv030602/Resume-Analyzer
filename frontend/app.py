import os

from dotenv import load_dotenv
import plotly.graph_objects as go
import requests
import streamlit as st

load_dotenv()
try:
    API_BASE_URL = st.secrets.get("API_BASE_URL", os.environ.get("API_BASE_URL", "http://localhost:8000/api"))
except Exception:
    API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000/api")

INK = "#12181b"
PANEL = "#1a2226"
PANEL_LINE = "#2a353b"
TEAL = "#6fe7c4"
AMBER = "#e8a94c"
RED = "#e2685c"
TEXT_MUTED = "#8fa3a6"

st.set_page_config(page_title="ResumeFit AI", page_icon="🎯", layout="centered")

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

    .stApp {{
        background-color: {INK};
        color: #e9eeee;
    }}
    .block-container {{
        max-width: 760px;
        padding-top: 3rem;
    }}
    .eyebrow {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
        letter-spacing: 0.14em;
        color: {TEAL};
        margin-bottom: 10px;
    }}
    .headline {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 36px;
        font-weight: 600;
        line-height: 1.15;
        margin-bottom: 10px;
    }}
    .subhead {{
        color: {TEXT_MUTED};
        font-size: 15px;
        line-height: 1.6;
        margin-bottom: 24px;
        max-width: 560px;
    }}
    .panel-box {{
        background: {PANEL};
        border: 1px solid {PANEL_LINE};
        border-radius: 4px;
        padding: 20px;
        margin-top: 16px;
    }}
    .chip {{
        display: inline-block;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
        padding: 4px 9px;
        border-radius: 3px;
        margin: 3px 4px 3px 0;
        border: 1px solid;
    }}
    .chip-teal {{ color: {TEAL}; border-color: {TEAL}; background: rgba(111,231,196,0.08); }}
    .chip-amber {{ color: {AMBER}; border-color: {AMBER}; background: rgba(232,169,76,0.08); }}
    .col-title {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
        letter-spacing: 0.08em;
        color: {TEXT_MUTED};
        margin-bottom: 8px;
    }}
    .notes-title {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
        letter-spacing: 0.08em;
        color: {TEXT_MUTED};
        margin: 20px 0 10px;
        border-top: 1px solid {PANEL_LINE};
        padding-top: 16px;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="eyebrow">RESUMEFIT AI — DIAGNOSTIC INSTRUMENT</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="headline">Read the signal between your resume and the role.</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="subhead">A keyword-matching engine scans your resume against a job description — '
    "instant fit score, matched/missing skills, and exactly what to fix. No AI API, no waiting.</div>",
    unsafe_allow_html=True,
)

mode = st.radio("Input mode", ["Paste resume text", "Upload PDF"], horizontal=True, label_visibility="collapsed")

col1, col2 = st.columns(2)
resume_text = ""
resume_file = None

with col1:
    st.markdown('<div class="col-title">01 — RESUME</div>', unsafe_allow_html=True)
    if mode == "Paste resume text":
        resume_text = st.text_area("Resume", height=240, label_visibility="collapsed", placeholder="Paste your resume text here...")
    else:
        resume_file = st.file_uploader("Resume PDF", type=["pdf"], label_visibility="collapsed")

with col2:
    st.markdown('<div class="col-title">02 — JOB DESCRIPTION</div>', unsafe_allow_html=True)
    job_description = st.text_area("JD", height=240, label_visibility="collapsed", placeholder="Paste the job description here...")

can_submit = bool(job_description.strip()) and (
    bool(resume_text.strip()) if mode == "Paste resume text" else resume_file is not None
)

if st.button("Run fit analysis", type="primary", use_container_width=True, disabled=not can_submit):
    with st.spinner("Running diagnostic…"):
        try:
            if mode == "Paste resume text":
                resp = requests.post(
                    f"{API_BASE_URL}/analyze/agentic",
                    json={"resume_text": resume_text, "job_description": job_description},
                    timeout=120,
                )
            else:
                resp = requests.post(
                    f"{API_BASE_URL}/analyze/upload",
                    files={"resume_file": (resume_file.name, resume_file.getvalue(), "application/pdf")},
                    data={"job_description": job_description},
                    timeout=120,
                )
            resp.raise_for_status()
            st.session_state["result"] = resp.json()
        except requests.exceptions.RequestException as e:
            st.session_state["result"] = None
            st.error(f"Analysis failed: {e}")

result = st.session_state.get("result")

if result:
    score = result["fit_score"]
    zone_color = TEAL if score >= 70 else AMBER if score >= 40 else RED
    zone_label = "STRONG SIGNAL" if score >= 70 else "PARTIAL SIGNAL" if score >= 40 else "WEAK SIGNAL"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "/100", "font": {"family": "IBM Plex Mono", "color": "#e9eeee", "size": 40}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": TEXT_MUTED, "tickfont": {"color": TEXT_MUTED}},
                "bar": {"color": zone_color},
                "bgcolor": PANEL,
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 40], "color": "rgba(226,104,92,0.12)"},
                    {"range": [40, 70], "color": "rgba(232,169,76,0.12)"},
                    {"range": [70, 100], "color": "rgba(111,231,196,0.12)"},
                ],
            },
        )
    )
    fig.update_layout(
        paper_bgcolor=INK,
        font={"color": "#e9eeee"},
        height=260,
        margin=dict(l=30, r=30, t=30, b=10),
    )

    st.markdown('<div class="panel-box">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown(
        f'<div style="text-align:center; font-family:\'IBM Plex Mono\', monospace; '
        f'font-size:11px; letter-spacing:0.12em; color:{zone_color}; margin-top:-16px;">{zone_label}</div>',
        unsafe_allow_html=True,
    )

    diff_col1, diff_col2 = st.columns(2)
    with diff_col1:
        st.markdown('<div class="col-title">● MATCHED SIGNAL</div>', unsafe_allow_html=True)
        matched = result.get("matched_skills", [])
        if matched:
            st.markdown(
                "".join(f'<span class="chip chip-teal">{s}</span>' for s in matched),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f'<span style="color:{TEXT_MUTED}; font-size:13px;">Nothing matched yet</span>', unsafe_allow_html=True)

    with diff_col2:
        st.markdown('<div class="col-title">● GAP SIGNAL</div>', unsafe_allow_html=True)
        missing = result.get("missing_skills", [])
        if missing:
            st.markdown(
                "".join(f'<span class="chip chip-amber">{s}</span>' for s in missing),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f'<span style="color:{TEXT_MUTED}; font-size:13px;">No gaps detected</span>', unsafe_allow_html=True)

    st.markdown('<div class="notes-title">INSPECTION NOTES</div>', unsafe_allow_html=True)
    for i, s in enumerate(result.get("suggestions", []), start=1):
        st.markdown(f"**{i}.** {s}")

    st.markdown("</div>", unsafe_allow_html=True)

    optimized_resume = result.get("optimized_resume", "")
    if optimized_resume:
        st.markdown('<div class="notes-title">OPTIMIZED RESUME</div>', unsafe_allow_html=True)
        with st.expander("Preview optimized resume (original + keyword alignment summary)"):
            st.text(optimized_resume)
        st.download_button(
            "Download optimized resume (.txt)",
            data=optimized_resume,
            file_name="optimized_resume.txt",
            mime="text/plain",
            use_container_width=True,
        )

st.markdown(
    f'<div style="text-align:center; margin-top:40px; font-family:\'IBM Plex Mono\', monospace; '
    f'font-size:11px; color:{TEXT_MUTED};">Built by Atharv — FastAPI + Streamlit, local keyword matching</div>',
    unsafe_allow_html=True,
)
