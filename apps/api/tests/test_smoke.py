"""Smoke tests for core API endpoints.

These tests hit the real database, so they require running infra.
Run with: pytest tests/test_smoke.py -v
"""
import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "services" in data
    assert "api" in data["services"]


@pytest.mark.asyncio
async def test_list_projects(client):
    resp = await client.get("/api/projects/")
    assert resp.status_code == 200
    data = resp.json()
    assert "projects" in data
    assert isinstance(data["projects"], list)


@pytest.mark.asyncio
async def test_create_and_get_project(client):
    create_resp = await client.post(
        "/api/projects/",
        json={"title": "Test Smoke Project", "description": "Created by smoke test"},
    )
    assert create_resp.status_code == 200
    project = create_resp.json()
    pid = project["id"]
    assert project["title"] == "Test Smoke Project"

    get_resp = await client.get(f"/api/projects/{pid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == pid

    # Cleanup
    await client.delete(f"/api/projects/{pid}")


@pytest.mark.asyncio
async def test_list_jobs(client):
    resp = await client.get("/api/jobs/")
    assert resp.status_code == 200
    data = resp.json()
    assert "jobs" in data


@pytest.mark.asyncio
async def test_project_styles(client):
    """Verify global style presets are accessible."""
    create_resp = await client.post(
        "/api/projects/",
        json={"title": "Style Test Project"},
    )
    pid = create_resp.json()["id"]

    resp = await client.get(f"/api/projects/{pid}/styles")
    assert resp.status_code == 200
    data = resp.json()
    assert "presets" in data
    # Global presets should be seeded
    assert len(data["presets"]) >= 1

    await client.delete(f"/api/projects/{pid}")


@pytest.mark.asyncio
async def test_export_json(client):
    create_resp = await client.post(
        "/api/projects/",
        json={"title": "Export Test Project"},
    )
    pid = create_resp.json()["id"]

    resp = await client.get(f"/api/projects/{pid}/export/json")
    assert resp.status_code == 200
    data = resp.json()
    assert "project" in data
    assert data["project"]["title"] == "Export Test Project"

    await client.delete(f"/api/projects/{pid}")
