-- Migration 003: Normalization & Review Queue Schema
-- Ensures NO silent resolution of ambiguous brand, strength, or formulation.
-- Every uncertain mapping lands in review_queue with explicit reason codes.

CREATE TABLE IF NOT EXISTS review_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_input_text TEXT NOT NULL,
    context_type TEXT NOT NULL, -- 'PHARMACY_STOCK', 'PRESCRIPTION_RAIL', 'DOCTOR_SEARCH'
    inferred_candidate_brand TEXT,
    inferred_product_id TEXT,
    candidate_matches_json TEXT, -- JSON array of candidate matches with confidence
    confidence_score REAL NOT NULL,
    reason_code TEXT NOT NULL, 
    -- Reason codes:
    -- 'AMBIGUOUS_STRENGTH_MULTIPLE_MATCHES'
    -- 'UNRECOGNIZED_BRAND'
    -- 'INCOMPLETE_SPECIFICATION'
    -- 'POSSIBLE_PHONETIC_MATCH'
    -- 'UNVERIFIED_INPUT'
    -- 'IRRATIONAL_COMBINATION_SUSPECT'
    status TEXT NOT NULL DEFAULT 'PENDING_REVIEW', -- 'PENDING_REVIEW', 'APPROVED', 'REJECTED'
    reviewer_note TEXT,
    resolved_by TEXT,
    resolved_at TEXT,
    load_batch_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_review_queue_reason ON review_queue(reason_code);
CREATE INDEX IF NOT EXISTS idx_review_queue_status ON review_queue(status);

CREATE TABLE IF NOT EXISTS brand_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alias_name TEXT NOT NULL UNIQUE,
    canonical_brand_name TEXT NOT NULL,
    product_id TEXT REFERENCES products(product_id),
    confidence REAL NOT NULL DEFAULT 1.0,
    source TEXT NOT NULL, -- 'CLINIC_STOCK_PATTERN', 'CURATED_SYNONYM', 'PHONETIC_EXPANSION'
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_brand_aliases_name ON brand_aliases(alias_name);

CREATE TABLE IF NOT EXISTS pharmacy_stock (
    stock_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name_as_billed TEXT NOT NULL,
    qty_units INTEGER NOT NULL,
    mrp_inr REAL,
    batch TEXT,
    expiry TEXT,
    cleaned_name TEXT,
    normalized_product_id TEXT REFERENCES products(product_id),
    normalization_confidence REAL,
    normalization_method TEXT, -- 'EXACT_MATCH', 'TOKEN_CLEANED', 'ALIAS_LEXICAL', 'QUEUED_FOR_REVIEW'
    review_queue_id INTEGER REFERENCES review_queue(queue_id),
    load_batch_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_stock_billed ON pharmacy_stock(item_name_as_billed);
CREATE INDEX IF NOT EXISTS idx_stock_prod_id ON pharmacy_stock(normalized_product_id);
