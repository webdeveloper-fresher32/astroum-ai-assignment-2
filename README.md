# BRAHMO Clinical AI — Senior Engineering Assessment

> **A Patient-Safe Clinical AI for Indian Outpatient Practice**  
> Grounded in Indian medical evidence with claim citations, protected by deterministic medication-safety checks that never guess.

---

## 1. Quickstart & Reproduction (< 2 Minutes)

This project has zero heavyweight external service dependencies (no external Docker or PostgreSQL setup required for evaluation). It runs on standard Python 3.10+ with SQLite in WAL mode.

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Run Numbered Migrations & Complete Data Ingestion
```bash
python3 -m src.core.db
python3 -m src.module_a.ingestion
```
*Applies SQL migrations `001` through `004` and ingests the CDCI drug catalog, pharmacy stock, NLEM, Jan Aushadhi, gazette events, and severe interactions.*

### Step 3: Run Automated Test Suite (25 Tests)
```bash
python3 -m pytest -v tests/
```
*Validates FDC decomposition accuracy ($\ge 95\%$), zero silent resolutions, event-sourced regulatory supersession, 8-state safety rail contract, grounded citations, dose fences, and end-to-end trace provenance.*

### Step 4: Run Seed Prescriptions Demonstration (10 Prescriptions)
```bash
python3 -m src.module_a.run_seed_eval
```
*Outputs evaluation to console and writes `output/completed_seed_prescriptions.csv`.*

### Step 5: Run Module B Mini-Evaluation Harness (11 Sample Questions)
```bash
python3 -m src.module_b.mini_eval
```
*Benchmarks the 11 clinical questions, validating 100% accuracy, claim citations, dose calculation refusal, and honest abstentions. Writes report to `output/mini_eval_results.json`.*

### Step 6: Generate Module C End-to-End JSON Trace
```bash
python3 -m src.module_c.e2e_trace
```
*Executes full `{draft prescription + clinical question}` trace and writes `output/sample_trace.json`.*

### Step 7: Launch Doctor Inspection Web Dashboard (Optional Stretch)
```bash
python3 -m src.stretch.doctor_ui
```
*Open http://127.0.0.1:8000 in your browser to interact with the real-time prescription safety checker, cumulative dosage meters, and grounded Q&A citation viewer.*

---

## 2. Core Architecture & Modules

1. **Module A — Drug Master & Deterministic Safety Rail:**
   - Schema with numbered SQL migrations (`migrations/001_...` to `004_...`).
   - Normalization with confidence scores, method tags, and non-silent Review Queue (`review_queue`).
   - FDC decomposition engine decomposing >160 products into active salts + strengths.
   - Event-sourced regulatory resolver tracking gazette orders, High Court stays, and supersession chains.
   - Deterministic safety rail implementing the strict 8-state contract (`HIT`, `CHECKED_NO_HIT`, `PARTIAL_COVERAGE`, `UNVERIFIED_INPUT`, etc.) and cumulative same-ingredient daily exposure totaling.

2. **Module B — Grounded Clinical Q&A Slice (Mini-RAG):**
   - Clinical decision-unit chunking for 13 ICMR STW PDFs + Sunrise Clinic SOP.
   - Hybrid retrieval (BM25 + condition keyword boosting + metadata filtering).
   - Grounded answering with claim-level citations (`[STW-PED-01 v2024.1: FIRST-LINE MANAGEMENT, p.1]`).
   - Mandatory dose calculation refusal (Law 12) for pediatric weight-based formulas.
   - Supersession disclosure (Hypertension 2021 vs 2025 editions).
   - Honest, calibrated abstentions on out-of-corpus queries (Migraine, Tuberculosis).
   - Local clinic protocol labeling (`SUNRISE-SOP-CLIN-014`) with national divergence highlighting.

3. **Module C — Unified End-to-End Trace:**
   - Single JSON audit trace capturing normalization, safety checks, grounded QA, and 100% provenance (`output/sample_trace.json`).

4. **Stretch Capabilities:**
   - Colloquial / phonetic brand alias matcher (`src/stretch/alias_matcher.py`).
   - Dynamic regulatory freshness watcher (`src/stretch/freshness_watcher.py`).
   - Interactive doctor inspection dashboard & API server (`src/stretch/doctor_ui.py`).

---

## 3. Project Documentation Index

- [`SUBMISSION.md`](file:///Users/ganeshpirikirala/Desktop/assignmentt-2/SUBMISSION.md) — Master submission checklist and acceptance gates verification.
- [`DESIGN.md`](file:///Users/ganeshpirikirala/Desktop/assignmentt-2/DESIGN.md) — System restatement, 3 riskiest assumptions, and decision ledger D-001 through D-012.
- [`PART_2_PRODUCTION_PLAN.md`](file:///Users/ganeshpirikirala/Desktop/assignmentt-2/PART_2_PRODUCTION_PLAN.md) — 4-week architectural roadmap for 100 simultaneous doctors answering 100,000 queries vs ChatGPT/Claude.
- [`SCALE.md`](file:///Users/ganeshpirikirala/Desktop/assignmentt-2/SCALE.md) — Strain analysis at 100× data volume and 100 concurrent users.
- [`GAPS_REGISTER.md`](file:///Users/ganeshpirikirala/Desktop/assignmentt-2/GAPS_REGISTER.md) — Honest accounting of scope, starter kit weaknesses, and real-world data anomalies.
- [`DAY_2_QA.md`](file:///Users/ganeshpirikirala/Desktop/assignmentt-2/DAY_2_QA.md) — Clarification questions submitted for Day 2.
- [`CLAUDE.md`](file:///Users/ganeshpirikirala/Desktop/assignmentt-2/CLAUDE.md) — Engineering standards and developer conventions.
- [`prompts/`](file:///Users/ganeshpirikirala/Desktop/assignmentt-2/prompts/) — Replayable prompt library for normalization, chunking, and grounded answering.
