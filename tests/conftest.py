"""
Pytest configuration and shared fixtures for BRAHMO Clinical AI test suite.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path for bare 'pytest' executions
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
