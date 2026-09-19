# SCALE.md — Strain Analysis at 100× Volume & 100 Concurrent Doctors

## 1. Baseline Part 1 vs. 100× Scale Profile

| Dimension | Part 1 Baseline | 100× Production Target | Architectural Strain Point |
|---|---|---|---|
| **Drug Master SKUs** | ~2,000 CDCI subset products | ~200,000 Indian commercial SKUs | In-memory normalizer lookups; string matching latency. |
| **Severe Interactions** | 15 seed pairs | ~15,000 multi-tier interaction pairs | Combinatorial drug-drug pair queries ($O(N^2)$ checks). |
| **Clinical Corpus** | 13 STWs + 1 clinic SOP (49 units) | >2,500 Indian specialty guidelines | Linear in-memory BM25 search creates CPU cache thrashing. |
| **Concurrent Clinicians**| 1 user (local process) | 100 active doctors simultaneous | SQLite single-writer lock blocks concurrent audit logging. |
| **Query Throughput** | Sequential CLI / batch eval | 25–50 queries/sec sustained; 100 peak | Latency SLA (<1,500ms total, <10ms for safety rail). |

---

## 2. Where the Part-1 Architecture Strains First

### A. Database Write Serialization (The SQLite Bottleneck)
*Strain:* In Part 1, SQLite operates in WAL mode. While WAL permits multiple concurrent readers, it enforces a **single exclusive writer lock**. Under 100 concurrent doctors, simultaneous writes to `audit_traces`, `review_queue`, and prescription logs will encounter `SQLITE_BUSY` contention, queuing write transactions and spiking P99 latency above 2,500ms.

### B. In-Memory Full-Scan BM25 Ranking
*Strain:* Part 1's `HybridClinicalRetriever` recalculates BM25 term frequencies dynamically across all corpus decision units. With 49 units, this executes in 0.4ms. At 100× (5,000+ decision units across ICMR, FOGSI, API, RSSDI, and state protocols), pure Python term frequency iterations will consume 120–250ms of CPU per query, saturating multi-core workers and choking throughput.

### C. Combinatorial Drug-Drug Interaction Lookups
*Strain:* In a 6-drug prescription containing multiple FDCs, resolving 12 active salts requires $\binom{12}{2} = 66$ distinct interaction table lookups. At 100 concurrent doctors, this triggers 6,600 SQL queries per second against the interactions table, stressing database connection pools.

### D. Dynamic Regulatory DAG Traversal Per Request
*Strain:* In Part 1, `RegulatoryEngine` queries all historical gazette events and walks supersession chains dynamically on each check. While negligible for 12 events, a full national gazette history (>1,000 historical notifications and court stays) makes recursive DAG traversal expensive on the critical path.

---

## 3. What to Change First (The Immediate Production Evolution)

1. **Migrate Database to PostgreSQL with Read Replicas & PgBouncer:**
   - Replace SQLite with managed PostgreSQL 16.
   - Separate OLTP read traffic (Drug Master lookups, STW retrieval) from heavy write streams via read replicas.
   - Implement PgBouncer with transaction pooling to handle 100+ concurrent clinician connections with sub-millisecond connection overhead.

2. **Decouple Audit Logging & Review Queue Ingestion to Async Event Streams:**
   - Introduce Redis Streams or Kafka to decouple writes from the user-facing request path.
   - Safety checks log audit traces to the in-memory stream in <0.5ms; background consumers batch-write to ClickHouse / PostgreSQL cold storage without blocking the clinician's UI.

3. **Materialize Effective Regulatory Status & Interaction Graph in In-Memory Redis:**
   - Pre-compute current legal standing for all active ingredient sets at the time a gazette notification is ingested.
   - Cache active prohibited FDC sets and severe interaction pairs as a Bloom filter or Redis Hash (`HGETALL interactions:{salt_a}:{salt_b}`).
   - Drug-drug interaction checks drop from 66 database queries to sub-millisecond in-memory hash lookups ($O(1)$ per pair).

4. **Vector Database with Native Hybrid HNSW Indexing (Qdrant / pgvector):**
   - Replace in-memory Python BM25 with a dedicated vector engine (Qdrant or PostgreSQL `pgvector` with HNSW index).
   - Combine dense clinical embeddings (e.g. `bge-base-en-v1.5` or `Med-BioBERT`) with sparse BM25 lexical search, filtered by metadata (`specialty`, `effective_date`, `is_superseded = false`).
   - Grounded retrieval executes in <15ms across 50,000 clinical decision units.

5. **Clustered Fast-Lookup Prefix Trie for Drug Normalization:**
   - Implement a C-accelerated or Rust-backed Marisa-Trie for prefix matching across 200,000 brand SKUs and aliases.
   - Disambiguates exact brands in <0.2ms and isolates multi-strength ambiguities instantaneously.
