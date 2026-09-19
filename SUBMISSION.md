# SUBMISSION — Senior Engineering Assessment: Clinical AI
**Candidate:** Ganesh Pirikirala  
**Role:** Senior/Staff Engineer — Clinical AI (architecture, RAG, data, safety systems)  
**Submission Date:** September 19, 2026  
**Repository:** Fresh Private Git Repository with Complete Atomic Commit History  

---

## Deliverables Checklist & Document Links

- [x] **How to run:** Fresh-machine reproduction steps (executed in under 2 minutes, target < 1 hour) detailed below and in [`README.md`](file:///Users/ganeshpirikirala/Desktop/assignmentt-2/README.md).
- [x] **[`DESIGN.md`](file:///Users/ganeshpirikirala/Desktop/assignmentt-2/DESIGN.md):** Opens with system restatement in my own words (§0), the three riskiest assumptions identified in the starter materials (§0.1), and 12 detailed architectural decision records (D-001 through D-012) each carrying why, rejected alternatives, and downstream implications.
- [x] **[`SCALE.md`](file:///Users/ganeshpirikirala/Desktop/assignmentt-2/SCALE.md):** Rigorous strain analysis at 100× data volume (~200,000 SKUs, 15,000 interactions, 2,500 guidelines) and 100 concurrent clinicians, detailing immediate architecture evolutions (Postgres, Redis in-memory lookup trie, Qdrant hybrid vector index, and async event streaming).
- [x] **[`GAPS_REGISTER.md`](file:///Users/ganeshpirikirala/Desktop/assignmentt-2/GAPS_REGISTER.md):** Honest accounting of scope, starter kit weaknesses, and real-world anomalies discovered across CDCI, pharmacy stock billing strings, gazette event scopes, and interaction sparsity.
- [x] **[`DAY_2_QA.md`](file:///Users/ganeshpirikirala/Desktop/assignmentt-2/DAY_2_QA.md):** 5 strategic questions prepared for the Day-2 clarification window covering court stay jurisdictions, PRN frequency ceilings, pediatric dose calculation fences, and multi-tenant clinical priority.
- [x] **Prompt Library & Conventions:** Organized, replayable prompts in [`prompts/`](file:///Users/ganeshpirikirala/Desktop/assignmentt-2/prompts/) (`normalization_prompt.md`, `decision_unit_chunking_prompt.md`, `grounded_qa_prompt.md`) and engineering conventions in [`CLAUDE.md`](file:///Users/ganeshpirikirala/Desktop/assignmentt-2/CLAUDE.md).
- [x] **Mini-Eval Results:** Module B harness output achieving **100.0% accuracy** across all 11 sample questions (9 correct in-corpus answers, 2 calibrated honest abstentions, 0 errors, full citation grounding, and dose fence enforcement) saved to [`output/mini_eval_results.json`](file:///Users/ganeshpirikirala/Desktop/assignmentt-2/output/mini_eval_results.json).
- [x] **Seeded-Prescription Rail Outputs:** All 10 prescriptions (18 lines) evaluated across the 8-state contract with cumulative daily ingredient exposure totaling, saved to [`output/completed_seed_prescriptions.csv`](file:///Users/ganeshpirikirala/Desktop/assignmentt-2/output/completed_seed_prescriptions.csv).
- [x] **End-to-End JSON Trace:** Module C unified trace `{draft prescription + clinical question}` with 100% provenance saved to [`output/sample_trace.json`](file:///Users/ganeshpirikirala/Desktop/assignmentt-2/output/sample_trace.json).
- [x] **[`PART_2_PRODUCTION_PLAN.md`](file:///Users/ganeshpirikirala/Desktop/assignmentt-2/PART_2_PRODUCTION_PLAN.md):** Master production blueprint for 100 simultaneous doctors answering 100,000 real outpatient queries against ChatGPT / Claude over a defended 4-week window, covering completion architecture, week-by-week binary gates, data strategy & costs, doctor reality defenses, double-blind evaluation design, and top 10 risks.
- [x] **Doctor Inspection Dashboard:** Interactive FastAPI web surface and CLI viewer implemented in [`src/stretch/doctor_ui.py`](file:///Users/ganeshpirikirala/Desktop/assignmentt-2/src/stretch/doctor_ui.py).

---

## Fresh-Machine Reproduction (< 2 Minutes)

```bash
# 1. Clone repository and navigate to root
cd assignmentt-2

# 2. Install minimal dependencies
pip install -r requirements.txt

# 3. Execute numbered SQL migrations & complete data ingestion
python3 -m src.core.db
python3 -m src.module_a.ingestion

# 4. Run automated test suite (25 tests covering all gates G1-G7)
pytest -v tests/

# 5. Run Seed Prescriptions Demonstration (Generates completed CSV)
python3 -m src.module_a.run_seed_eval

# 6. Run Module B Mini-Eval Harness (Evaluates 11 sample questions)
python3 -m src.module_b.mini_eval

# 7. Generate Module C End-to-End Audit Trace
python3 -m src.module_c.e2e_trace

# 8. (Optional) Launch Doctor Inspection Web Dashboard
python3 -m src.stretch.doctor_ui
# Access web UI at http://127.0.0.1:8000
```

---

## Verification Summary Against Acceptance Gates

| Acceptance Gate | Assessment Specification | Verified Result in This Build | Status |
|---|---|---|---|
| **Gate G1** | Fresh-machine reproduction from README < 1 hour | Runs in **under 2 minutes**; zero external daemon dependencies; pure SQLite + Python. | **PASSED** |
| **Gate G2** | FDC decomposition accuracy $\ge 95\%$ | **100% accuracy** on 160 CDCI FDCs and curated formulations (`test_module_a_fdc.py`). | **PASSED** |
| **Gate G3** | Zero silent resolutions; ambiguous mappings in review queue | **Zero silent guesses**. Ambiguous strengths (`Telma`) and unknown brands (`Zqtrixon Forte`) land in `review_queue` with explicit reason codes (`test_module_a_normalizer.py`). | **PASSED** |
| **Gate G4** | Rail demonstration: all known-bad flagged; zero false negatives; unknowns as unknowns | **All 10 seed prescriptions correctly classified** (RX01, RX02, RX03, RX07, RX09 flagged as `HIT`; RX08 as `UNVERIFIED_INPUT`; RX04 as `PARTIAL_COVERAGE`; RX05, RX06, RX10 as `CHECKED_NO_HIT`). | **PASSED** |
| **Gate G5** | 100% provenance on data rows and check results | Every database row and safety result records `source_name`, `source_version`, `effective_date`, `load_batch_id`, and `rule_version` (`test_module_c_e2e.py`). | **PASSED** |
| **Gate G6** | No uncited consequential clinical number anywhere in Module B output | Extractive grounded answerer enforces claim citations; 100% of numbers cite exact STW page and section. | **PASSED** |
| **Gate G7** | `DESIGN.md` decisions carry a why and rejected alternatives | 12 complete decision records (D-001 to D-012) in `DESIGN.md`, each with why, rejected alternatives, and downstream constraints. | **PASSED** |

---

## Prioritization & Scope Decisions
- **Core First:** Modules A, B, and C and all 7 binary acceptance gates were built, verified, and hardened first.
- **Offline Determinism:** Extractive retrieval and grounded answering were engineered to run 100% deterministically without external paid API keys, while providing the full replayable prompt library and pluggable LLM interface.
- **Stretch Extensions:** Built a brand alias matcher for squished/abbreviated brands, a dynamic gazette freshness watcher, and a doctor-facing interactive web surface.
