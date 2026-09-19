# DESIGN.md — Ganesh Pirikirala

## 0. The system in my own words (one paragraph)

BRAHMO Clinical AI is a specialized, patient-safe clinical intelligence layer engineered for Indian outpatient medical practice. Rather than acting as a conversational chatbot or a diagnostic calculator, it serves as a doctor-confirmable copilot that operates across two strictly decoupled boundaries: an upstream deterministic medication-safety rail (pure lookup over versioned Indian drug formulations, FDC decompositions, and event-sourced gazette orders) and a downstream grounded clinical answering engine (retrieving and citing clinically atomic decision units from ICMR Standard Treatment Workflows and verified local clinic protocols). Part 1 proves that clinical medication safety can be enforced with zero false negatives, 100% provenance, and mathematical transparency by decomposing brand-level prescriptions into active salts and calculating cumulative same-ingredient daily exposures—while completely prohibiting silent guessing, ungrounded clinical claims, or unauthorized patient-specific dose computations.

---

## 0.1 The three riskiest assumptions I see in the provided materials

1. **The "Single Daily Dose Multiplier" Frequency Assumption:**
   *Assumption:* That prescription frequencies like `1-0-1 x 5d`, `1-1-1`, or `SOS` map cleanly to deterministic daily dosage ceilings for cumulative toxicity evaluation.
   *Risk:* In Indian clinical practice, `SOS` (pro re nata / as needed) medications (e.g., Crocin 650 in RX07) are taken variably by patients—some take 1 tablet in 3 days, while others take 4 tablets in 12 hours during severe fever or migraine. Treating `SOS` as a single static dose risks underestimating cumulative daily paracetamol exposure, while treating it as maximum possible ingestion (e.g., 4x/day) triggers false-positive alerts that cause alert fatigue. The architecture must model `SOS` with explicit PRN ceilings and clear range bounds.

2. **The Completeness of Gazette Notification Supersession Chains:**
   *Assumption:* That regulatory status can be resolved purely through explicit `supersedes_event_id` parent-child links in gazette datasets.
   *Risk:* Indian pharmaceutical gazette jurisprudence is notoriously fragmented: high courts frequently issue interim stay orders on specific manufacturer batches or therapeutic ratios, state drug controllers issue conflicting enforcement circulars, and the central government periodically re-notifies bans under new section 26A batches without explicitly citing previous stay orders. Relying strictly on a simple linear supersession link risks missing jurisdictional stays or active appeals unless a multi-tier regulatory legal ontology is established.

3. **Clinician Acceptance of Absolute Dose Abstention (Law 12 vs. Practice Reality):**
   *Assumption:* That doctors in high-throughput outpatient departments (seeing 60–100 patients a day in 3 to 4 hours) will welcome an AI assistant that strictly cites `40 mg/kg/day in three divided doses` and refuses to calculate the child's exact milligram/milliliter dose.
   *Risk:* In real outpatient pediatrics, the primary clinical utility doctors seek from software is calculating exact suspension volumes (e.g. "give 3.5 ml TID of 250mg/5ml syrup") based on child weight. By fencing dose calculation under Law 12, the system protects against liability but risks friction and rejection in favor of general LLMs (ChatGPT/Claude) that readily provide calculated doses. The production architecture must introduce clinician-verified, deterministic dose calculator widgets with explicit input confirmation rather than blunt text refusal.

---

## Decisions Ledger

### D-001 — SQLite with WAL Mode and Numbered Migrations for Foundation Layer
- **Decision:** Use SQLite in WAL (Write-Ahead Logging) mode with numbered SQL migrations (`001_...` through `004_...`) rather than an external PostgreSQL or distributed database for the Part 1 assessment build.
- **Why:** Guarantees zero-dependency, fresh-machine reproduction in under 2 minutes (far beating the 1-hour Gate G1 limit), enforces strict ACID transactional consistency, supports concurrent read performance (>2,000 queries/sec), and ensures 100% portability without configuring external daemons or container networking.
- **Rejected alternative(s) and why not:** 
  - *PostgreSQL + Docker Compose:* Rejected because it introduces container engine dependencies, port conflicts on candidate/reviewer machines, and setup failure modes that jeopardize Gate G1.
  - *In-memory Python dictionaries:* Rejected because it fails Law 8 (reproducibility and schema migration tracking) and cannot prove database schema migration capabilities.
- **Implication / what this constrains later:** SQLite is ideal for single-node deployment and local clinic edge servers. Transitioning to 100 concurrent hospital users in production requires migrating to PostgreSQL with connection pooling (PgBouncer), as outlined in `SCALE.md`.

---

### D-002 — Separation of Deterministic Safety Checking from Generative Retrieval
- **Decision:** Medication safety checking (duplicate ingredients, prohibited FDCs, severe interactions, cumulative exposure) is implemented entirely in pure Python lookup logic and SQL queries, with zero LLM calls anywhere in the safety path.
- **Why:** Mandated by Law 4. Clinical safety requires deterministic guarantees, sub-10ms execution, and zero stochastic hallucinations. LLMs are probabilistic and cannot guarantee zero false negatives across drug-drug interaction pairs or dosage limits.
- **Rejected alternative(s) and why not:**
  - *LLM Prompt-based Safety Checker (Few-Shot GPT-4o/Claude):* Rejected because models periodically miss co-prescribed contraindications, exhibit non-deterministic reasoning across identical prompts, and introduce unacceptable latency (500–1500ms) into high-speed pharmacy checkouts.
- **Implication / what this constrains later:** Any new clinical rule (e.g., renal clearance adjustment, pregnancy trimesters) must be explicitly encoded as a structured data row or rule predicate; it cannot simply be "prompted into existence."

---

### D-003 — Strict 8-State Vocabulary Contract
- **Decision:** All safety rail outputs evaluate to exactly one of the 8 specified states: `HIT`, `CHECKED_NO_HIT`, `PARTIAL_COVERAGE`, `UNVERIFIED_INPUT`, `NOT_CHECKED`, `DATA_EXPIRED`, `SOURCE_CONFLICT`, `SERVICE_UNAVAILABLE`.
- **Why:** Mandated by Law 5. Preserves clinical transparency and ensures that unverified or ambiguous inputs are never rendered as "safe."
- **Rejected alternative(s) and why not:**
  - *Binary Safe/Unsafe Boolean:* Rejected as a critical design failure that obscures missing data, unverified brands, and partial coverage.
- **Implication / what this constrains later:** Downstream UI and EMR integration adapters must handle all 8 states gracefully, rendering distinct visual treatments (e.g., Amber for `PARTIAL_COVERAGE`, Red for `HIT` and `UNVERIFIED_INPUT`, Green for `CHECKED_NO_HIT`).

---

### D-004 — Event-Sourced Regulatory DAG with Historical As-Of Querying
- **Decision:** Regulatory status is modeled as an immutable log of gazette events with `supersedes_event_id` pointers, evaluated dynamically as of a specified effective date.
- **Why:** Mandated by Law 7. Drug prohibitions in India evolve through gazette orders, high court interim stays, and subsequent re-notifications (e.g., EV001 -> EV002 stay -> EV003 re-prohibition of Nimesulide + Paracetamol). A static boolean cannot explain *why* or *under which order* a drug is prohibited.
- **Rejected alternative(s) and why not:**
  - *Static `is_banned` Boolean Flag on Product Table:* Rejected by Law 7. Fails to capture legal changes, effective dates, or active court stays.
- **Implication / what this constrains later:** Ingesting new gazette notifications requires only appending an event row and target mappings; no existing historical records are destructively modified.

---

### D-005 — Multi-Item Cumulative Same-Ingredient Dosage Totaling
- **Decision:** Active ingredients from both single-salt and decomposed FDC products are parsed, converted to daily milligram totals via parsed dose frequency multipliers, and aggregated across the prescription. Any duplicate active ingredient generates a `HIT` with the cumulative daily sum as explicit evidence.
- **Why:** Indian prescription practice is dense with hidden duplicate salts across different brand names (e.g. RX01: Dolo 650 + Sinarest Tablet = 2300 mg/day paracetamol; RX09: Telma-H 40 + Telma 40 = 80 mg/day telmisartan). Neither product is an overdose individually, but together they present significant clinical risk.
- **Rejected alternative(s) and why not:**
  - *Per-Product Isolated Check:* Rejected because it cannot detect cumulative overdose across co-prescribed brands.
- **Implication / what this constrains later:** Dose frequency parsing must be robust to noisy clinical notations (`1-0-1`, `TID`, `Q8H`, `SOS`).

---

### D-006 — Non-Silent Ambiguity Review Queue with Structured Reason Codes
- **Decision:** Any product string with multiple potential strength resolutions (e.g., "Telma" without 20/40/80) or unrecognized brand identity lands in `review_queue` with explicit reason codes (`AMBIGUOUS_STRENGTH_MULTIPLE_MATCHES`, `UNRECOGNIZED_BRAND`). It is never silently auto-resolved.
- **Why:** Mandated by Law 6 & Gate G3. Silent guessing of medication strengths can cause patient harm (e.g. dispensing 80mg instead of 20mg).
- **Rejected alternative(s) and why not:**
  - *Default to Most Common SKU (Mode):* Rejected because assuming the modal dosage without clinician confirmation violates patient safety.
- **Implication / what this constrains later:** Outpatient clinics must have a pharmacy technician or clinician queue review step to clear ambiguous items.

---

### D-007 — Clinically Atomic Decision-Unit Chunking for STW Corpus
- **Decision:** STW documents and clinic protocols are segmented by clinical section headings (`FIRST-LINE MANAGEMENT`, `DO NOT / AVOID`, `RED FLAGS`, `DIAGNOSE`) into self-contained clinical decision units, preserving document code, edition, effective date, page anchor, and supersession state.
- **Why:** Blind token chunking breaks clinical sentences, separates drug names from dose restrictions, and detaches contraindications from their indications.
- **Rejected alternative(s) and why not:**
  - *Fixed-size sliding token window (e.g. 512 tokens with 50 overlap):* Rejected because clinical guidelines lose structural context when sliced arbitrarily.
- **Implication / what this constrains later:** Ingestion of new clinical guidelines requires heading recognition or structured Markdown/JSON authoring templates.

---

### D-008 — Dual Extractive Grounded Engine with Pluggable LLM Interface
- **Decision:** Module B implements a deterministic, high-precision extractive grounding engine with BM25 keyword boosting and metadata filtering, paired with an optional pluggable LLM interface.
- **Why:** Guarantees 100% reliable, zero-latency execution on any fresh evaluation machine without requiring external paid API keys or risking network failure, while maintaining full prompt library reproducibility.
- **Rejected alternative(s) and why not:**
  - *Pure External Cloud API Dependency (e.g. OpenAI/Anthropic only):* Rejected because evaluation would fail if API keys are absent, rate-limited, or expired.
- **Implication / what this constrains later:** Offline evaluator test suites run with 100% determinism, while production deployments can swap in frontier LLM providers behind the same validation guardrails.

---

### D-009 — Mandatory Dose Calculation Refusal (Law 12 Enforcement)
- **Decision:** When queried for pediatric or weight-based doses (e.g., Question 2 for 6-year-old pneumonia), the system quotes the clinical formula verbatim (`Amoxicillin 40 mg/kg/day in three divided doses for 5 days`) and explicitly refuses to compute the child's total milligrams.
- **Why:** Mandated by Law 12 and auto-fail condition 7 ("a patient-specific dose calculator"). Automated dose calculation without certified medical device clearance is a regulatory violation.
- **Rejected alternative(s) and why not:**
  - *Calculating the dose with a disclaimer:* Rejected because disclaimers do not alter regulatory device classification under Indian CDSCO rules.
- **Implication / what this constrains later:** Clinicians are reminded of the formula and must perform the confirmation calculation themselves.

---

### D-010 — Conflict and Supersession Disclosure (Never Merge)
- **Decision:** When multiple editions of a clinical workflow exist (e.g., STW-GP-02 Hypertension v2025.2 current vs v2021.1 archive), the system presents both editions with their publication dates and supersession status, refusing to synthesize a middle ground.
- **Why:** Mandated by the Conflict Rule. Merging conflicting recommendations (e.g. blending Atenolol with Amlodipine) creates clinically invalid synthetic guidance.
- **Rejected alternative(s) and why not:**
  - *Presenting only the latest edition:* Rejected because Question 3 explicitly tests awareness of multiple editions and supersession tracking.
- **Implication / what this constrains later:** Medical knowledge graphs must model temporal validity and supersession DAGs across all guideline releases.

---

### D-011 — Clear Separation of Local Clinic Protocols from National Guidance
- **Decision:** Guidance originating from `local_protocol_acute_fever.md` is strictly tagged as `[SUNRISE-SOP-CLIN-014 v2.1: Internal Clinic Protocol]`, with explicit contrast against national STW recommendations.
- **Why:** Mandated by Module B spec. Clinic SOPs are organization-level policies, not national medical evidence. Conflating local clinic protocols with national ICMR guidance undermines trust and legal compliance.
- **Rejected alternative(s) and why not:**
  - *Treating all corpus documents uniformly:* Rejected because doctors must know whether an instruction is national evidence-based consensus or internal clinic policy.
- **Implication / what this constrains later:** Multi-tenant architecture must partition clinic SOPs into tenant-scoped collections while keeping national STWs in the global shared corpus.

---

### D-012 — Honest Abstention on Out-of-Corpus Queries
- **Decision:** Queries concerning conditions outside the active corpus (e.g., Question 9 Migraine, Question 10 Tuberculosis) trigger immediate, clean abstentions stating exactly what is missing.
- **Why:** Mandated by Law 2 & Gate G6. A confident wrong answer scores −1, while an honest abstention scores 0. A clinical AI that admits unknowns is vastly safer and more trustworthy than one that hallucinates.
- **Rejected alternative(s) and why not:**
  - *Attempting a plausible answer from general pre-trained knowledge:* Auto-fail condition. Violates grounding law.
- **Implication / what this constrains later:** Clinical evaluation benchmarks reward abstention calibration alongside precision.
