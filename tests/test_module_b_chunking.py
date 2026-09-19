"""
Tests for Module B: Clinical Decision-Unit Chunking.
Validates that documents are chunked into clinically meaningful units rather than token slices.
"""

import pytest
from src.module_b.chunker import ClinicalChunker

def test_decision_unit_extraction():
    units = ClinicalChunker.load_entire_corpus()
    assert len(units) >= 40

    # Verify required STW codes exist
    codes = {u.document_code for u in units}
    expected_codes = {
        "STW-GP-01", "STW-GP-02", "STW-GP-03", "STW-GP-04",
        "STW-GYN-01", "STW-GYN-02", "STW-GYN-03",
        "STW-ORT-01", "STW-ORT-02",
        "STW-PED-01", "STW-PED-02", "STW-PED-03",
        "SUNRISE-SOP-CLIN-014"
    }
    for ec in expected_codes:
        assert ec in codes, f"Missing document code: {ec}"

def test_superseded_metadata_flag():
    units = ClinicalChunker.load_entire_corpus()
    v2021_units = [u for u in units if u.document_code == "STW-GP-02" and u.version == "2021.1"]
    assert len(v2021_units) > 0
    assert all(u.is_superseded for u in v2021_units)

    v2025_units = [u for u in units if u.document_code == "STW-GP-02" and u.version == "2025.2"]
    assert len(v2025_units) > 0
    assert all(not u.is_superseded for u in v2025_units)

def test_local_clinic_protocol_metadata():
    units = ClinicalChunker.load_entire_corpus()
    clinic_units = [u for u in units if u.document_code == "SUNRISE-SOP-CLIN-014"]
    assert len(clinic_units) >= 4
    assert all(u.is_clinic_internal for u in clinic_units)
