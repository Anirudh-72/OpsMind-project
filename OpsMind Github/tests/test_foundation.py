"""Foundation tests for Phase 1 (server bootstrap, health check, static files)."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify /api/health returns 200 with honest status structure."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "OpsMind"
    assert "hindsight" in data
    assert "llm" in data
    assert "mode" in data["hindsight"]


def test_root_serves_html():
    """Verify / serves the static HTML index."""
    response = client.get("/")
    assert response.status_code == 200
    assert "OpsMind" in response.text
    assert "Memory-Aware Incident Response Assistant" in response.text


def test_static_css_accessible():
    """Verify tokens.css and style.css are properly mounted and served."""
    res_tokens = client.get("/static/css/tokens.css")
    assert res_tokens.status_code == 200
    assert "--bg-canvas" in res_tokens.text
    assert "--border-default" in res_tokens.text

    res_style = client.get("/static/css/style.css")
    assert res_style.status_code == 200
    assert ".btn" in res_style.text
    assert ".panel" in res_style.text
    assert ".data-table" in res_style.text
