"""RAG pipeline for the resume chat assistant.

ingest()  -> chunk + embed resume/JD into the session's vector collection
answer()  -> retrieve top-k chunks, prepend chat history, call the LLM,
             return an answer with citations. Without an API key it returns
             an extractive answer built from the retrieved chunks.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.llm import ai_enabled, get_chat_model
from app.logging_config import get_logger
from app.schemas import ChatResponse, Citation
from app.services import memory_service
from app.services.vectorstore import Retrieved, chunk_text, get_vector_store

log = get_logger(__name__)

_SYSTEM = (
    "You are ResumeFit AI's resume assistant. Answer the user's question using "
    "ONLY the context passages provided (the candidate's resume and the target "
    "job description). If the answer is not in the context, say so plainly. "
    "Be concrete and concise. When you use a passage, cite it as [source]."
)


def ingest(session_id: str, resume_text: str, job_description: str = "") -> int:
    store = get_vector_store()
    store.reset_session(session_id)
    chunks = chunk_text(resume_text, source="resume")
    if job_description.strip():
        chunks += chunk_text(job_description, source="job_description")
    count = store.add(session_id, chunks)
    log.info("Indexed %d chunks for session %s", count, session_id)
    return count


def _format_context(passages: list[Retrieved]) -> str:
    return "\n\n".join(f"[{p.source}] {p.text}" for p in passages)


def _extractive_answer(question: str, passages: list[Retrieved]) -> str:
    if not passages:
        return (
            "I don't have any indexed content for this session yet. "
            "Upload/analyse a resume first, then ask again."
        )
    top = passages[0]
    return (
        "AI answering is disabled (no API key set), so here is the most relevant "
        f"passage from your {top.source.replace('_', ' ')}:\n\n“{top.text.strip()}”"
    )


def answer(db: Session | None, session_id: str, message: str) -> ChatResponse:
    store = get_vector_store()
    passages = store.query(session_id, message)
    hist = memory_service.history(db, session_id)

    if ai_enabled():
        try:
            from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

            model = get_chat_model()
            msgs = [SystemMessage(content=_SYSTEM)]
            for role, content in hist:
                msgs.append(
                    HumanMessage(content=content) if role == "user" else AIMessage(content=content)
                )
            msgs.append(
                HumanMessage(
                    content=f"Context passages:\n{_format_context(passages)}\n\nQuestion: {message}"
                )
            )
            reply = model.invoke(msgs).content.strip()
            ai_powered = True
        except Exception as exc:
            log.warning("RAG LLM call failed, using extractive answer: %s", exc)
            reply = _extractive_answer(message, passages)
            ai_powered = False
    else:
        reply = _extractive_answer(message, passages)
        ai_powered = False

    memory_service.append(db, session_id, "user", message)
    memory_service.append(db, session_id, "assistant", reply)

    citations = [
        Citation(source=p.source, snippet=(p.text[:240] + ("…" if len(p.text) > 240 else "")))
        for p in passages[:3]
    ]
    return ChatResponse(
        session_id=session_id,
        answer=reply,
        citations=citations,
        history_turns=len(hist) // 2 + 1,
        ai_powered=ai_powered,
    )
