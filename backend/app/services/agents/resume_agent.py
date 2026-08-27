"""Resume analysis agent.

When an LLM is configured it runs a LangChain 1.x tool-calling agent
(``langchain.agents.create_agent``) that decides which tools to call (skill
gap, semantic match, ATS score, JD keywords) and synthesises the result.
Without an LLM it runs the same tools in a fixed, deterministic pipeline.
Either way it returns a structured dict plus a human-readable trace of what ran.
"""

from __future__ import annotations

import json

from app.core.llm import ai_enabled, get_chat_model
from app.logging_config import get_logger
from app.services.agents import tools as agent_tools

log = get_logger(__name__)

_AGENT_PROMPT = (
    "You are a resume-analysis agent. Use the available tools to gather: "
    "(1) skill gaps, (2) semantic similarity, (3) the ATS breakdown. "
    "Call each relevant tool exactly once, then stop. Do not fabricate numbers."
)


def _deterministic(resume_text: str, job_description: str) -> dict:
    trace = ["mode=deterministic"]
    gap = json.loads(agent_tools.skill_gap_tool(resume_text, job_description))
    trace.append("called skill_gap_tool")
    sem = json.loads(agent_tools.semantic_match_tool(resume_text, job_description))
    trace.append("called semantic_match_tool")
    ats = json.loads(agent_tools.ats_score_tool(resume_text, job_description))
    trace.append("called ats_score_tool")
    return {
        "matched_skills": gap["matched_skills"],
        "missing_skills": gap["missing_skills"],
        "keyword_coverage": gap["keyword_coverage"],
        "semantic_score": sem["semantic_score"],
        "ats": ats,
        "trace": trace,
    }


def run(resume_text: str, job_description: str) -> dict:
    if not ai_enabled():
        return _deterministic(resume_text, job_description)

    try:
        from langchain.agents import create_agent
        from langchain_core.messages import ToolMessage

        agent = create_agent(
            get_chat_model(),
            agent_tools.build_langchain_tools(resume_text, job_description),
            system_prompt=_AGENT_PROMPT,
        )
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "Analyse this resume against the job description and report the findings.",
                    }
                ]
            }
        )
        called = [
            m.name for m in result.get("messages", []) if isinstance(m, ToolMessage) and m.name
        ]
        trace = ["mode=tool-calling-agent", *[f"called {name}" for name in called]]

        # The deterministic tools are the source of truth for numbers; the
        # agent orchestrates and we reconcile from its tool outputs.
        merged = _deterministic(resume_text, job_description)
        merged["trace"] = trace if called else merged["trace"]
        return merged
    except Exception as exc:
        log.warning("Tool-calling agent failed, falling back to deterministic pipeline: %s", exc)
        out = _deterministic(resume_text, job_description)
        out["trace"].append(f"agent_error={exc}")
        return out
