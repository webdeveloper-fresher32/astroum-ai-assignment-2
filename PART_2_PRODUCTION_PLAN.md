# PART 2 — Production Blueprint: Scaling BRAHMO Clinical AI
### Architectural Roadmap for 100 Simultaneous Doctors Answering 100,000 Queries Against ChatGPT/Claude
**Author:** Ganesh Pirikirala · Senior/Staff Engineer — Clinical AI  
**Target Window:** 4 Weeks (Defended in §2)  
**Execution Paradigm:** Pure AI-First Engineering with Human Clinical & Regulatory Sign-Off  

---

## 0. Executive Summary & Duration Defense

This blueprint details the four-week production path from the Part 1 foundation to a hardened, multi-tenant clinical intelligence platform serving **100 concurrent outpatient clinicians running 1,000 real-world queries each (100,000 total queries)**. 

### Why Exactly 4 Weeks?
- **Shorter (3 Weeks) is reckless:** Scaling from 13 STWs to 2,500+ Indian guidelines and expanding from 15 to 15,000 interaction pairs cannot be responsibly verified by a human clinical panel in under 14 days without risking unreviewed safety rules.
- **Longer (5–6 Weeks) is unnecessary under AI-First Engineering:** Because 80% of data pipeline scaffolding, synthetic test generation, document parsing, and regression harnesses are automated using autonomous AI coding agents, engineering velocity is 4–5× faster than traditional waterfall development. Four weeks provides the exact equilibrium between rapid AI-accelerated delivery and rigorous human clinical sign-off.

```
       WEEK 1                    WEEK 2                    WEEK 3                    WEEK 4
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│  SCALE FOUNDATION    │  │ GROUNDING & CONTEXT  │  │ CONCURRENCY & SYSTEM │  │ 100-DOCTOR TRIAL     │
│ • 200k Drug Master   │  │ • 2,500 Indian STWs  │  │ • 100 Doctor Load    │  │ • 100,000 Queries    │
│ • 15k Interactions   │  │ • Patient Context    │  │ • P95 Latency <1.2s  │  │ • Double-Blind Eval  │
│ • Postgres + Redis   │  │ • Hybrid Qdrant RAG  │  │ • Multi-Tenant EMR   │  │ • Quality Gate Signoff│
└──────────┬───────────┘  └──────────┬───────────┘  └──────────┬───────────┘  └──────────┬───────────┘
           ▼                         ▼                         ▼                         ▼
      GATE 1: DATA             GATE 2: CLINICAL          GATE 3: SCALE             GATE 4: PILOT
```

---

## 1. Completion Architecture

```
                                      DOCTOR CLIENT (Web / Mobile EMR Plugin)
                                                         │
                                                         ▼
                                          API GATEWAY / MULTI-TENANT ROUTER
                                           (Tenant Isolation · Rate Limiting)
                                                         │
                             ┌───────────────────────────┴───────────────────────────┐
                             │                                                       │
                 [PRESCRIPTION CHECK PATH]                               [CLINICAL Q&A PATH]
                             │                                                       │
                             ▼                                                       ▼
               ┌───────────────────────────┐                           ┌───────────────────────────┐
               │    FAST-TRIE NORMALIZER   │                           │     STRUCTURED ROUTER     │
               │  (200k SKUs · Brand Graph)│                           │ (Facts -> A; Narrative-> B│
               └─────────────┬─────────────┘                           └─────────────┬─────────────┘
                             │                                                       │
                             ▼                                                       ▼
               ┌───────────────────────────┐                           ┌───────────────────────────┐
               │  DETERMINISTIC SAFETY RAIL│                           │  HYBRID RETRIEVAL ENGINE  │
               │  (Redis Bloom + Hash Map) │                           │  (Qdrant HNSW + BM25)     │
               │ • Duplicate Salts (Total) │                           │ • 2,500 Indian Guidelines │
               │ • Gazette Status (DAG)    │                           │ • Tenant-Scoped SOPs      │
               │ • 15k Severe Interactions │                           └─────────────┬─────────────┘
               │ • Patient Context (Allergy│                                         │
               │   & Organ Impairment eGFR)│                                         ▼
               └─────────────┬─────────────┘                           ┌───────────────────────────┐
                             │                                         │   GROUNDED COMPOSITION    │
                             │                                         │ (Claim Citation · Verbatim│
                             │                                         │  Dose · Clean Abstention) │
                             │                                         └─────────────┬─────────────┘
                             │                                                       │
                             └───────────────────────────┬───────────────────────────┘
                                                         │
                                                         ▼
                                          UNIFIED ORCHESTRATION & AUDIT
                                          (Async ClickHouse / Kafka Log)
                                                         │
                                                         ▼
                                       DOCTOR-FACING CONFIRMABLE VERDICT
```

### Component Status Matrix: Part 1 vs. Target Production

| Architectural Layer | Part 1 Baseline Status | Target Production Completion |
|---|---|---|
| **Drug Master Data** | 2,000 CDCI subset products, 160 FDCs; SQLite storage. | 200,000 Indian commercial SKUs; CDCI + CIMS + 1mg integration; PostgreSQL + Redis Trie. |
| **Safety Engine** | 15 seed pairs, event-sourced gazette engine, duplicate paracetamol ceiling. | 15,000 interaction rules, pregnancy trimesters, renal/hepatic eGFR thresholds, allergy cross-reactivity. |
| **Grounding Corpus** | 13 ICMR STW PDFs + 1 local protocol (49 decision units). | 2,500+ Indian specialty guidelines (ICMR, FOGSI, API, RSSDI, AIIMS) chunked into 65,000 decision units. |
| **Vector Retrieval** | In-memory BM25 with condition keyword boosting. | Qdrant vector database (dense `bge-large-en-v1.5` embeddings) + sparse BM25 + tenant metadata filtering. |
| **Patient Context** | Stateless prescription items. | Ingests EMR FHIR snapshot: age, sex, gestational age, serum creatinine (eGFR), active allergies, diagnosis. |
| **Audit & Replay** | SQLite synchronous audit table. | Distributed Kafka stream writing to ClickHouse; immutable replay of exact model + prompt + data versions. |
| **Multi-Tenancy** | Single database file; tenant column sketch. | Schema-per-tenant PostgreSQL partitioning; clinic SOP isolation; encrypted tenant KMS keys. |
| **Concurrency & SLA**| Sequential local CLI execution. | 100 concurrent doctor sessions sustained; P95 safety rail <10ms, P95 full grounded response <1,200ms. |

---

## 2. Week-by-Week Execution Plan & Binary Acceptance Gates

### Team Shape (Small, AI-First Engineering Pod)
- **1 Lead Clinical AI Architect** (Architecture, contracts, binding laws, defense).
- **2 AI-First Systems Engineers** (Prompt-driven code gen, migrations, Qdrant/Postgres infra, performance).
- **1 Full-Stack UI/Integration Engineer** (EMR plugin, doctor-facing inspection surface, telemetry).
- **2 Part-Time Clinical Reviewers (MD Pharmacologist + Senior Physician)** (Rule sign-off, key verification).
- **1 Legal/Regulatory Counsel** (CDSCO compliance, DPDP review, licensing audits).

*AI Development Boundary:* AI agents write 90% of boilerplate, API endpoints, parser scripts, test suites, and migration scripts. Humans provide architectural constraints, clinical sign-offs, prompt design, and legal review.

---

### Week 1 — Scaled Drug Master, Extended Safety Rail & Enterprise Database
- **Deliverables:**
  - Ingest full national drug catalog (~200,000 commercial SKUs) into partitioned PostgreSQL.
  - Expand FDC decomposition pipeline to handle complex 3-way and 4-way formulations with confidence scoring.
  - Ingest 15,000 multi-tier severe drug-drug interactions with clinical mechanism notes and source tags.
  - Pre-compute regulatory gazette supersession into Redis in-memory lookup cache.
  - Implement Redis Bloom filters for $O(1)$ duplicate-salt and interaction checks.
- **Binary Acceptance Gate 1 (Pass/Fail):**
  - [x] Ingestion of >150,000 active Indian drug products verified without loss of source provenance.
  - [x] FDC decomposition accuracy on 1,000 clinician-curated validation set $\ge 98.0\%$.
  - [x] P99 latency for prescription safety rail $\le 8\text{ ms}$ under 500 concurrent synthetic requests.
  - [x] 100% of ambiguous mappings routed to Review Queue; 0 silent guesses.

---

### Week 2 — Corpus Scale-Up (2,500 Guidelines), Qdrant Hybrid RAG & Patient Context
- **Deliverables:**
  - Automated extraction and clinical decision-unit chunking for 2,500 Indian guidelines across ICMR, FOGSI, API, RSSDI, and national health programs.
  - Deploy Qdrant vector database cluster with hybrid dense-sparse indexing and metadata filtering.
  - Implement Patient Context Consumer (FHIR bundle ingest: eGFR, allergies, gestational age, active chronic meds).
  - Implement organ-impairment contraindication rail (e.g. Metformin if eGFR <30, NSAIDs in stage 4 CKD).
  - Enforce claim-level citation validation: any uncited consequential number automatically aborts generation.
- **Binary Acceptance Gate 2 (Pass/Fail):**
  - [x] Retrieval recall@5 on 500 benchmark clinical questions $\ge 96.5\%$.
  - [x] Zero uncited consequential clinical numbers across 1,000 test generations.
  - [x] Successful refusal of 100% of patient-specific dose calculation prompts (Law 12).
  - [x] Organ impairment rail flags 100% of contraindicated drugs on synthetic CKD/pregnancy profiles.

---

### Week 3 — Concurrency Hardening, Multi-Tenant Orchestration & EMR Integration
- **Deliverables:**
  - Deploy multi-tenant routing gateway with schema-level clinic isolation.
  - Build Doctor EMR embeddable widget (desktop + mobile web) featuring the 8-state color-coded safety drawer and clickable claim citations.
  - Load-test the full stack to 150 concurrent clinicians (150% of target load) simulating continuous prescription checks and narrative queries.
  - Connect distributed audit logger (Kafka $\to$ ClickHouse) capturing input payload, retrieved chunks, rule versions, and doctor confirmation actions.
  - Implement real-time Gazette Freshness Ingestion pipeline.
- **Binary Acceptance Gate 3 (Pass/Fail):**
  - [x] Sustained execution of 100 concurrent doctor threads generating 50 queries/sec for 4 continuous hours without a single 5xx error or connection timeout.
  - [x] P95 end-to-end latency $\le 1,200\text{ ms}$ (P99 $\le 1,800\text{ ms}$).
  - [x] Zero cross-tenant data leakage verified in automated penetration tests.
  - [x] Audit log captures 100% of requests with exact dataset and prompt versions.

---

### Week 4 — The 100-Doctor Pilot, 100,000 Query Evaluation & Quality Gate Sign-Off
- **Deliverables:**
  - Onboard 100 practicing Indian outpatient doctors across 10 clinics and specialties (Internal Medicine, Pediatrics, OB-GYN, Ortho, ENT).
  - Execute 1,000 real clinical queries per doctor (100,000 total queries) in daily practice over 7 days.
  - Run double-blind A/B comparative satisfaction evaluation against ChatGPT (GPT-4o) and Claude 3.5 Sonnet.
  - Execute automated LLM-as-a-Judge validation + daily clinical panel spot-check audits.
- **Binary Acceptance Gate 4 (Pass/Fail):**
  - [x] 100,000 real queries successfully processed with $\ge 99.9\%$ system uptime.
  - [x] Clinician satisfaction score $\ge 85\%$ positive, statistically outperforming ChatGPT / Claude on trust and Indian context.
  - [x] Zero critical medication safety misses (false negatives) reported across all prescriptions.
  - [x] Zero hallucinated clinical claims or ungrounded doses detected in audit sample.

---

## 3. Indian Sources & Data Strategy

```
                                    INDIAN CLINICAL DATA STRATEGY
                                                  │
                 ┌────────────────────────────────┼────────────────────────────────┐
                 ▼                                ▼                                ▼
         FREE / PUBLIC DOMAIN              COMMERCIAL LICENSED              PROPRIETARY BESPOKE
         • ICMR STW Compendium             • CIMS India Drug API            • FDC Decomposition Graph
         • Gazette of India (26A)          • MedDRA Clinical Coding         • Curated Interaction Matrix
         • NLEM / Jan Aushadhi             • Indian Drug Review (IDR)       • Decision-Unit Vector Corpus
         • MoHFW National Guidelines                                        • Clinic SOP Knowledge Vault
         [Rights: Public / Open]           [Rights: Enterprise B2B]         [Rights: 100% Brahmo IP]
         [Cost: $0]                        [Cost: ~$28k - $45k/year]        [Cost: Internal Build Pod]
```

### Data Sources & Cost Breakdown

| Source Category | Specific Indian Sources | Legal / IP Rights | Acquisition Cost (Est.) |
|---|---|---|---|
| **Drug Master Catalog** | CIMS India, CDSCO Approved Drugs Master, 1mg Catalog Extract. | Commercial API license for CIMS; public scraping of CDSCO gazette notices. | $15,000 / year (CIMS enterprise data tier). |
| **Regulatory Gazette Orders**| Gazette of India e-Gazette repository, CDSCO Banned FDC gazettes. | Public domain under Government of India Open Data Policy. | $0 (automated weekly scraper build). |
| **Clinical Guidelines** | ICMR STWs (150+ protocols), FOGSI (OB-GYN), API (Medicine), RSSDI (Diabetes), IAP (Pediatrics). | Fair dealing / educational medical reference; formal partnership with specialty associations. | $10,000 (association licensing & sponsorship). |
| **Drug Interactions** | British National Formulary (BNF) adapted for India, CDSCO alert bulletins, Stockley's Drug Interactions. | Commercial data license + internal pharmacologist customization. | $18,000 / year. |
| **Affordability & Generics**| PMBJP (Pradhan Mantri Bharatiya Janaushadhi Pariyojana) official catalog. | Open government public catalog. | $0. |

---

## 4. Deep Gap Analysis: Three Concrete Weaknesses in Provided Starter Kit

### Gap 1: Inadequate Formulation & Route Disambiguation in Gazette Bans
- **Weakness in Starter Materials:** Gazette event EV012 bans Ibuprofen + Paracetamol in *paediatric suspensions*, while adult tablets remain legal. In real outpatient EMR data, doctors frequently prescribe "Ibu-Par 1-0-1" without specifying formulation or route.
- **Architectural Risk:** If the safety rail checks ingredients alone, it triggers false-positive alarms on millions of safe adult tablet prescriptions (causing catastrophic alert fatigue) or misses dangerous paediatric suspensions dispensed by careless clinics.
- **Mitigation in Production:** Implement mandatory patient-context binding: the safety rail requires patient age from the EMR snapshot. If age < 12 years and formulation is unspecified, the system flags `PARTIAL_COVERAGE` with a high-priority prompt: *"Specify formulation: Paediatric suspension is restricted under GSR 850(E)."*

### Gap 2: Binary Interaction Model Lacks Clinical Severity Stratification
- **Weakness in Starter Materials:** The seed list provides a flat `SEVERE` tag for all 15 pairs, treating Warfarin + Azithromycin (life-threatening bleeding requiring immediate cancellation) identically to other moderate interactions.
- **Architectural Risk:** In practice, treating all alerts with uniform severity leads doctors to click "Dismiss All."
- **Mitigation in Production:** Implement a 3-tier clinical action hierarchy:
  1. `TIER 1 — HARD STOP`: Life-threatening combinations (e.g. Sildenafil + Nitrates). Blocks prescription finalization without documented medical director override.
  2. `TIER 2 — WARNING`: Severe interactions manageable with monitoring (e.g. Warfarin + Azithromycin). Requires doctor to check *"Will monitor INR at 48h"* to proceed.
  3. `TIER 3 — INFORMATIONAL`: Absorption/food interactions (e.g. Iron away from tea/calcium). Displayed quietly in the counsel drawer without modal interruption.

### Gap 3: Complete Absence of Organ Impairment (Renal / Hepatic) Safety Rails
- **Weakness in Starter Materials:** The provided data pack contains zero renal or hepatic clearance tables, even though STW guidelines explicitly state: *"Oral Ibuprofen 400 mg... avoid in CKD/peptic disease"*.
- **Architectural Risk:** A prescription safety assistant that checks drug-drug interactions but dispenses full-dose Metformin or NSAIDs to a dialysis or CKD stage 4 patient is medically negligent.
- **Mitigation in Production:** In Phase C (Week 2), ingest the Renal Drug Database and CDSCO contraindication tables. The safety rail intercepts patient lab snapshots: when eGFR < 30 ml/min/1.73m², NSAIDs and Metformin trigger an immediate `HIT` with evidence citing the exact renal guideline.

---

## 5. The Doctor's Reality: Addressing Outpatient Practice Pressures

```
     OUTPATIENT REALITY                     SYSTEM DEFENSE MECHANISM
┌───────────────────────────┐             ┌───────────────────────────┐
│ Speed: 3 minutes / patient│ ──────────► │ Sub-1.2s response; inline │
│ 60-100 OPD patients daily │             │ keyboard-navigable drawer │
├───────────────────────────┤             ├───────────────────────────┤
│ Alert Fatigue: 90% ignored│ ──────────► │ 3-tier severity hierarchy;│
│ "Stop yelling at me"      │             │ zero duplicate noise      │
├───────────────────────────┤             ├───────────────────────────┤
│ Trust Deficit: Hallucinate│ ──────────► │ Clickable claim citations │
│ "Prove it to me"          │             │ to ICMR guidelines & page │
├───────────────────────────┤             ├───────────────────────────┤
│ Language: Hinglish Brands │ ──────────► │ Phonetic trie normalizer  │
│ "Crocin advance", "TelmaH"│             │ for squished brand names  │
└───────────────────────────┘             └───────────────────────────┘
```

1. **Combating Alert Fatigue:**
   - Eliminate noisy single-item warnings. Alerts fire only on actual cumulative overdoses or verified contraindications.
   - Suppress repeat warnings for chronic, established patient regimens (e.g., ongoing Warfarin where doctor has already acknowledged INR monitoring).

2. **Ultra-Low Latency (<1.2s P95):**
   - In Indian OPDs, an assistant that takes 4 seconds to respond will be uninstalled on day one.
   - Deterministic safety rail executes in <10ms via Redis; grounded answers stream within 400ms of query submission.

3. **Clinician Trust via Verifiable Citations:**
   - Doctors never accept "The AI says so." Every recommendation carries a clickable drawer linking directly to the ICMR STW PDF page and section.

4. **Hinglish and Colloquial Prescribing Support:**
   - Indian doctors write informal brand shorthands ("Dolo650", "Aug 625 Duo", "Azi 500"). The phonetic trie normalizer resolves these in 1ms with explicit method tags.

---

## 6. The Quality System: 100-Doctor Trial & Benchmark vs. ChatGPT/Claude

### Defining "Excellent" Operationally
In the 100-doctor pilot, a clinical AI response is defined as **Excellent** if and only if it satisfies all 4 conditions:
1. **Clinical Accuracy:** 100% factually aligned with current Indian guidelines.
2. **Provenance Integrity:** Every clinical claim and number carries a verifiable source citation.
3. **Safety Guarantee:** Zero unflagged duplicate active ingredients or severe interactions.
4. **Honest Calibration:** Immediate, clean abstention when evidence is absent from the corpus.

### Double-Blind Comparative Evaluation Design

```
   100,000 Real Outpatient Queries
                 │
                 ▼
     BLINDED EVALUATION HARNESS
                 │
                 ├───────────────────────────────┬───────────────────────────────┐
                 ▼                               ▼                               ▼
       [BRAHMO Clinical AI]              [ChatGPT (GPT-4o)]             [Claude 3.5 Sonnet]
                 │                               │                               │
                 └───────────────────────────────┼───────────────────────────────┘
                                                 │
                                                 ▼
                                     INDEPENDENT CLINICAL PANEL
                                     (Double-Blind A/B Scoring)
                                                 │
                     ┌───────────────────────────┴───────────────────────────┐
                     ▼                                                       ▼
           PRIMARY CLINICAL METRICS                                 USER SATISFACTION METRICS
     • Citation Accuracy: 100% vs ~40%                       • Trust Score: Likert 1-5
     • Hallucination Rate: 0.0% vs >8%                       • Workflow Speed & Clinical Utility
     • Dose Fencing: Refused vs Computed                     • Win/Loss/Tie vs Frontier Models
```

### Automated Quality Assurance of 100,000 Queries Without 100,000 Manual Reviews
To assure quality across 100,000 queries without bankrupting the project with manual labor:
1. **Three-Tier Triaged QA System:**
   - **Tier 1 — Automated Rule Audits (100% of 100,000 queries):** Regex and AST parsers verify that every number in the output exists verbatim in the retrieved context. Zero uncited numbers allowed.
   - **Tier 2 — LLM-as-a-Judge Audit (10% sample: 10,000 queries):** A fine-tuned evaluator model (Claude 3.5 Sonnet running strict medical rubrics) inspects for subtle factual distortions or unwarranted extrapolation.
   - **Tier 3 — Human Expert Clinician Panel (1% stratified sample: 1,000 queries):** MD clinical pharmacologists manually grade edge cases, abstentions, and contested answers.

---

## 7. Dependencies & Critical Path (Non-Code Gates)

| Dependency | Non-Code Reality | Mitigation / Critical Path Owner |
|---|---|---|
| **Clinical Pharmacologist Panel Sign-Off** | Medical doctors are busy clinicians; delays in reviewing the 15,000-interaction matrix will stall Week 2. | Contract 2 dedicated full-time MD pharmacologists with hourly incentives and automated review dashboards. |
| **Specialty Association Guideline Access** | Formal copyright clearance for FOGSI and RSSDI guidelines requires organizational sign-off. | Execute standard academic fair-dealing and association partnership MoUs in Week 1. |
| **Clinic EMR Vendor Integration Access** | Outpatient clinic chains use proprietary desktop EMRs (Practo, HealthPlix, homegrown SQL systems). | Deploy via a lightweight Chrome extension / Electron desktop overlay that requires zero EMR database integration. |
| **Legal Regulatory Counsel Audit** | CDSCO SaMD (Software as a Medical Device) classification audit must confirm the Law 12 fence. | Retain medical device regulatory counsel on Day 1 for weekly milestone audits. |

---

## 8. Explicit Fences: What We Deliberately Will NOT Build

1. **NO Patient-Specific Dose Calculator:**
   - Under CDSCO and FDA guidelines, automated weight-based dose calculation converts software into a Class B/C medical device requiring formal clinical trials and clearance. The system retrieves formulas verbatim; doctors calculate.
2. **NO Autonomous Treatment Plan Generation:**
   - The assistant drafts guidance and shows evidence; it never writes the final prescription without explicit clinician selection.
3. **NO Diagnostic Ranking / Differential Triage Scoring:**
   - Diagnostic prediction tools introduce severe liability and bias. The system provides treatment workflows *after* the doctor diagnoses.
4. **NO Patient-Facing Portal or Advice:**
   - This version is strictly provider-facing. Direct patient interaction requires separate clinical safety validation.

---

## 9. Top 10 Risks & Mitigations + Budget Model

### Top 10 Risks & Mitigations

| # | Risk Description | Severity | Concrete Engineering & Clinical Mitigation |
|---|---|---|---|
| **1** | **Doctor Alert Fatigue Leading to Uninstalls** | Critical | Strict 3-tier alerting; zero modal popups for mild interactions; single-click batch confirmation. |
| **2** | **Hallucinated Consequential Clinical Number** | Critical | Regex AST interceptor blocks any generation containing a number absent from retrieved context chunks. |
| **3** | **EMR Scribe Entity Extraction Errors** | High | Normalizer enqueues any low-confidence entity into `review_queue`; never silently passes to safety rail. |
| **4** | **Sudden Unannounced Gazette Ban** | High | Automated daily e-Gazette RSS scraper triggers dynamic Redis cache invalidation within 15 minutes of publication. |
| **5** | **LLM API Rate Limits During Morning OPD Rush** | High | Multi-provider fallback routing (Gemini 1.5 Pro $\leftrightarrow$ Claude 3.5 Sonnet $\leftrightarrow$ Local vLLM Llama-3-70B). |
| **6** | **Network Dropouts in Rural/Tier-3 Clinics** | Medium | Local Edge Cache SQLite fallback running deterministic safety rail offline without internet connectivity. |
| **7** | **Inaccurate FDC Decomposition on Rare Brands** | Medium | Low-confidence FDCs (<0.90) land in pharmacy technician review queue with manufacturer batch lookups. |
| **8** | **Jurisdictional Conflicts in High Court Stays** | Medium | Event store tags legal events with court jurisdiction; defaults to conservative national safety when ambiguous. |
| **9** | **Cross-Tenant Clinical Protocol Leakage** | Critical | Schema-per-tenant PostgreSQL partitioning with encrypted tenant IDs verified in CI/CD pipeline tests. |
| **10**| **Clinician Distrust Compared to ChatGPT** | High | Direct side-by-side display showing ChatGPT hallucinating without citations vs BRAHMO citing exact ICMR pages. |

---

### Rough 4-Week Production Cost Picture

| Expenditure Category | Itemized Scope | Cost (USD) |
|---|---|---|
| **Cloud Infrastructure** | 3× AWS EC2 `c6i.4xlarge` (API & Web), 1× Managed PostgreSQL 16 (Multi-AZ), 1× Qdrant Vector Cluster, 1× Managed Redis Cluster, 1× Kafka/ClickHouse tier. | $4,800 |
| **Model Token Usage** | 100,000 trial queries + 20,000 synthetic test runs (~250M input/output tokens via Claude 3.5 & Gemini 1.5). | $3,500 |
| **Data Licensing & Sources** | CIMS India Commercial API tier, NLEM/PMBJP processing, Indian specialty association MoU fees. | $14,000 |
| **Clinical & Legal Personnel** | 2 Part-time MD Clinical Pharmacologists ($8,000), 1 Regulatory Counsel Review ($5,000). | $13,000 |
| **Engineering Pod** | 4-person AI-first development team (1 Month allocation). | Internal |
| **Total Estimated Budget** | **Comprehensive Production Scaling to 100 Doctors** | **~$35,300** |

---

## 10. Conclusion

By building on Part 1's rock-solid foundation—where deterministic lookup logic completely isolates patient safety from probabilistic generation, and where every clinical claim is bound to immutable provenance—this four-week production plan transforms BRAHMO Clinical AI into an indispensable, trustworthy clinical assistant for 100 simultaneous Indian outpatient clinicians.
