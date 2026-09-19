"""
Tests for Module C: End-to-End Trace Execution.
Fulfills Gate G5: 100% provenance on data rows and check results.
"""

import pytest
from src.core.types import PrescriptionItem
from src.module_c.e2e_trace import EndToEndTracer

def test_end_to_end_trace_schema_and_provenance():
    tracer = EndToEndTracer()
    prescription = [
        PrescriptionItem(rx_id="RX-TEST-01", item_no=1, written_product="Dolo 650", strength_as_written="650 mg", dose_frequency="1-0-1"),
        PrescriptionItem(rx_id="RX-TEST-01", item_no=2, written_product="Sinarest Tablet", strength_as_written=None, dose_frequency="1-0-1")
    ]
    question = "Which analgesic class must be avoided in suspected dengue, and why?"

    trace = tracer.execute_trace("RX-TEST-01", prescription, question)

    # 1. Structural Checks
    assert "trace_id" in trace
    assert "timestamp" in trace
    assert "execution_duration_ms" in trace
    assert "system_provenance" in trace
    assert "module_a_normalization" in trace
    assert "module_a_safety_rail" in trace
    assert "module_b_grounded_qa" in trace

    # 2. Provenance Validation (Gate G5)
    prov = trace["system_provenance"]
    assert "system_version" in prov
    assert "safety_rule_version" in prov
    assert "cdci_source_version" in prov
    assert "regulatory_gazette_version" in prov
    assert "stw_corpus_version" in prov
    assert "local_protocol_version" in prov
    assert "load_batch_id" in prov

    # 3. Safety Rail Output
    safety = trace["module_a_safety_rail"]
    assert safety["overall_state"] == "HIT"
    assert "Paracetamol" in safety["cumulative_daily_exposures"]
    assert safety["cumulative_daily_exposures"]["Paracetamol"]["total_daily_exposure_mg"] == 2300.0

    # 4. Grounded Q&A Output
    qa = trace["module_b_grounded_qa"]
    assert len(qa["citations"]) > 0
    assert any("STW-GP-04" in c["source_document"] for c in qa["citations"])
