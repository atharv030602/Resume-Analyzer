"""Per-session vector store for the resume chat assistant.

Two interchangeable backends behind one interface:

* ``ChromaVectorStore`` — persistent ChromaDB collection per session
  (``VECTOR_BACKEND=chroma``, the default).
* ``InMemoryVectorStore`` — process-local cosine search, no dependencies.
  Used automatically when chromadb is unavailable or ``VECTOR_BACKEND=memory``.

Embeddings come from ``app.core.llm.get_embeddings`` (provider model when a key
is set, deterministic hashing vectoriser otherwise).
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from functools import lru_cache

from app.config import settings
from app.core.llm import get_embeddings
from app.logging_config import get_logger
from app.services.embeddings_service import cosine_similarity

log = get_logger(__name__)


@dataclass
class Chunk:
    text: str
    source: str


@dataclass
class Retrieved:
    text: str
    source: str
    score: float


def chunk_text(
    text: str, source: str, size: int | None = None, overlap: int | None = None
) -> list[Chunk]:
    size = size or settings.rag_chunk_size
    overlap = overlap or settings.rag_chunk_overlap
    # Split on blank lines first, then pack paragraphs up to `size`.
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paras:
        if len(buf) + len(para) + 1 <= size:
            buf = f"{buf}\n{para}".strip()
        else:
            if buf:
                chunks.append(buf)
            if len(para) <= size:
                buf = para
            else:
                for i in range(0, len(para), size - overlap):
                    chunks.append(para[i : i + size])
                buf = ""
    if buf:
        chunks.append(buf)
    return [Chunk(text=c, source=source) for c in chunks if c.strip()]


class InMemoryVectorStore:
    backend = "memory"

    def __init__(self) -> None:
        self._data: dict[str, list[tuple[list[float], Chunk]]] = {}
        self._lock = threading.Lock()

    def reset_session(self, session_id: str) -> None:
        with self._lock:
            self._data.pop(session_id, None)

    def add(self, session_id: str, chunks: list[Chunk]) -> int:
        if not chunks:
            return 0
        vectors = get_embeddings().embed_documents([c.text for c in chunks])
        with self._lock:
            self._data.setdefault(session_id, []).extend(zip(vectors, chunks, strict=True))
        return len(chunks)

    def query(self, session_id: str, question: str, k: int | None = None) -> list[Retrieved]:
        k = k or settings.rag_top_k
        with self._lock:
            entries = list(self._data.get(session_id, []))
        if not entries:
            return []
        q_vec = get_embeddings().embed_query(question)
        scored = [
            Retrieved(text=chunk.text, source=chunk.source, score=cosine_similarity(q_vec, vec))
            for vec, chunk in entries
        ]
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:k]


class ChromaVectorStore:
    backend = "chroma"

    def __init__(self) -> None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        self._client = chromadb.PersistentClient(
            path=settings.chroma_dir,
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
        )
        self._embeddings = get_embeddings()
        self._lock = threading.Lock()

    def _collection(self, session_id: str):
        return self._client.get_or_create_collection(
            name=f"session_{re.sub(r'[^a-zA-Z0-9_-]', '', session_id)}",
            metadata={"hnsw:space": "cosine"},
        )

    def reset_session(self, session_id: str) -> None:
        name = f"session_{re.sub(r'[^a-zA-Z0-9_-]', '', session_id)}"
        try:
            self._client.delete_collection(name)
        except Exception:
            pass

    def add(self, session_id: str, chunks: list[Chunk]) -> int:
        if not chunks:
            return 0
        col = self._collection(session_id)
        vectors = self._embeddings.embed_documents([c.text for c in chunks])
        start = col.count()
        with self._lock:
            col.add(
                ids=[f"{session_id}-{start + i}" for i in range(len(chunks))],
                embeddings=vectors,
                documents=[c.text for c in chunks],
                metadatas=[{"source": c.source} for c in chunks],
            )
        return len(chunks)

    def query(self, session_id: str, question: str, k: int | None = None) -> list[Retrieved]:
        k = k or settings.rag_top_k
        col = self._collection(session_id)
        if col.count() == 0:
            return []
        q_vec = self._embeddings.embed_query(question)
        res = col.query(query_embeddings=[q_vec], n_results=min(k, col.count()))
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]
        out = []
        for doc, meta, dist in zip(docs, metas, dists, strict=False):
            out.append(
                Retrieved(
                    text=doc, source=(meta or {}).get("source", "document"), score=1.0 - float(dist)
                )
            )
        return out


@lru_cache(maxsize=1)
def get_vector_store():
    if settings.vector_backend.lower() == "chroma":
        try:
            store = ChromaVectorStore()
            log.info("Vector backend: ChromaDB (%s)", settings.chroma_dir)
            return store
        except Exception as exc:
            log.warning("ChromaDB unavailable (%s); falling back to in-memory store.", exc)
    log.info("Vector backend: in-memory")
    return InMemoryVectorStore()
