"""Comprehensive tests for LLMService, prompt safety, and provider resilience (Phase 4)."""

import json
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import IncidentInput, MemoryEvidenceItem
from app.services.llm_service import LLMService, llm_service

try:
    from groq import AuthenticationError, RateLimitError, APITimeoutError
except ImportError:
    AuthenticationError = Exception
    RateLimitError = Exception
    APITimeoutError = Exception

client = TestClient(app)


def test_llm_service_default_fallback_mode():
    """Verify LLM service defaults to deterministic reasoner when GROQ_API_KEY is unset."""
    svc = LLMService()
    assert svc.is_configured is False
    assert svc.client is None


def test_build_user_prompt_with_and_without_memories():
    """Verify user prompt correctly embeds incident details and memory context."""
    svc = LLMService()
    incident = IncidentInput(
        title="Checkout API timeout",
        service="checkout-api",
        severity="SEV-2",
        description="Database connection acquisition timeouts during flash sale.",
        log_excerpt="pool.go:142 timeout after 5000ms",
    )

    # 1. With memories
    memories = [
        MemoryEvidenceItem(
            incident_id="INC-2026-0417",
            title="Checkout API Pool Saturation",
            service="checkout-api",
            excerpt="Pool size 20 was exhausted under peak traffic.",
            relevance_reason="Matching service and timeout symptom.",
            historical_verification_status="VERIFIED",
            recorded_at="2026-04-17T14:22:00Z",
            source_type="simulated",
        )
    ]
    prompt_with_mem = svc.build_user_prompt(incident, memories)
    assert "INC-2026-0417" in prompt_with_mem
    assert "Pool size 20 was exhausted" in prompt_with_mem
    assert "checkout-api" in prompt_with_mem

    # 2. Without memories
    prompt_no_mem = svc.build_user_prompt(incident, [])
    assert "0 relevant historical memories found" in prompt_no_mem
    assert "Operating without historical incident precedent" in prompt_no_mem


def test_safe_read_only_diagnostic_checks():
    """Verify that generated diagnostic checks only contain safe read-only operations."""
    svc = LLMService()
    incident = IncidentInput(
        title="Database connection timeouts",
        service="checkout-api",
        severity="SEV-2",
        description="Pool connection acquisition timeouts on postgres primary.",
        log_excerpt="pool.go:142 timeout",
    )
    memories = [
        MemoryEvidenceItem(
            incident_id="INC-2026-0417",
            title="Checkout API Pool Saturation",
            service="checkout-api",
            excerpt="Pool limit 20 was too restrictive.",
            relevance_reason="Similar symptom.",
            historical_verification_status="VERIFIED",
            recorded_at="2026-04-17T14:22:00Z",
            source_type="simulated",
        )
    ]

    result = svc.generate_investigation(incident, memories)
    assert len(result.recommended_diagnostic_checks) >= 3

    forbidden_commands = ["drop", "delete", "restart", "reboot", "update", "kill -9", "truncate"]
    for check in result.recommended_diagnostic_checks:
        action_lower = check.action.lower()
        cmd_lower = (check.command_example or "").lower()
        for forbidden in forbidden_commands:
            assert forbidden not in action_lower, f"Forbidden command '{forbidden}' in action: {check.action}"
            assert forbidden not in cmd_lower, f"Forbidden command '{forbidden}' in command: {check.command_example}"


def test_mock_live_groq_successful_call():
    """Verify live Groq completion parsing when a valid JSON response is returned."""
    svc = LLMService()
    svc.is_configured = True

    mock_llm_json = {
        "incident_summary": "Checkout API experiencing pool exhaustion under traffic spike.",
        "relevant_past_incidents": ["INC-2026-0417: Similar pool exhaustion on checkout-api."],
        "what_history_suggests": "Pool exhaustion was previously verified; however, lock contention must be checked.",
        "recommended_diagnostic_checks": [
            {
                "step": 1,
                "action": "Query pg_stat_activity for waiting locks",
                "purpose": "Check if slow transactions hold connections",
                "command_example": "SELECT * FROM pg_stat_activity WHERE wait_event IS NOT NULL;",
            }
        ],
        "differences_and_uncertainty": "Current pool is 50 instead of 20; verify database server CPU first.",
        "suggested_next_step": "Run read-only query on pg_stat_activity.",
    }

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(mock_llm_json)
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    svc.client = mock_client

    incident = IncidentInput(
        title="Checkout API pool timeout",
        service="checkout-api",
        severity="SEV-2",
        description="504 errors on gateway.",
    )
    result = svc.generate_investigation(incident, [])

    assert result.incident_summary == "Checkout API experiencing pool exhaustion under traffic spike."
    assert "INC-2026-0417" in result.relevant_past_incidents[0]
    assert len(result.recommended_diagnostic_checks) == 1
    assert "groq" in result.provenance_summary["reasoner_source"]


def test_groq_error_resilience():
    """Verify service falls back safely on AuthenticationError, RateLimitError, or malformed JSON."""
    svc = LLMService()
    svc.is_configured = True

    # 1. 401 Unauthorized
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = AuthenticationError(
        "Invalid Groq API key", response=MagicMock(status_code=401), body={}
    )
    svc.client = mock_client

    incident = IncidentInput(
        title="Test incident",
        service="payment-svc",
        severity="SEV-2",
        description="Payment timeouts during transaction commit.",
    )
    result_auth_err = svc.generate_investigation(incident, [])
    assert result_auth_err.incident_summary is not None
    assert len(result_auth_err.recommended_diagnostic_checks) >= 1

    # 2. Malformed JSON
    mock_choice = MagicMock()
    mock_choice.message.content = "Not a valid JSON string"
    mock_resp = MagicMock(choices=[mock_choice])
    mock_client.chat.completions.create.side_effect = None
    mock_client.chat.completions.create.return_value = mock_resp

    result_json_err = svc.generate_investigation(incident, [])
    assert result_json_err.incident_summary is not None
    assert "deterministic_reasoner" in result_json_err.provenance_summary["reasoner_source"] or "groq_fallback" in result_json_err.provenance_summary["reasoner_source"]


def test_e2e_investigate_api_with_llm_service():
    """Verify /api/investigate routes through llm_service with 6 required sections."""
    payload = {
        "title": "Checkout API database connection acquisition timeouts",
        "service": "checkout-api",
        "severity": "SEV-2",
        "description": "API gateway reporting elevated 504 errors on /checkout/v2 endpoint during traffic surge.",
        "log_excerpt": "pool.go:142: connection acquisition timeout after 5000ms",
    }
    res = client.post("/api/investigate", json=payload)
    assert res.status_code == 200
    data = res.json()

    # Verify provenance and 6 sections
    assert "reasoner_source" in data["provenance_summary"]
    assert len(data["memory_evidence"]) >= 1
    assert data["memory_evidence"][0]["incident_id"] == "INC-2026-0417"
    assert "INC-2026-0417" in data["what_history_suggests"]
    assert len(data["recommended_diagnostic_checks"]) >= 3
    assert "pg_stat_activity" in data["suggested_next_step"]
