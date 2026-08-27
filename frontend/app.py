import os
import uuid

import plotly.graph_objects as go
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
try:
    API_BASE_URL = st.secrets.get(
        "API_BASE_URL", os.environ.get("API_BASE_URL", "http://localhost:8000/api")
    )
except Exception:
    API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000/api")

INK = "#12181b"
PANEL = "#1a2226"
PANEL_LINE = "#2a353b"
TEAL = "#6fe7c4"
AMBER = "#e8a94c"
RED = "#e2685c"
TEXT_MUTED = "#8fa3a6"

st.set_page_config(page_title="ResumeFit AI 2.0", page_icon="🎯", layout="centered")

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
    .stApp {{ background-color: {INK}; color: #e9eeee; }}
    .block-container {{ max-width: 820px; padding-top: 2.5rem; }}
    .eyebrow {{ font-family: 'IBM Plex Mono', monospace; font-size: 12px; letter-spacing: 0.14em;
        color: {TEAL}; margin-bottom: 10px; }}
    .headline {{ font-family: 'Space Grotesk', sans-serif; font-size: 34px; font-weight: 600;
        line-height: 1.15; margin-bottom: 10px; }}
    .subhead {{ color: {TEXT_MUTED}; font-size: 15px; line-height: 1.6; margin-bottom: 20px; max-width: 620px; }}
    .chip {{ display: inline-block; font-family: 'IBM Plex Mono', monospace; font-size: 12px;
        padding: 4px 9px; border-radius: 3px; margin: 3px 4px 3px 0; border: 1px solid; }}
    .chip-teal {{ color: {TEAL}; border-color: {TEAL}; background: rgba(111,231,196,0.08); }}
    .chip-amber {{ color: {AMBER}; border-color: {AMBER}; background: rgba(232,169,76,0.08); }}
    .col-title {{ font-family: 'IBM Plex Mono', monospace; font-size: 12px; letter-spacing: 0.08em;
        color: {TEXT_MUTED}; margin-bottom: 8px; }}
    .metric-row {{ font-family: 'IBM Plex Mono', monospace; font-size: 13px; color: #e9eeee;
        border-bottom: 1px solid {PANEL_LINE}; padding: 7px 0; }}
    .pass {{ color: {TEAL}; }} .fail {{ color: {AMBER}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="eyebrow">RESUMEFIT AI 2.0 — SEMANTIC + AGENTIC</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="headline">Read the signal between your resume and the role.</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="subhead">Keyword + embedding-based semantic matching, an ATS score breakdown, '
    "a tool-calling analysis agent, and a RAG chat assistant with memory over your resume + JD.</div>",
    unsafe_allow_html=True,
)

if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex

tab_fit, tab_chat = st.tabs(["  Fit Analysis  ", "  Resume Chat  "])


# ─────────────────────────────────────────────────────────────────────────
# Tab 1 — Fit analysis (v2)
# ─────────────────────────────────────────────────────────────────────────
with tab_fit:
    mode = st.radio(
        "Input mode",
        ["Paste resume text", "Upload PDF / DOCX"],
        horizontal=True,
        label_visibility="collapsed",
    )

    col1, col2 = st.columns(2)
    resume_text, resume_file = "", None
    with col1:
        st.markdown('<div class="col-title">01 — RESUME</div>', unsafe_allow_html=True)
        if mode == "Paste resume text":
            resume_text = st.text_area(
                "Resume", height=240, label_visibility="collapsed", placeholder="Paste your resume…"
            )
        else:
            resume_file = st.file_uploader(
                "Resume", type=["pdf", "docx"], label_visibility="collapsed"
            )
    with col2:
        st.markdown('<div class="col-title">02 — JOB DESCRIPTION</div>', unsafe_allow_html=True)
        job_description = st.text_area(
            "JD", height=240, label_visibility="collapsed", placeholder="Paste the job description…"
        )

    can_submit = bool(job_description.strip()) and (
        bool(resume_text.strip()) if mode == "Paste resume text" else resume_file is not None
    )

    if st.button("Run analysis", type="primary", use_container_width=True, disabled=not can_submit):
        with st.spinner("Running agent → ATS → suggestions…"):
            try:
                sid = st.session_state.session_id
                if mode == "Paste resume text":
                    resp = requests.post(
                        f"{API_BASE_URL}/v2/analyze",
                        json={
                            "resume_text": resume_text,
                            "job_description": job_description,
                            "session_id": sid,
                        },
                        timeout=180,
                    )
                else:
                    resp = requests.post(
                        f"{API_BASE_URL}/v2/analyze/upload",
                        files={"resume_file": (resume_file.name, resume_file.getvalue())},
                        data={"job_description": job_description, "session_id": sid},
                        timeout=180,
                    )
                resp.raise_for_status()
                st.session_state["result"] = resp.json()
                st.session_state["last_jd"] = job_description
                # Backend has now indexed this resume + JD into the chat session.
                st.session_state["chat_ready"] = True
            except requests.exceptions.RequestException as e:
                st.session_state["result"] = None
                detail = ""
                try:
                    detail = e.response.json().get("error", {}).get("message", "")  # type: ignore
                except Exception:
                    pass
                st.error(f"Analysis failed: {detail or e}")

    result = st.session_state.get("result")
    if result:
        score = result["fit_score"]
        zone = TEAL if score >= 70 else AMBER if score >= 40 else RED
        label = "STRONG FIT" if score >= 70 else "PARTIAL FIT" if score >= 40 else "WEAK FIT"

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=score,
                number={
                    "suffix": "/100",
                    "font": {"family": "IBM Plex Mono", "color": "#e9eeee", "size": 38},
                },
                gauge={
                    "axis": {"range": [0, 100], "tickcolor": TEXT_MUTED},
                    "bar": {"color": zone},
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
            height=250,
            margin=dict(l=30, r=30, t=24, b=6),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            f'<div style="text-align:center;font-family:\'IBM Plex Mono\',monospace;font-size:11px;'
            f'letter-spacing:0.12em;color:{zone};margin-top:-14px;">{label}</div>',
            unsafe_allow_html=True,
        )

        ats = result["ats"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("ATS overall", ats["overall"])
        c2.metric("Semantic", result["semantic_score"])
        c3.metric("Keyword", ats["keyword_coverage"])
        c4.metric("Impact lang.", ats["impact_language"])

        if result.get("degraded_reason"):
            st.info(result["degraded_reason"])
        st.caption("Agent trace: " + " → ".join(result.get("agent_trace", [])))

        d1, d2 = st.columns(2)
        with d1:
            st.markdown('<div class="col-title">● MATCHED</div>', unsafe_allow_html=True)
            st.markdown(
                "".join(f'<span class="chip chip-teal">{s}</span>' for s in result["matched_skills"])
                or f'<span style="color:{TEXT_MUTED}">none</span>',
                unsafe_allow_html=True,
            )
        with d2:
            st.markdown('<div class="col-title">● GAPS</div>', unsafe_allow_html=True)
            st.markdown(
                "".join(f'<span class="chip chip-amber">{s}</span>' for s in result["missing_skills"])
                or f'<span style="color:{TEXT_MUTED}">none</span>',
                unsafe_allow_html=True,
            )

        with st.expander("ATS checklist"):
            for chk in ats["checks"]:
                mark = "✓" if chk["passed"] else "✗"
                cls = "pass" if chk["passed"] else "fail"
                st.markdown(
                    f'<div class="metric-row"><span class="{cls}">{mark}</span> '
                    f"<b>{chk['name']}</b> — {chk['detail']}</div>",
                    unsafe_allow_html=True,
                )

        st.markdown('<div class="col-title" style="margin-top:16px">SUGGESTIONS</div>', unsafe_allow_html=True)
        for i, s in enumerate(result.get("suggestions", []), 1):
            st.markdown(f"**{i}.** {s}")

        if result.get("skill_gaps"):
            with st.expander("Skill gap detail"):
                for g in result["skill_gaps"]:
                    st.markdown(f"- **{g['skill']}** ({g['importance']}): {g['recommendation']}")

        opt = result.get("optimized_resume", "")
        if opt:
            st.download_button(
                "Download optimized resume (.txt)",
                data=opt,
                file_name="optimized_resume.txt",
                mime="text/plain",
                use_container_width=True,
            )
        st.success("This resume + JD are now loaded into the Resume Chat tab →")


# ─────────────────────────────────────────────────────────────────────────
# Tab 2 — RAG chat with memory
# ─────────────────────────────────────────────────────────────────────────
with tab_chat:
    st.markdown('<div class="col-title">RESUME CHAT ASSISTANT — RAG + MEMORY</div>', unsafe_allow_html=True)
    st.caption(f"Session: {st.session_state.session_id[:12]}")

    if not st.session_state.get("chat_ready"):
        st.info("Run a Fit Analysis first, then click “Send this resume + JD to the chat assistant”.")

    for role, content in st.session_state.get("chat_log", []):
        with st.chat_message(role):
            st.markdown(content)

    prompt = st.chat_input("Ask about your resume vs. this role…")
    if prompt:
        st.session_state.setdefault("chat_log", []).append(("user", prompt))
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"), st.spinner("Thinking…"):
            try:
                r = requests.post(
                    f"{API_BASE_URL}/v2/chat",
                    json={"session_id": st.session_state.session_id, "message": prompt},
                    timeout=120,
                )
                r.raise_for_status()
                data = r.json()
                answer = data["answer"]
                if data.get("citations"):
                    answer += "\n\n---\n" + "\n".join(
                        f"> _{c['source']}_: {c['snippet']}" for c in data["citations"]
                    )
                st.markdown(answer)
                st.session_state["chat_log"].append(("assistant", answer))
            except requests.exceptions.RequestException as e:
                st.error(f"Chat failed: {e}")

    if st.session_state.get("chat_log") and st.button("Clear conversation"):
        try:
            requests.delete(
                f"{API_BASE_URL}/v2/chat/{st.session_state.session_id}", timeout=30
            )
        except requests.exceptions.RequestException:
            pass
        st.session_state["chat_log"] = []
        st.rerun()

st.markdown(
    f'<div style="text-align:center;margin-top:40px;font-family:\'IBM Plex Mono\',monospace;'
    f'font-size:11px;color:{TEXT_MUTED};">Built by Atharv — FastAPI · LangChain · ChromaDB · '
    f"Streamlit</div>",
    unsafe_allow_html=True,
)
