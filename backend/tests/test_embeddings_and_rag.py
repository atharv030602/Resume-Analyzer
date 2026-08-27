from app.services import embeddings_service, rag_service
from app.services.embeddings_service import HashingEmbeddings, cosine_similarity
from app.services.vectorstore import chunk_text, get_vector_store


def test_hashing_embeddings_are_normalised():
    vec = HashingEmbeddings().embed_query("python fastapi docker")
    assert len(vec) == HashingEmbeddings.dimension
    assert abs(sum(v * v for v in vec) ** 0.5 - 1.0) < 1e-6


def test_semantic_score_higher_for_related_text():
    related = embeddings_service.semantic_score(
        "python fastapi backend engineer docker kubernetes",
        "hiring a python backend engineer with fastapi and docker",
    )
    unrelated = embeddings_service.semantic_score(
        "medieval french poetry and renaissance art history",
        "hiring a python backend engineer with fastapi and docker",
    )
    assert related > unrelated
    assert 0 <= related <= 100


def test_cosine_bounds():
    a = [1.0, 0.0, 0.0]
    assert cosine_similarity(a, a) == 1.0
    assert cosine_similarity(a, [0.0, 1.0, 0.0]) == 0.0


def test_chunking_respects_size():
    text = "\n\n".join(f"paragraph number {i} " * 20 for i in range(10))
    chunks = chunk_text(text, source="resume", size=300, overlap=50)
    assert len(chunks) > 1
    assert all(len(c.text) <= 600 for c in chunks)
    assert all(c.source == "resume" for c in chunks)


def test_rag_ingest_and_retrieve():
    get_vector_store().reset_session("pytest-session-1")
    n = rag_service.ingest(
        "pytest-session-1",
        "I have 5 years of Python and FastAPI experience.",
        "Looking for a Python FastAPI engineer.",
    )
    assert n >= 1
    resp = rag_service.answer(None, "pytest-session-1", "What experience do I have?")
    assert resp.session_id == "pytest-session-1"
    assert resp.answer
    assert resp.ai_powered is False  # no API key in tests
    assert len(resp.citations) >= 1
