-- Migration 004: Safety Interactions & Complete Audit Log
-- Severe interactions list, essential medicines mapping, and audit trail for 100% provenance

CREATE TABLE IF NOT EXISTS severe_interactions (
    interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_a TEXT NOT NULL,
    ingredient_b TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'SEVERE',
    clinical_note TEXT NOT NULL,
    source_tag TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_interactions_ab ON severe_interactions(ingredient_a, ingredient_b);
CREATE INDEX IF NOT EXISTS idx_interactions_ba ON severe_interactions(ingredient_b, ingredient_a);

CREATE TABLE IF NOT EXISTS jan_aushadhi_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    generic_name TEXT NOT NULL,
    strength TEXT NOT NULL,
    pack TEXT,
    mrp_inr REAL NOT NULL,
    catalog_version TEXT NOT NULL,
    load_batch_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_jan_aushadhi_gen ON jan_aushadhi_catalog(generic_name);

CREATE TABLE IF NOT EXISTS audit_traces (
    trace_id TEXT PRIMARY KEY,
    request_type TEXT NOT NULL, -- 'SAFETY_RAIL_CHECK', 'E2E_PRESCRIPTION_QA', 'MINI_EVAL'
    input_payload_json TEXT NOT NULL,
    verdict_state TEXT NOT NULL, -- The 8-state verdict
    output_payload_json TEXT NOT NULL,
    data_versions_json TEXT NOT NULL,
    rule_versions_json TEXT NOT NULL,
    execution_time_ms REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_traces_verdict ON audit_traces(verdict_state);
CREATE INDEX IF NOT EXISTS idx_audit_traces_created ON audit_traces(created_at);
