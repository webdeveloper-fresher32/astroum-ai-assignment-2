-- Migration 002: Event-Sourced Regulatory Register
-- Regulatory status derived from effective-dated regulatory events with supersession DAG
-- Enables exact citation of notification ID, effective date, and legal history

CREATE TABLE IF NOT EXISTS regulatory_events (
    event_id TEXT PRIMARY KEY,
    notification_id TEXT NOT NULL,
    date_published TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    action TEXT NOT NULL, -- 'PROHIBITED', 'RESTRICTED', 'STAY_GRANTED', 'WITHDRAWN'
    target_type TEXT NOT NULL, -- 'FDC', 'INGREDIENT', 'PRODUCT'
    target_description TEXT NOT NULL,
    supersedes_event_id TEXT REFERENCES regulatory_events(event_id),
    note TEXT,
    source_name TEXT NOT NULL DEFAULT 'GAZETTE_OF_INDIA',
    source_version TEXT NOT NULL DEFAULT '2026-REG-EVENT-SET',
    load_batch_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_reg_events_supersedes ON regulatory_events(supersedes_event_id);
CREATE INDEX IF NOT EXISTS idx_reg_events_effective ON regulatory_events(effective_date);

-- Structured target decomposition for high-performance deterministic lookups
CREATE TABLE IF NOT EXISTS regulatory_event_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL REFERENCES regulatory_events(event_id) ON DELETE CASCADE,
    ingredient_canonical_name TEXT NOT NULL,
    population_scope TEXT NOT NULL DEFAULT 'ALL', -- 'ALL', 'PAEDIATRIC', 'ADULT'
    formulation_scope TEXT NOT NULL DEFAULT 'ALL', -- 'ALL', 'SUSPENSION', 'TABLET'
    ratio_specification TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_reg_targets_event ON regulatory_event_targets(event_id);
CREATE INDEX IF NOT EXISTS idx_reg_targets_ing ON regulatory_event_targets(ingredient_canonical_name);
