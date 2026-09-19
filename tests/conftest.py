"""
Pytest configuration and shared fixtures for BRAHMO Clinical AI test suite.
"""

import pytest
from src.core.db import get_connection, run_migrations
from src.module_a.ingestion import IngestionPipeline

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Ensure database migrations and initial ingestions are complete."""
    run_migrations()
    pipeline = IngestionPipeline()
    pipeline.run_all()
    yield
