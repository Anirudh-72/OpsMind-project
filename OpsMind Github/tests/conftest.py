"""Pytest shared fixtures and test isolation."""

import pytest
from app.services.hindsight_service import hindsight_service


@pytest.fixture(autouse=True)
def reset_memory_bank_state():
    """Ensure each test runs with clean baseline historical memory."""
    hindsight_service.reset_to_baseline()
    yield
    hindsight_service.reset_to_baseline()
