"""Semantic similarity between two texts.

Uses the configured provider's embedding model when an API key is set,
otherwise a deterministic character-n-gram hashing vectoriser so the feature
still returns a meaningful score offline and in CI.
"""

from __future__ import annotations

import hashlib
import math
import re

_DIM = 512
_TOKEN_RE = re.compile(r"[a-z0-9+#.]{2,}")


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _char_ngrams(token: str, n: int = 3) -> list[str]:
    padded = f"^{token}$"
    if len(padded) <= n:
        return [padded]
    return [padded[i : i + n] for i in range(len(padded) - n + 1)]


class HashingEmbeddings:
    """Offline, dependency-free embedding compatible with LangChain's duck type."""

    dimension = _DIM

    def embed_query(self, text: str) -> list[float]:
        return self._vectorise(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vectorise(t) for t in texts]

    def _vectorise(self, text: str) -> list[float]:
        vec = [0.0] * _DIM
        for token in _tokens(text):
            for gram in _char_ngrams(token):
                bucket = int(hashlib.md5(gram.encode()).hexdigest(), 16) % _DIM
                vec[bucket] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def semantic_score(resume_text: str, job_description: str) -> int:
    """0-100 semantic alignment between a resume and a job description."""
    if not resume_text.strip() or not job_description.strip():
        return 0

    from app.core.llm import get_embeddings

    embedder = get_embeddings()
    resume_vec, jd_vec = embedder.embed_documents([resume_text, job_description])
    similarity = max(0.0, cosine_similarity(resume_vec, jd_vec))

    # Provider embeddings for related-but-distinct docs typically land in
    # 0.6-0.85; stretch that band across 0-100 so the score is legible.
    stretched = (similarity - 0.35) / 0.55
    return max(0, min(100, round(stretched * 100)))
