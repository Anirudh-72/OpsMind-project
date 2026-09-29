"""
Phase 6 Deliverables & Quality Assurance Tests
Validates:
1. Static asset delivery and syntax validity.
2. AGENTS.md design constraints (zero emojis, strict radii, no prohibited gradients/effects).
3. End-to-end integration and learning loop sanity.
"""

import glob
import re
import pytest
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)

EMOJI_PATTERN = re.compile(
    r"[\U0001F600-\U0001F64F"
    r"\U0001F300-\U0001F5FF"
    r"\U0001F680-\U0001F6FF"
    r"\U0001F1E0-\U0001F1FF"
    r"\U00002702-\U000027B0"
    r"\U000024C2-\U0001F251"
    r"\U0001F900-\U0001F9FF"
    r"\U0001FA70-\U0001FAFF]",
    flags=re.UNICODE,
)


def test_static_assets_all_load():
    """Verify all front-end assets return 200 with appropriate content types."""
    # HTML
    res_html = client.get("/")
    assert res_html.status_code == 200
    assert "OpsMind" in res_html.text
    assert "<!DOCTYPE html>" in res_html.text

    # Tokens CSS
    res_tokens = client.get("/static/css/tokens.css")
    assert res_tokens.status_code == 200
    assert "--bg-canvas" in res_tokens.text

    # Main CSS
    res_style = client.get("/static/css/style.css")
    assert res_style.status_code == 200
    assert ".workspace-grid" in res_style.text

    # JavaScript
    res_js = client.get("/static/js/app.js")
    assert res_js.status_code == 200
    assert "DOMContentLoaded" in res_js.text


def test_zero_emojis_in_source_files():
    """Verify AGENTS.md rule: 'No emojis anywhere in the UI' and source files."""
    violating_files = []
    for ext in ["py", "html", "css", "js"]:
        for fpath in glob.glob(f"app/**/*.{ext}", recursive=True):
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
                matches = EMOJI_PATTERN.findall(content)
                if matches:
                    violating_files.append((fpath, matches))

    assert len(violating_files) == 0, f"Found emojis in source files: {violating_files}"


def test_design_tokens_adhere_to_agents_rules():
    """Verify design tokens adhere to maximum radii and styling rules."""
    with open("app/static/css/tokens.css", "r", encoding="utf-8") as f:
        tokens_css = f.read()

    # Max panel border radius: 6px
    panel_radius_match = re.search(r"--radius-panel:\s*(\d+)px", tokens_css)
    assert panel_radius_match is not None
    assert int(panel_radius_match.group(1)) <= 6

    # Max button/input border radius: 4px
    control_radius_match = re.search(r"--radius-control:\s*(\d+)px", tokens_css)
    assert control_radius_match is not None
    assert int(control_radius_match.group(1)) <= 4

    # No forbidden gradients/colors: purple, indigo, violet, neon cyan, magenta
    prohibited_terms = ["purple", "indigo", "violet", "neon cyan", "magenta", "glassmorphism", "backdrop-filter"]
    for term in prohibited_terms:
        assert term not in tokens_css.lower(), f"Prohibited design term '{term}' found in tokens.css"

    with open("app/static/css/style.css", "r", encoding="utf-8") as f:
        style_css = f.read()
    for term in prohibited_terms:
        assert term not in style_css.lower(), f"Prohibited design term '{term}' found in style.css"


def test_javascript_syntax_and_brace_balance():
    """Verify JavaScript file has perfectly balanced braces."""
    with open("app/static/js/app.js", "r", encoding="utf-8") as f:
        code = f.read()

    # Strip comments to ensure no stray characters
    cleaned = re.sub(r"//.*", "", code)
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)

    open_braces = cleaned.count("{")
    close_braces = cleaned.count("}")
    assert open_braces == close_braces, f"Mismatched braces: {open_braces} open vs {close_braces} close"
    assert open_braces > 0, "No braces found in JavaScript file"


def test_full_application_workflow_deliverable():
    """End-to-end verification of baseline seeding, investigation, and learning loop."""
    # 1. Health check
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    health_data = res_health.json()
    assert health_data["status"] == "ok"
    assert "hindsight" in health_data

    # 2. Seed baseline
    res_seed = client.post("/api/seed")
    assert res_seed.status_code == 200
    assert res_seed.json()["status"] == "success"

    # 3. Investigate checkout-api (matches baseline INC-2026-0417)
    res_inv_a = client.post(
        "/api/investigate",
        json={
            "title": "Database connection pool saturated on checkout-api",
            "service": "checkout-api",
            "severity": "SEV-1",
            "description": "Payment timeouts and connection pool exhausted under normal traffic.",
            "log_excerpt": "Connection acquisition timeout after 30000ms",
        },
    )
    assert res_inv_a.status_code == 200
    inv_a_data = res_inv_a.json()
    assert len(inv_a_data["memory_evidence"]) >= 1
    assert "INC-2026-0417" in inv_a_data["relevant_past_incidents"][0]
    assert len(inv_a_data["recommended_diagnostic_checks"]) > 0

    # 4. Investigate unseen worker service -> 0 memories
    res_inv_b = client.post(
        "/api/investigate",
        json={
            "title": "Email dispatch buffer backlog on mail-worker",
            "service": "mail-worker",
            "severity": "SEV-2",
            "description": "Outbound message buffer increasing; SMTP provider throttling.",
        },
    )
    assert res_inv_b.status_code == 200
    inv_b_data = res_inv_b.json()
    assert len(inv_b_data["memory_evidence"]) == 0

    # 5. Record verified outcome for mail-worker
    res_outcome = client.post(
        "/api/outcomes",
        json={
            "service": "mail-worker",
            "confirmed_root_cause": "SMTP provider quota exceeded due to duplicate transaction notification loop.",
            "resolution_fix": "Patched notification deduplication cache and enabled exponential backoff rate limiter.",
            "verification_status": "VERIFIED",
            "notes": "Queue cleared within 4 minutes after deploying deduplicator.",
        },
    )
    assert res_outcome.status_code == 200

    # 6. Re-investigate mail-worker -> persistent memory recalled!
    res_inv_b2 = client.post(
        "/api/investigate",
        json={
            "title": "Outbound message delay on mail-worker",
            "service": "mail-worker",
            "severity": "SEV-2",
            "description": "Delivery latency spike on mail-worker queue.",
        },
    )
    assert res_inv_b2.status_code == 200
    inv_b2_data = res_inv_b2.json()
    assert "mail-worker" in inv_b2_data["memory_evidence"][0]["service"].lower() or "mail-worker" in inv_b2_data["memory_evidence"][0]["title"].lower()
