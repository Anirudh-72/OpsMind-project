"""FastAPI application entrypoint for OpsMind."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.data.sample_incidents import get_scenario, list_scenarios
from app.services.hindsight_service import hindsight_service
from app.services.llm_service import llm_service
from app.models.schemas import (
    IncidentInput,
    InvestigationResult,
    OutcomeInput,
    MemoryEvidenceItem,
    DiagnosticCheck,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for clean startup and teardown."""
    yield
    # Clean up client connections on server stop
    hindsight_service.close()


app = FastAPI(
    title="OpsMind API",
    description="Memory-Aware Incident Response Assistant powered by Hindsight",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

# Mount static files directory
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root():
    """Serve the root OpsMind workspace interface directly."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse(
        status_code=404,
        content={"error": "Frontend UI file not found. Ensure static directory exists."},
    )


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Return 204 No Content for favicon requests."""
    from fastapi import Response
    return Response(status_code=204)


@app.get("/api/health")
async def health_check():
    """Honest application health check reporting actual provider connection state."""
    hindsight_status = hindsight_service.get_status()
    llm_status = (
        f"groq ({settings.GROQ_MODEL})"
        if llm_service.is_configured
        else "deterministic_reasoner (No GROQ_API_KEY)"
    )

    return {
        "status": "ok",
        "app": "OpsMind",
        "version": "0.1.0",
        "hindsight": hindsight_status,
        "llm": {
            "mode": llm_status,
            "configured": llm_service.is_configured,
            "model": settings.GROQ_MODEL if llm_service.is_configured else "fallback",
        },
    }


@app.get("/api/scenarios")
async def get_scenarios():
    """List available sample demonstration scenarios."""
    return list_scenarios()


@app.get("/api/scenarios/{scenario_id}")
async def get_scenario_details(scenario_id: str):
    """Retrieve prefill incident payload for a specific scenario."""
    scenario = get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@app.post("/api/seed")
async def seed_memory_bank():
    """Explicitly seed historical incident memories into Hindsight."""
    result = hindsight_service.seed_baseline_incidents()
    return {
        "status": "success",
        "message": f"Seeded {result['seeded_count']} incident memory record(s) into Hindsight.",
        "details": result,
    }


@app.post("/api/investigate", response_model=InvestigationResult)
async def investigate_incident(incident: IncidentInput):
    """Investigate an incident using relevant memory retrieved from Hindsight and LLM reasoning."""
    # Step 1: Recall relevant memories from Hindsight
    retrieved_memories: List[MemoryEvidenceItem] = hindsight_service.recall_relevant_memories(
        service=incident.service,
        symptoms=incident.description,
        log_excerpt=incident.log_excerpt,
    )

    # Step 2: Pass incident and retrieved memories to LLM reasoning service
    investigation_result = llm_service.generate_investigation(
        incident=incident,
        memories=retrieved_memories,
    )

    return investigation_result


@app.post("/api/outcomes")
async def save_verified_outcome(outcome: OutcomeInput):
    """Save an engineer-verified outcome for future persistent memory retention."""
    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        "service": outcome.service,
        "title": f"Resolved Incident for {outcome.service}",
        "confirmed_root_cause": outcome.confirmed_root_cause,
        "resolution_fix": outcome.resolution_fix,
        "verification_status": outcome.verification_status,
        "notes": outcome.notes,
        "recorded_at": now_iso,
    }

    # Retain through Hindsight service
    retain_result = hindsight_service.retain_incident(record)

    return {
        "status": "success",
        "message": f"Verified outcome for service '{outcome.service}' retained in memory.",
        "storage_mode": retain_result.get("mode"),
        "retention_result": retain_result,
        "recorded_outcome": record,
    }
