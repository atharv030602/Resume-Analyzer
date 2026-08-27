"""Conversation memory for the chat assistant.

Backed by MySQL (``chat_session`` / ``chat_message``) when persistence is
available, otherwise a process-local dict. Same API either way.
"""

from __future__ import annotations

import threading
from collections import defaultdict

from sqlalchemy.orm import Session

from app.config import settings
from app.logging_config import get_logger

log = get_logger(__name__)

_mem: dict[str, list[tuple[str, str]]] = defaultdict(list)
_lock = threading.Lock()


def _from_db(db: Session, session_id: str):
    from app.models import ChatSession

    row = db.query(ChatSession).filter(ChatSession.session_id == session_id).one_or_none()
    if row is None:
        row = ChatSession(session_id=session_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def append(db: Session | None, session_id: str, role: str, content: str) -> None:
    if db is not None:
        from app.models import ChatMessage

        try:
            session_row = _from_db(db, session_id)
            db.add(ChatMessage(session_pk=session_row.id, role=role, content=content))
            db.commit()
            return
        except Exception as exc:  # pragma: no cover - db hiccup
            db.rollback()
            log.warning("memory append to DB failed, using in-memory: %s", exc)
    with _lock:
        _mem[session_id].append((role, content))


def history(db: Session | None, session_id: str, turns: int | None = None) -> list[tuple[str, str]]:
    limit = (turns or settings.chat_history_turns) * 2
    if db is not None:
        from app.models import ChatMessage, ChatSession

        try:
            rows = (
                db.query(ChatMessage)
                .join(ChatSession, ChatMessage.session_pk == ChatSession.id)
                .filter(ChatSession.session_id == session_id)
                .order_by(ChatMessage.id.desc())
                .limit(limit)
                .all()
            )
            return [(r.role, r.content) for r in reversed(rows)]
        except Exception as exc:  # pragma: no cover
            log.warning("memory read from DB failed, using in-memory: %s", exc)
    with _lock:
        return list(_mem.get(session_id, []))[-limit:]


def clear(db: Session | None, session_id: str) -> None:
    if db is not None:
        from app.models import ChatMessage, ChatSession

        try:
            row = db.query(ChatSession).filter(ChatSession.session_id == session_id).one_or_none()
            if row is not None:
                db.query(ChatMessage).filter(ChatMessage.session_pk == row.id).delete()
                db.commit()
        except Exception:  # pragma: no cover
            db.rollback()
    with _lock:
        _mem.pop(session_id, None)
