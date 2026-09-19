# CLAUDE.md — Engineering Conventions & Rules for BRAHMO Clinical AI

This document establishes the architecture standards, coding conventions, and operational workflows for the BRAHMO Clinical AI codebase.

---

## 1. Non-Negotiable Architecture Principles

1. **Law 4: Safety Outside the LLM**
   - Medication safety checks (duplicate salts, prohibited FDCs, severe interactions, cumulative dosage) are **pure lookup and deterministic rule logic**.
   - NEVER place an LLM or probabilistic call anywhere in the safety rail path.

2. **Law 5: Strict 8-State Vocabulary**
   - Safety checks must return exactly one of: `HIT · CHECKED_NO_HIT · PARTIAL_COVERAGE · UNVERIFIED_INPUT · NOT_CHECKED · DATA_EXPIRED · SOURCE_CONFLICT · SERVICE_UNAVAILABLE`.
   - Missing data must NEVER render as "safe."

3. **Law 6 & Gate G3: Zero Silent Ambiguity**
   - Uncertain brands, missing strengths with multiple variants, or unrecognized products must NEVER be silently auto-resolved.
   - All ambiguous inputs must be routed to `review_queue` with explicit reason codes (`AMBIGUOUS_STRENGTH_MULTIPLE_MATCHES`, `UNRECOGNIZED_BRAND`, etc.).

4. **Law 7: Event-Sourced Regulatory Truth**
   - Regulatory legality derives from effective-dated gazette events with supersession tracking.
   - Plain `banned = true/false` booleans are prohibited. Every check output must cite the notification ID and effective date.

5. **Law 12: Absolute Fences**
   - Deliberately do NOT implement: patient-specific dose calculation (including pediatric mg/kg), diagnostic ranking, triage scoring, or autonomous treatment plans.
   - Verbatim clinical dosing formulas are retrieved and cited as written; patient dose calculations are strictly refused.

6. **No Hardcoded Constants**
   - All thresholds, source versions, and paths must load from `src/core/config.py`.

---

## 2. Directory Layout & Module Responsibilities

- `migrations/`: Numbered SQL schema migrations (`001_...` to `004_...`).
- `src/core/`: Application config (`config.py`), database manager (`db.py`), and Pydantic types (`types.py`).
- `src/module_a/`: Drug master ingestion, normalizer, FDC decomposition, event-sourced regulatory engine, deterministic safety rail, and seed eval runner.
- `src/module_b/`: Clinical decision-unit chunking, hybrid retrieval, query routing, grounded answering, and mini-eval harness.
- `src/module_c/`: End-to-end trace executor (`e2e_trace.py`).
- `src/stretch/`: Brand alias matcher, regulatory freshness watcher, and doctor dashboard (`doctor_ui.py`).
- `tests/`: Pytest test suite covering all modules, constraints, and acceptance gates.
- `prompts/`: Replayable prompt templates for AI-assisted development and clinical RAG.
- `output/`: Generated evaluation reports (`mini_eval_results.json`, `completed_seed_prescriptions.csv`, `sample_trace.json`).

---

## 3. Developer Workflows & Commands

### Running Migrations & Ingestion:
```bash
python3 -m src.core.db            # Applies numbered SQL migrations
python3 -m src.module_a.ingestion # Ingests CDCI, stock, NLEM, Jan Aushadhi, gazette, interactions
```

### Running Test Suite:
```bash
python3 -m pytest -v tests/
```

### Running Seed Prescription Benchmark:
```bash
python3 -m src.module_a.run_seed_eval
```

### Running Mini-Eval Harness (11 Sample Questions):
```bash
python3 -m src.module_b.mini_eval
```

### Generating End-to-End JSON Trace:
```bash
python3 -m src.module_c.e2e_trace
```

### Starting Doctor Inspection Web Surface:
```bash
python3 -m src.stretch.doctor_ui  # Serves dashboard on http://127.0.0.1:8000
```
