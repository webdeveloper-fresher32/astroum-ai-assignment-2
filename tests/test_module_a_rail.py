"""
Tests for Module A: Deterministic Medication Safety Rail.
Fulfills Gate G4: All known-bad seeded prescriptions flagged; zero false negatives; unknowns rendered as unknowns.
"""

import pytest
from src.core.types import PrescriptionItem, SafetyVerdictState
from src.module_a.safety_rail import DeterministicSafetyRail

@pytest.fixture
def rail():
    return DeterministicSafetyRail()

def test_rx01_duplicate_paracetamol_fdc_cumulative(rail):
    items = [
        PrescriptionItem(rx_id="RX01", item_no=1, written_product="Dolo 650", strength_as_written="650 mg", dose_frequency="1-0-1 x 5d"),
        PrescriptionItem(rx_id="RX01", item_no=2, written_product="Sinarest Tablet", strength_as_written=None, dose_frequency="1-0-1 x 5d")
    ]
    report = rail.evaluate_prescription("RX01", items)
    assert report.overall_state == SafetyVerdictState.HIT
    assert any(f.check_type == "DUPLICATE_ACTIVE_INGREDIENT" for f in report.findings)
    # Check cumulative exposure
    paracetamol_exp = report.cumulative_exposures.get("Paracetamol")
    assert paracetamol_exp is not None
    assert paracetamol_exp["total_daily_exposure_mg"] == 2300.0 # (650*2) + (500*2)

def test_rx02_prohibited_fdc(rail):
    items = [
        PrescriptionItem(rx_id="RX02", item_no=1, written_product="NimuPar-P", dose_frequency="1-0-1 x 3d")
    ]
    report = rail.evaluate_prescription("RX02", items)
    assert report.overall_state == SafetyVerdictState.HIT
    assert any(f.check_type == "PROHIBITED_RESTRICTED_FDC" for f in report.findings)
    finding = next(f for f in report.findings if f.check_type == "PROHIBITED_RESTRICTED_FDC")
    assert "GSR 411(E)" in finding.evidence

def test_rx03_severe_interaction(rail):
    items = [
        PrescriptionItem(rx_id="RX03", item_no=1, written_product="Warf 5", strength_as_written="5 mg", dose_frequency="0-0-1"),
        PrescriptionItem(rx_id="RX03", item_no=2, written_product="Azee 500", strength_as_written="500 mg", dose_frequency="1-0-0 x 3d")
    ]
    report = rail.evaluate_prescription("RX03", items)
    assert report.overall_state == SafetyVerdictState.HIT
    assert any(f.check_type == "SEVERE_INTERACTION" for f in report.findings)
    finding = next(f for f in report.findings if f.check_type == "SEVERE_INTERACTION")
    assert "bleeding" in finding.evidence.lower()

def test_rx04_ambiguous_strength_partial_coverage(rail):
    items = [
        PrescriptionItem(rx_id="RX04", item_no=1, written_product="Telma", dose_frequency="1-0-0")
    ]
    report = rail.evaluate_prescription("RX04", items)
    assert report.overall_state == SafetyVerdictState.PARTIAL_COVERAGE
    assert "Telma" in report.unresolved_items

def test_rx05_clean_pass(rail):
    items = [
        PrescriptionItem(rx_id="RX05", item_no=1, written_product="Glycomet 500", strength_as_written="500 mg", dose_frequency="1-0-1"),
        PrescriptionItem(rx_id="RX05", item_no=2, written_product="Atorva 10", strength_as_written="10 mg", dose_frequency="0-0-1")
    ]
    report = rail.evaluate_prescription("RX05", items)
    assert report.overall_state == SafetyVerdictState.CHECKED_NO_HIT

def test_rx08_unverified_input(rail):
    items = [
        PrescriptionItem(rx_id="RX08", item_no=1, written_product="Zqtrixon Forte", dose_frequency="1-0-1")
    ]
    report = rail.evaluate_prescription("RX08", items)
    assert report.overall_state == SafetyVerdictState.UNVERIFIED_INPUT
    assert "Zqtrixon Forte" in report.unresolved_items

def test_rx09_fdc_hidden_duplicate_salt(rail):
    items = [
        PrescriptionItem(rx_id="RX09", item_no=1, written_product="Telma-H 40", dose_frequency="1-0-0"),
        PrescriptionItem(rx_id="RX09", item_no=2, written_product="Telma 40", strength_as_written="40 mg", dose_frequency="0-0-1")
    ]
    report = rail.evaluate_prescription("RX09", items)
    assert report.overall_state == SafetyVerdictState.HIT
    telmisartan_exp = report.cumulative_exposures.get("Telmisartan")
    assert telmisartan_exp is not None
    assert telmisartan_exp["total_daily_exposure_mg"] == 80.0
