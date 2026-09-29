"""Dedicated Hindsight persistent memory service for OpsMind.

Integrates with official Vectorize.io Hindsight SDK (`hindsight-client`).
Provides incident retention, multi-strategy recall, memory bank lifecycle,
and an explicitly labelled simulation fallback when credentials are not configured.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from app.config import settings
from app.data.sample_incidents import HISTORICAL_INCIDENTS
from app.models.schemas import MemoryEvidenceItem

logger = logging.getLogger("opsmind.hindsight")

# Attempt importing official Hindsight SDK classes
try:
    from hindsight_client import Hindsight
    from hindsight_client_api.exceptions import (
        ApiException,
        UnauthorizedException,
        NotFoundException,
    )
    HINDSIGHT_SDK_AVAILABLE = True
except ImportError:
    HINDSIGHT_SDK_AVAILABLE = False


class HindsightService:
    """Manages persistent memory operations with Hindsight."""

    def __init__(self, config=settings):
        self.config = config
        self.bank_id = config.HINDSIGHT_BANK_ID
        self.base_url = config.HINDSIGHT_API_URL
        self.api_key = config.HINDSIGHT_API_KEY
        self.client: Optional[Any] = None
        self.is_simulation: bool = True

        # In-memory store for simulation mode
        self.simulated_bank: List[Dict[str, Any]] = []

        self._initialize_client()
        self._initialize_simulation_data()

    def _initialize_client(self) -> None:
        """Instantiate official Hindsight client if credentials are configured."""
        if not HINDSIGHT_SDK_AVAILABLE:
            logger.warning("hindsight-client package not installed. Running in simulation mode.")
            self.is_simulation = True
            return

        if self.config.has_hindsight_credentials:
            try:
                self.client = Hindsight(
                    base_url=self.base_url,
                    api_key=self.api_key,
                    timeout=15.0,
                    user_agent="OpsMind-Assistant/0.1.0",
                )
                self.is_simulation = False
                logger.info("Initialized live Hindsight client pointing to %s", self.base_url)
            except Exception as e:
                logger.error("Failed to initialize Hindsight client: %s. Falling back to simulation.", e)
                self.client = None
                self.is_simulation = True
        else:
            self.client = None
            self.is_simulation = True
            logger.info("No Hindsight API key configured. Active mode: SIMULATION.")

    def _initialize_simulation_data(self) -> None:
        """Populate simulated bank with baseline historical incidents."""
        self.simulated_bank = [dict(item) for item in HISTORICAL_INCIDENTS]

    def reset_to_baseline(self) -> None:
        """Reset simulated memory bank to baseline historical fixtures."""
        self._initialize_simulation_data()

    def get_status(self) -> Dict[str, Any]:
        """Check live connection status to Hindsight memory bank."""
        if self.is_simulation or not self.client:
            return {
                "mode": "simulation_mode",
                "configured": False,
                "connected": False,
                "endpoint": self.base_url,
                "bank_id": self.bank_id,
                "message": "Hindsight running in local simulation mode. Set HINDSIGHT_API_KEY in .env for live cloud.",
            }

        try:
            # Query bank config to verify connectivity and credentials
            config = self.client.get_bank_config(bank_id=self.bank_id)
            return {
                "mode": "live_cloud",
                "configured": True,
                "connected": True,
                "endpoint": self.base_url,
                "bank_id": self.bank_id,
                "bank_config": config,
                "message": "Connected to Hindsight Cloud.",
            }
        except NotFoundException:
            return {
                "mode": "live_cloud",
                "configured": True,
                "connected": True,
                "endpoint": self.base_url,
                "bank_id": self.bank_id,
                "message": f"Connected to Hindsight, but bank '{self.bank_id}' is not yet initialized. Use seed endpoint.",
            }
        except UnauthorizedException:
            return {
                "mode": "live_cloud",
                "configured": True,
                "connected": False,
                "endpoint": self.base_url,
                "bank_id": self.bank_id,
                "error": "Invalid Hindsight API key (401 Unauthorized).",
            }
        except Exception as e:
            return {
                "mode": "live_cloud",
                "configured": True,
                "connected": False,
                "endpoint": self.base_url,
                "bank_id": self.bank_id,
                "error": f"Connection error: {str(e)}",
            }

    def ensure_bank_exists(self) -> Dict[str, Any]:
        """Ensure the target memory bank exists in Hindsight."""
        if self.is_simulation or not self.client:
            return {"status": "success", "mode": "simulated", "bank_id": self.bank_id}

        try:
            self.client.create_bank(
                bank_id=self.bank_id,
                name="OpsMind Incident Memory",
                mission="Persistent engineering incident memory bank for OpsMind incident response agent.",
            )
            return {"status": "created", "mode": "live_cloud", "bank_id": self.bank_id}
        except ApiException as e:
            # Bank already exists or similar non-fatal status
            return {"status": "exists", "mode": "live_cloud", "bank_id": self.bank_id, "detail": str(e)}
        except Exception as e:
            logger.error("Error creating bank: %s", e)
            return {"status": "error", "mode": "live_cloud", "error": str(e)}

    def retain_incident(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """Retain an incident record into persistent memory."""
        incident_id = incident_data.get("incident_id") or f"INC-{datetime.now(timezone.utc).strftime('%Y-%m%d-%H%M')}"
        service = incident_data.get("service", "unknown-service")
        title = incident_data.get("title", "Technical Incident")
        symptoms = incident_data.get("symptoms", "")
        steps = incident_data.get("investigation_steps", "")
        cause = incident_data.get("confirmed_root_cause", "")
        fix = incident_data.get("resolution_fix", "")
        status = incident_data.get("verification_status", "VERIFIED")
        recorded_at = incident_data.get("recorded_at") or datetime.now(timezone.utc).isoformat()

        # Structured memory content for extraction
        content = (
            f"Incident Identifier: {incident_id}\n"
            f"Service/Component: {service}\n"
            f"Incident Title: {title}\n"
            f"Observed Symptoms: {symptoms}\n"
            f"Investigation Steps: {steps}\n"
            f"Confirmed Root Cause: {cause}\n"
            f"Verified Resolution: {fix}\n"
            f"Verification Status: {status}\n"
            f"Recorded At: {recorded_at}\n"
        )

        if not self.is_simulation and self.client:
            try:
                self.ensure_bank_exists()
                response = self.client.retain(
                    bank_id=self.bank_id,
                    content=content,
                    document_id=incident_id,
                    tags=[service, "incident", status.lower()],
                )
                logger.info("Successfully retained incident %s in Hindsight Cloud", incident_id)
                return {
                    "success": True,
                    "mode": "hindsight_cloud",
                    "incident_id": incident_id,
                    "items_count": getattr(response, "items_count", 1),
                }
            except Exception as e:
                logger.error("Hindsight retention failed: %s. Falling back to local store.", e)
                # Fallback to local store if live call fails
                self.simulated_bank.append({
                    "incident_id": incident_id,
                    "service": service,
                    "title": title,
                    "symptoms": symptoms,
                    "investigation_steps": steps,
                    "confirmed_root_cause": cause,
                    "resolution_fix": fix,
                    "verification_status": status,
                    "recorded_at": recorded_at,
                })
                return {
                    "success": False,
                    "mode": "error_fallback_simulated",
                    "incident_id": incident_id,
                    "error": str(e),
                }

        # Simulation Mode (Idempotent update by incident_id)
        new_record = {
            "incident_id": incident_id,
            "service": service,
            "title": title,
            "symptoms": symptoms,
            "investigation_steps": steps,
            "confirmed_root_cause": cause,
            "resolution_fix": fix,
            "verification_status": status,
            "recorded_at": recorded_at,
        }
        for i, existing in enumerate(self.simulated_bank):
            if existing.get("incident_id") == incident_id:
                self.simulated_bank[i] = new_record
                return {
                    "success": True,
                    "mode": "simulated",
                    "incident_id": incident_id,
                    "items_count": 1,
                    "action": "updated",
                }

        self.simulated_bank.append(new_record)
        return {
            "success": True,
            "mode": "simulated",
            "incident_id": incident_id,
            "items_count": 1,
            "action": "created",
        }

    def recall_relevant_memories(
        self, service: str, symptoms: str, log_excerpt: Optional[str] = None
    ) -> List[MemoryEvidenceItem]:
        """Retrieve relevant past incident memories from Hindsight."""
        query = (
            f"Incident involving service '{service}'. "
            f"Reported symptoms: {symptoms}. "
            f"Error details: {log_excerpt or 'None provided.'}"
        )

        # 1. Real Hindsight Cloud Retrieval
        if not self.is_simulation and self.client:
            try:
                response = self.client.recall(
                    bank_id=self.bank_id,
                    query=query,
                    max_tokens=2048,
                    budget="mid",
                )

                results = getattr(response, "results", []) or []
                evidence_items: List[MemoryEvidenceItem] = []

                for r in results:
                    text = getattr(r, "text", "")
                    doc_id = getattr(r, "document_id", None) or getattr(r, "id", "UNKNOWN-INCIDENT")
                    occurred = (
                        getattr(r, "occurred_start", None)
                        or getattr(r, "mentioned_at", None)
                        or datetime.now(timezone.utc).isoformat()
                    )

                    evidence_items.append(
                        MemoryEvidenceItem(
                            incident_id=doc_id,
                            title=f"Historical Incident ({doc_id})",
                            service=service,
                            excerpt=text,
                            relevance_reason="Retrieved from Hindsight memory bank via TEMPR multi-strategy search.",
                            historical_verification_status="VERIFIED",
                            recorded_at=occurred,
                            source_type="hindsight_cloud",
                        )
                    )
                return evidence_items

            except Exception as e:
                logger.error("Hindsight recall failed: %s. Falling back to simulation.", e)

        # 2. Honest Simulated Fallback (Explicitly Labelled)
        matches: List[MemoryEvidenceItem] = []
        seen_ids = set()
        svc_lower = service.lower().strip()

        for item in self.simulated_bank:
            inc_id = item.get("incident_id")
            if inc_id in seen_ids:
                continue

            item_svc = item["service"].lower().strip()
            # Match on identical service or pool/checkout keywords
            if (
                item_svc == svc_lower
                or (svc_lower in item_svc)
                or ("checkout" in svc_lower and "checkout" in item_svc)
            ):
                if inc_id:
                    seen_ids.add(inc_id)
                excerpt = (
                    f"Symptom: {item['symptoms']}. "
                    f"Confirmed Cause: {item['confirmed_root_cause']}. "
                    f"Verified Resolution: {item['resolution_fix']}."
                )
                matches.append(
                    MemoryEvidenceItem(
                        incident_id=item["incident_id"],
                        title=item["title"],
                        service=item["service"],
                        excerpt=excerpt,
                        relevance_reason="[SIMULATED MEMORY - HINDSIGHT NOT CONFIGURED] Match on service and symptom.",
                        historical_verification_status=item.get("verification_status", "VERIFIED"),
                        recorded_at=item.get("recorded_at", datetime.now(timezone.utc).isoformat()),
                        source_type="simulated",
                    )
                )

        return matches

    def seed_baseline_incidents(self) -> Dict[str, Any]:
        """Seed baseline historical incident(s) into Hindsight."""
        seeded_count = 0
        results = []

        for inc in HISTORICAL_INCIDENTS:
            res = self.retain_incident(inc)
            results.append(res)
            if res.get("success"):
                seeded_count += 1

        return {
            "status": "success",
            "mode": "simulated" if self.is_simulation else "hindsight_cloud",
            "seeded_count": seeded_count,
            "details": results,
        }

    def close(self) -> None:
        """Close underlying client connections cleanly."""
        if self.client and hasattr(self.client, "close"):
            try:
                self.client.close()
            except Exception:
                pass


# Global singleton instance
hindsight_service = HindsightService()
