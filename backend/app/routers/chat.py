from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    ChatHistoryMessage,
    ChatHistoryResponse,
    ChatIngestRequest,
    ChatIngestResponse,
    ChatRequest,
    ChatResponse,
)
from app.services import memory_service, rag_service

router = APIRouter(prefix="/api/v2/chat", tags=["chat"])


@router.post("/ingest", response_model=ChatIngestResponse)
def ingest(request: ChatIngestRequest):
    count = rag_service.ingest(request.session_id, request.resume_text, request.job_description)
    return ChatIngestResponse(session_id=request.session_id, chunks_indexed=count)


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    return rag_service.answer(db, request.session_id, request.message)


@router.get("/{session_id}/history", response_model=ChatHistoryResponse)
def history(session_id: str, db: Session = Depends(get_db)):
    msgs = memory_service.history(db, session_id)
    return ChatHistoryResponse(
        session_id=session_id,
        messages=[ChatHistoryMessage(role=r, content=c) for r, c in msgs],
    )


@router.delete("/{session_id}")
def clear(session_id: str, db: Session = Depends(get_db)):
    memory_service.clear(db, session_id)
    return {"session_id": session_id, "cleared": True}
