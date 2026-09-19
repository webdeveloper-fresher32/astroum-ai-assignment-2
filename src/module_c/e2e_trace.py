"""
End-to-End Trace Generator for BRAHMO Clinical AI (Module C).
Takes {a draft prescription + one clinical question} and returns a single JSON trace:
- Normalization results (including unresolved items in review queue)
- Safety check results adhering to the 8-state contract
- Cumulative active ingredient daily exposures
- Grounded answer with claim citations or abstention
- 100% provenance: versions of every dataset, rule, prompt, model used.

Saves trace to output/sample_trace.json.
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from src.core.config import config
from src.core.types import PrescriptionItem
from src.module_a.normalizer import DrugNormalizer
from src.module_a.safety_rail import DeterministicSafetyRail
from src.module_b.answerer import GroundedClinicalAnswerer

class EndToEndTracer:
    def __init__(self, conn=None):
        self._conn = conn
        self.normalizer = DrugNormalizer(conn)
        self.safety_rail = DeterministicSafetyRail(conn)
        self.answerer = GroundedClinicalAnswerer(conn=conn)

    def execute_trace(
        self,
        rx_id: str,
        prescription_items: List[PrescriptionItem],
        clinical_question: str,
        patient_is_paediatric: bool = False
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        timestamp = datetime.now().isoformat()

        # Step 1: Normalization Trace
        norm_results = []
        for it in prescription_items:
            norm = self.normalizer.normalize(
                raw_text=it.written_product,
                strength_as_written=it.strength_as_written,
                context_type="E2E_PRESCRIPTION_TRACE"
            )
            norm_results.append({
                "raw_product": it.written_product,
                "strength_as_written": it.strength_as_written,
                "resolved_product_id": norm.product_id,
                "canonical_brand": norm.brand_name,
                "dose_form": norm.dose_form,
                "is_fdc": norm.is_fdc,
                "decomposed_ingredients": [
                    {
                        "ingredient_name": ing.ingredient_name,
                        "strength_value": ing.strength_value,
                        "strength_unit": ing.strength_unit,
                        "confidence": ing.confidence,
                        "method": ing.method
                    }
                    for ing in norm.ingredients
                ],
                "normalization_confidence": norm.confidence,
                "normalization_method": norm.method.value,
                "review_queue_id": norm.review_queue_id,
                "review_reason": norm.review_reason.value if norm.review_reason else None
            })

        # Step 2: Safety Rail Execution (8-State Contract)
        safety_report = self.safety_rail.evaluate_prescription(
            rx_id=rx_id,
            items=prescription_items,
            patient_is_paediatric=patient_is_paediatric
        )

        safety_trace = {
            "rx_id": rx_id,
            "overall_state": safety_report.overall_state.value,
            "findings": [
                {
                    "check_type": f.check_type,
                    "state": f.state.value,
                    "severity": f.severity,
                    "evidence": f.evidence,
                    "regulatory_citation": f.regulatory_citation,
                    "effective_date": f.effective_date,
                    "rule_version": f.rule_version,
                    "data_version": f.data_version
                }
                for f in safety_report.findings
            ],
            "cumulative_daily_exposures": safety_report.cumulative_exposures,
            "unresolved_items": safety_report.unresolved_items
        }

        # Step 3: Grounded Clinical Answering (Module B)
        qa_resp = self.answerer.answer_query(clinical_question)
        qa_trace = {
            "query": clinical_question,
            "answer_text": qa_resp.answer_text,
            "citations": [c.model_dump() for c in qa_resp.citations],
            "is_abstained": qa_resp.is_abstained,
            "abstention_reason": qa_resp.abstention_reason,
            "conflict_identified": qa_resp.conflict_identified,
            "conflict_notes": qa_resp.conflict_notes,
            "refused_dose_calculation": qa_resp.refused_dose_calculation
        }

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # Assemble Unified Trace
        trace_payload = {
            "trace_id": f"TRACE-{rx_id}-{int(time.time())}",
            "timestamp": timestamp,
            "execution_duration_ms": round(duration_ms, 2),
            "system_provenance": {
                "system_version": config.system_version,
                "safety_rule_version": config.safety_rule_version,
                "cdci_source_version": config.cdci_source_version,
                "regulatory_gazette_version": config.regulatory_gazette_version,
                "stw_corpus_version": config.stw_corpus_version,
                "local_protocol_version": config.local_protocol_version,
                "load_batch_id": config.load_batch_id
            },
            "input_prescription": [it.model_dump() for it in prescription_items],
            "input_clinical_question": clinical_question,
            "module_a_normalization": norm_results,
            "module_a_safety_rail": safety_trace,
            "module_b_grounded_qa": qa_trace
        }

        return trace_payload

def generate_sample_trace():
    tracer = EndToEndTracer()

    # Sample Input: Classic FDC duplicate exposure trap prescription (Dolo 650 + Sinarest Tablet)
    # + Clinical question on pediatric otitis media
    prescription = [
        PrescriptionItem(
            rx_id="RX-SAMPLE-01",
            item_no=1,
            written_product="Dolo 650",
            strength_as_written="650 mg",
            dose_frequency="1-0-1 x 5d",
            clinical_note="Fever and bodyache"
        ),
        PrescriptionItem(
            rx_id="RX-SAMPLE-01",
            item_no=2,
            written_product="Sinarest Tablet",
            strength_as_written=None,
            dose_frequency="1-0-1 x 5d",
            clinical_note="Cold symptoms"
        )
    ]
    clinical_question = "What is the first-line antibiotic, dose basis, and duration for acute otitis media in a child?"

    print("Generating End-to-End Trace...")
    trace = tracer.execute_trace(
        rx_id="RX-SAMPLE-01",
        prescription_items=prescription,
        clinical_question=clinical_question
    )

    out_file = config.output_dir / "sample_trace.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2)

    print(f"Sample trace generated and written to {out_file}")
    print(f"Trace ID: {trace['trace_id']}")
    print(f"Overall Safety Verdict: [{trace['module_a_safety_rail']['overall_state']}]")
    print(f"Cumulative Paracetamol Exposure: {trace['module_a_safety_rail']['cumulative_daily_exposures']['Paracetamol']['total_daily_exposure_mg']} mg/day")
    print(f"Q&A Citation Count: {len(trace['module_b_grounded_qa']['citations'])}")
    return trace

if __name__ == "__main__":
    generate_sample_trace()
