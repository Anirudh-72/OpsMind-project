"""Comprehensive tests for HindsightService and persistent memory workflows (Phase 3)."""

from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.hindsight_service import HindsightService, hindsight_service
from app.models.schemas import MemoryEvidenceItem

try:
    from hindsight_client_api.exceptions import UnauthorizedException, ApiException
except ImportError:
    UnauthorizedException = Exception
    ApiException = Exception

client = TestClient(app)


def test_hindsight_service_default_simulation_mode():
    """Verify service defaults to explicitly labelled simulation mode when credentials unset."""
    svc = HindsightService()
    assert svc.is_simulation is True
    status = svc.get_status()
    assert status["mode"] == "simulation_mode"
    assert status["configured"] is False
    assert "simulation mode" in status["message"].lower()


def test_hindsight_service_seed_baseline():
    """Verify seeding baseline historical incidents works."""
    svc = HindsightService()
    result = svc.seed_baseline_incidents()
    assert result["status"] == "success"
    assert result["seeded_count"] >= 1


def test_hindsight_service_recall_similar_incident():
    """Verify recall retrieves historical incident for checkout-api with honest simulation labelling."""
    svc = HindsightService()
    memories = svc.recall_relevant_memories(
        service="checkout-api",
        symptoms="intermittent database connection timeouts",
    )
    assert len(memories) >= 1
    primary = memories[0]
    assert primary.incident_id == "INC-2026-0417"
    assert primary.service == "checkout-api"
    assert primary.historical_verification_status == "VERIFIED"
    assert primary.source_type == "simulated"
    assert "SIMULATED MEMORY - HINDSIGHT NOT CONFIGURED" in primary.relevance_reason


def test_hindsight_service_recall_unseen_service():
    """Verify recall returns zero memories for unseen service without inventing history."""
    svc = HindsightService()
    memories = svc.recall_relevant_memories(
        service="notification-worker",
        symptoms="message processing delay",
    )
    assert len(memories) == 0


def test_hindsight_service_retain_and_recall_loop():
    """Verify that retaining a new incident outcome allows subsequent retrieval."""
    svc = HindsightService()
    new_incident = {
        "incident_id": "INC-2026-0927",
        "service": "billing-service",
        "title": "Payment gateway webhook signature mismatch",
        "symptoms": "webhook delivery failures",
        "investigation_steps": "Checked HMAC key rotation history",
        "confirmed_root_cause": "Clock skew between servers exceeded 300s tolerance window",
        "resolution_fix": "Resynced NTP daemon and adjusted tolerance to 600s",
        "verification_status": "VERIFIED",
    }
    retain_res = svc.retain_incident(new_incident)
    assert retain_res["success"] is True
    assert retain_res["incident_id"] == "INC-2026-0927"

    # Recall the newly stored memory
    recalled = svc.recall_relevant_memories(
        service="billing-service",
        symptoms="webhook delivery failures",
    )
    assert len(recalled) == 1
    assert recalled[0].incident_id == "INC-2026-0927"
    assert "Clock skew" in recalled[0].excerpt


def test_hindsight_client_unauthorized_error_handling():
    """Verify get_status handles 401 Unauthorized without crashing."""
    svc = HindsightService()
    svc.is_simulation = False
    mock_client = MagicMock()
    mock_client.get_bank_config.side_effect = UnauthorizedException(status=401, reason="Unauthorized")
    svc.client = mock_client

    status = svc.get_status()
    assert status["mode"] == "live_cloud"
    assert status["connected"] is False
    assert "Unauthorized" in status["error"]


def test_hindsight_client_network_error_fallback():
    """Verify retain falls back safely if network error occurs during live call."""
    svc = HindsightService()
    svc.is_simulation = False
    mock_client = MagicMock()
    mock_client.create_bank.return_value = True
    mock_client.retain.side_effect = Exception("Connection timeout after 15000ms")
    svc.client = mock_client

    result = svc.retain_incident({
        "service": "auth-service",
        "confirmed_root_cause": "Token expiration issue",
        "resolution_fix": "Refreshed token",
    })
    assert result["success"] is False
    assert result["mode"] == "error_fallback_simulated"
    assert "timeout" in result["error"].lower()


def test_api_seed_endpoint():
    """Verify /api/seed endpoint seeds baseline incidents."""
    res = client.post("/api/seed")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "Seeded" in data["message"]


def test_api_health_reports_hindsight_status():
    """Verify /api/health exposes honest Hindsight status."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert "hindsight" in data
    assert data["hindsight"]["mode"] in ["simulation_mode", "live_cloud"]
