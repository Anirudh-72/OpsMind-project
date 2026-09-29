"""Fictional sample incident records and test scenarios.

All data in this module is synthetic and clearly designated for demonstration
and automated testing purposes.
"""

from typing import Dict, List
from app.models.schemas import IncidentInput, SampleScenario, MemoryEvidenceItem

# Historical baseline incidents to be retained in Hindsight
HISTORICAL_INCIDENTS = [
    {
        "incident_id": "INC-2026-0417",
        "service": "checkout-api",
        "title": "Checkout API Connection Pool Saturation Under Peak Traffic",
        "symptoms": "intermittent database connection timeouts",
        "investigation_steps": "Connection pool saturation observed during flash sale. Application threads blocked waiting for available pool connection.",
        "confirmed_root_cause": "Database connection pool maximum size (20) was too restrictive for concurrency burst during peak checkout traffic.",
        "resolution_fix": "Increased pool limit from 20 to 50, added 30-second idle connection keepalive timeout, and validated recovery through Prometheus connection metrics.",
        "verification_status": "VERIFIED",
        "recorded_at": "2026-04-17T14:22:00Z",
    }
]

# Sample scenarios available for demonstration and evaluation
SAMPLE_SCENARIOS: Dict[str, SampleScenario] = {
    "scenario-a": SampleScenario(
        id="scenario-a",
        label="Scenario A: Related Historical Incident (checkout-api connection timeouts)",
        category="related",
        has_historical_match=True,
        incident=IncidentInput(
            title="Checkout API database connection acquisition timeouts",
            service="checkout-api",
            severity="SEV-2",
            description="API gateway reporting elevated 504 errors on /checkout/v2 endpoint during traffic surge. Service logs show connection acquisition timeout while attempting to communicate with Postgres primary. Current pool utilization and database health have not yet been verified.",
            log_excerpt=(
                "[checkout-api] 2026-09-27T17:14:02.411Z pool.go:142: "
                "connection acquisition timeout after 5000ms "
                "[max_pool=50, active=50, waiting=28, host=pg-primary.prod.internal:5432]"
            ),
        ),
    ),
    "scenario-b": SampleScenario(
        id="scenario-b",
        label="Scenario B: Unseen Incident (notification-worker queue delay)",
        category="unseen",
        has_historical_match=False,
        incident=IncidentInput(
            title="Notification worker message queue consumer lag",
            service="notification-worker",
            severity="SEV-3",
            description="Batch notification worker is experiencing severe consumer lag on the transactional dispatch topic. Message processing rate dropped from 350 msg/s to 12 msg/s. This newly deployed service has zero prior recorded incidents in the memory bank.",
            log_excerpt=(
                "[notification-worker] 2026-09-27T17:20:15.892Z consumer.go:88: "
                "partition lag exceeding threshold "
                "[partition=3, lag=1420 messages, processing_rate=12 msg/s, worker_id=worker-04]"
            ),
        ),
    ),
}


def get_scenario(scenario_id: str) -> SampleScenario | None:
    """Retrieve sample scenario fixture by identifier."""
    return SAMPLE_SCENARIOS.get(scenario_id)


def list_scenarios() -> List[dict]:
    """List available sample scenarios for the UI selector."""
    return [
        {
            "id": s.id,
            "label": s.label,
            "category": s.category,
            "has_historical_match": s.has_historical_match,
            "service": s.incident.service,
            "severity": s.incident.severity,
        }
        for s in SAMPLE_SCENARIOS.values()
    ]
