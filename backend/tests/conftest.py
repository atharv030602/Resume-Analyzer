"""Test config: force deterministic, DB-less, in-memory mode before app import."""

import os

os.environ.setdefault("DB_ENABLED", "false")
os.environ.setdefault("VECTOR_BACKEND", "memory")
os.environ.setdefault("LLM_PROVIDER", "gemini")
os.environ.setdefault("GOOGLE_API_KEY", "")
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("LANGSMITH_TRACING", "false")

import pytest
from fastapi.testclient import TestClient

from app.main import app

RESUME = """
Atharv Mitkari
atharv@example.com | +91 90000 00000

Summary
Backend engineer with 3 years building Python and FastAPI services.

Experience
- Built REST APIs with FastAPI and PostgreSQL, reduced p95 latency by 40%.
- Led migration of a monolith to Docker containers, cutting deploy time 60%.
- Implemented CI/CD with GitHub Actions for 12 microservices.

Skills
Python, FastAPI, Docker, PostgreSQL, REST APIs, Git, Linux

Education
B.E. Computer Science
"""

JOB_DESCRIPTION = """
We are hiring a GenAI Engineer. You will build RAG pipelines with LangChain and
LangGraph, work with embeddings and vector databases like ChromaDB, design tool
calling and memory systems, and ship FastAPI microservices with Docker and CI/CD.
Experience with LangSmith observability and AI governance is a plus. Strong
Python and REST API skills required.
"""


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture
def resume():
    return RESUME


@pytest.fixture
def jd():
    return JOB_DESCRIPTION
