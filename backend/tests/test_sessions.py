"""Tests for session CRUD endpoints."""

import pytest


@pytest.mark.asyncio
async def test_create_session(client):
    resp = await client.post("/api/v1/sessions", json={"title": "Test Session"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Session"
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_create_session_no_title(client):
    resp = await client.post("/api/v1/sessions", json={})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] is None


@pytest.mark.asyncio
async def test_list_sessions(client):
    # Create two sessions
    await client.post("/api/v1/sessions", json={"title": "S1"})
    await client.post("/api/v1/sessions", json={"title": "S2"})

    resp = await client.get("/api/v1/sessions")
    assert resp.status_code == 200
    sessions = resp.json()
    assert len(sessions) >= 2


@pytest.mark.asyncio
async def test_get_session(client):
    create_resp = await client.post("/api/v1/sessions", json={"title": "Get Me"})
    session_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/sessions/{session_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == session_id
    assert data["title"] == "Get Me"
    assert "messages" in data


@pytest.mark.asyncio
async def test_get_nonexistent_session(client):
    resp = await client.get("/api/v1/sessions/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_session(client):
    create_resp = await client.post("/api/v1/sessions", json={"title": "Delete Me"})
    session_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/sessions/{session_id}")
    assert resp.status_code == 204

    # Verify it's gone
    resp = await client.get(f"/api/v1/sessions/{session_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_chat_validation_empty_message(client):
    create_resp = await client.post("/api/v1/sessions", json={"title": "Validate"})
    session_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/sessions/{session_id}/chat",
        json={"message": ""},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_chat_validation_too_long(client):
    create_resp = await client.post("/api/v1/sessions", json={"title": "Long"})
    session_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/sessions/{session_id}/chat",
        json={"message": "x" * 33000},
    )
    assert resp.status_code == 422
