"""Automated tests for Phase 2: data models, scenarios, investigation layout, and outcomes."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_scenarios():
    """Verify /api/scenarios returns available scenarios."""
    res = client.get("/api/scenarios")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 2
    ids = [s["id"] for s in data]
    assert "scenario-a" in ids
    assert "scenario-b" in ids


def test_get_scenario_details():
    """Verify /api/scenarios/{id} returns full incident payload."""
    res = client.get("/api/scenarios/scenario-a")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "scenario-a"
    assert data["has_historical_match"] is True
    assert data["incident"]["service"] == "checkout-api"
    assert "pool.go" in data["incident"]["log_excerpt"]

    res_b = client.get("/api/scenarios/scenario-b")
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["has_historical_match"] is False
    assert data_b["incident"]["service"] == "notification-worker"


def test_get_nonexistent_scenario():
    """Verify /api/scenarios/{id} returns 404 for unknown IDs."""
    res = client.get("/api/scenarios/scenario-unknown")
    assert res.status_code == 404


def test_investigate_input_validation():
    """Verify /api/investigate rejects invalid or missing fields."""
    # Missing service and description
    res = client.post("/api/investigate", json={"title": "Test"})
    assert res.status_code == 422

    # Title too short
    res2 = client.post(
        "/api/investigate",
        json={"title": "ab", "service": "srv", "description": "Short description test"},
    )
    assert res2.status_code == 422


def test_investigate_scenario_a_with_memory():
    """Verify investigation for checkout-api retrieves historical memory and suggests safe checks."""
    payload = {
        "title": "Checkout API database connection acquisition timeouts",
        "service": "checkout-api",
        "severity": "SEV-2",
        "description": "API gateway reporting elevated 504 errors on /checkout/v2 endpoint during traffic surge.",
        "log_excerpt": "pool.go:142: connection acquisition timeout after 5000ms [max_pool=50, active=50]",
    }
    res = client.post("/api/investigate", json=payload)
    assert res.status_code == 200
    data = res.json()

    # 6 required sections
    assert "incident_summary" in data
    assert len(data["relevant_past_incidents"]) > 0
    assert "INC-2026-0417" in data["relevant_past_incidents"][0]
    assert "what_history_suggests" in data
    assert len(data["recommended_diagnostic_checks"]) >= 3
    assert "differences_and_uncertainty" in data
    assert "suggested_next_step" in data

    # Memory evidence verification
    assert len(data["memory_evidence"]) == 1
    assert data["memory_evidence"][0]["incident_id"] == "INC-2026-0417"
    assert data["memory_evidence"][0]["historical_verification_status"] == "VERIFIED"

    # Verify safe read-only checks (no destructive commands)
    for check in data["recommended_diagnostic_checks"]:
        assert "drop" not in check["action"].lower()
        assert "delete" not in check["action"].lower()
        assert "restart" not in check["action"].lower()


def test_investigate_scenario_b_without_memory():
    """Verify investigation for notification-worker handles zero memory case honestly."""
    payload = {
        "title": "Notification worker message queue consumer lag",
        "service": "notification-worker",
        "severity": "SEV-3",
        "description": "Consumer lag spiked on partition 3 without historical record on this cluster.",
        "log_excerpt": "consumer.go:88: partition lag exceeding threshold",
    }
    res = client.post("/api/investigate", json=payload)
    assert res.status_code == 200
    data = res.json()

    # Honest zero memory
    assert len(data["memory_evidence"]) == 0
    assert len(data["relevant_past_incidents"]) == 0
    assert "No relevant past incidents" in data["what_history_suggests"]


def test_save_verified_outcome_endpoint():
    """Verify /api/outcomes validates input and confirms storage."""
    # Invalid payload (missing fix)
    res_bad = client.post(
        "/api/outcomes",
        json={"service": "checkout-api", "confirmed_root_cause": "Pool saturation caused by deadlock"},
    )
    assert res_bad.status_code == 422

    # Valid payload
    payload = {
        "service": "checkout-api",
        "confirmed_root_cause": "Upstream microservice deadlocks causing pool exhaustion.",
        "resolution_fix": "Patched upstream lock timeout to 2s and recycled pool.",
        "verification_status": "VERIFIED",
        "notes": "Validated zero 504 errors for 30 minutes under load.",
    }
    res = client.post("/api/outcomes", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "recorded_outcome" in data
    assert data["recorded_outcome"]["service"] == "checkout-api"
