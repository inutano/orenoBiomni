"""Tests for the health endpoint."""

import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "agent_ready" in data
    assert "database" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_health_checks_database(client):
    resp = await client.get("/api/v1/health")
    data = resp.json()
    assert data["database"] == "connected"
