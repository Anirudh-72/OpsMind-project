"""Tests for Phase 5: Verified Outcome workflow and persistent memory learning loop."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.hindsight_service import HindsightService, hindsight_service

client = TestClient(app)


def test_outcome_input_validation():
    """Verify /api/outcomes rejects invalid or incomplete submissions."""
    # Missing resolution fix
    res1 = client.post(
        "/api/outcomes",
        json={
            "service": "checkout-api",
            "confirmed_root_cause": "Database connection pool exhausted due to timeout.",
        },
    )
    assert res1.status_code == 422

    # Root cause too short (< 10 chars)
    res2 = client.post(
        "/api/outcomes",
        json={
            "service": "checkout-api",
            "confirmed_root_cause": "Short",
            "resolution_fix": "Increased pool capacity to 100",
        },
    )
    assert res2.status_code == 422

    # Invalid verification status
    res3 = client.post(
        "/api/outcomes",
        json={
            "service": "checkout-api",
            "confirmed_root_cause": "Database connection pool exhausted under load.",
            "resolution_fix": "Increased pool capacity to 100 connections.",
            "verification_status": "MAYBE",
        },
    )
    assert res3.status_code == 422


def test_full_learning_loop_scenario():
    """Verify the core hackathon story:

    1. Investigate unseen service (notification-worker) -> 0 memories.
    2. Engineer records verified outcome for notification-worker.
    3. Subsequent investigation of notification-worker -> recalls newly saved memory!
    """
    # Step 1: Initial investigation of unseen service has 0 memories
    unseen_payload = {
        "title": "Notification worker message queue consumer lag",
        "service": "notification-worker",
        "severity": "SEV-3",
        "description": "Batch notification worker is experiencing partition lag. First occurrence.",
        "log_excerpt": "consumer.go:88 partition lag",
    }
    res_initial = client.post("/api/investigate", json=unseen_payload)
    assert res_initial.status_code == 200
    data_initial = res_initial.json()
    assert len(data_initial["memory_evidence"]) == 0
    assert "No relevant past incidents" in data_initial["what_history_suggests"]

    # Step 2: Engineer investigates, fixes issue, and records verified outcome
    outcome_payload = {
        "service": "notification-worker",
        "confirmed_root_cause": "Downstream SMS gateway rate limiting triggered exponential retry backoff, choking message partition workers.",
        "resolution_fix": "Introduced asynchronous dispatch queue with circuit breaker to shed unacknowledged SMS bursts without worker blocking.",
        "verification_status": "VERIFIED",
        "notes": "Verified message processing returned to 360 msg/s across all partitions.",
    }
    res_outcome = client.post("/api/outcomes", json=outcome_payload)
    assert res_outcome.status_code == 200
    outcome_data = res_outcome.json()
    assert outcome_data["status"] == "success"
    assert "retention_result" in outcome_data
    doc_id = outcome_data["retention_result"].get("incident_id")
    assert doc_id is not None

    # Step 3: Subsequent investigation of notification-worker NOW retrieves the newly stored memory!
    res_subsequent = client.post("/api/investigate", json=unseen_payload)
    assert res_subsequent.status_code == 200
    data_subsequent = res_subsequent.json()

    # Memory evidence now contains the new outcome!
    assert len(data_subsequent["memory_evidence"]) >= 1
    recalled_ids = [m["incident_id"] for m in data_subsequent["memory_evidence"]]
    assert doc_id in recalled_ids

    # What history suggests now references the newly verified knowledge
    assert "circuit breaker" in data_subsequent["what_history_suggests"].lower() or "rate limiting" in data_subsequent["what_history_suggests"].lower()
    assert doc_id in data_subsequent["what_history_suggests"]
