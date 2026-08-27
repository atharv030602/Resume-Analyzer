def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["ai_enabled"] is False
    assert body["version"].startswith("2.")


def test_v1_analyze_agentic(client, resume, jd):
    r = client.post("/api/analyze/agentic", json={"resume_text": resume, "job_description": jd})
    assert r.status_code == 200
    body = r.json()
    assert "fit_score" in body and "matched_skills" in body


def test_v2_analyze(client, resume, jd):
    r = client.post("/api/v2/analyze", json={"resume_text": resume, "job_description": jd})
    assert r.status_code == 200
    body = r.json()
    assert set(["fit_score", "semantic_score", "ats", "skill_gaps", "agent_trace"]).issubset(body)
    assert 0 <= body["ats"]["overall"] <= 100
    assert body["ai_powered"] is False
    assert body["degraded_reason"]
    assert any("skill_gap_tool" in step for step in body["agent_trace"])


def test_v2_analyze_seeds_chat_session(client, resume, jd):
    sid = "analyze-seeds-chat-01"
    r = client.post(
        "/api/v2/analyze",
        json={"resume_text": resume, "job_description": jd, "session_id": sid},
    )
    assert r.status_code == 200
    # /v2/analyze should have indexed resume + JD into the chat session.
    chat = client.post(
        "/api/v2/chat", json={"session_id": sid, "message": "summarize my background"}
    )
    assert chat.status_code == 200
    assert len(chat.json()["citations"]) >= 1


def test_v2_analyze_validation_error(client):
    r = client.post("/api/v2/analyze", json={"resume_text": "", "job_description": "x"})
    assert r.status_code == 422
    assert r.json()["error"]["type"] == "validation_error"


def test_chat_flow(client, resume, jd):
    sid = "api-test-session-01"
    ing = client.post(
        "/api/v2/chat/ingest",
        json={"session_id": sid, "resume_text": resume, "job_description": jd},
    )
    assert ing.status_code == 200
    assert ing.json()["chunks_indexed"] >= 1

    chat = client.post("/api/v2/chat", json={"session_id": sid, "message": "What are my skills?"})
    assert chat.status_code == 200
    assert chat.json()["answer"]

    hist = client.get(f"/api/v2/chat/{sid}/history")
    assert hist.status_code == 200
    assert len(hist.json()["messages"]) == 2


def test_upload_rejects_bad_type(client, jd):
    r = client.post(
        "/api/v2/analyze/upload",
        files={"resume_file": ("resume.rtf", b"nonsense", "application/rtf")},
        data={"job_description": jd},
    )
    assert r.status_code == 400
    assert r.json()["error"]["type"] == "bad_input"
