-- Migration 001: Initial Drug Master Schema
-- Defines brand/SKU -> formulation -> strength -> active ingredients
-- Tracks source, source version, effective date, and load batch for 100% provenance

CREATE TABLE IF NOT EXISTS active_ingredients (
    ingredient_id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL UNIQUE,
    therapeutic_category TEXT,
    is_nlem BOOLEAN DEFAULT 0,
    nlem_care_levels TEXT,
    source_name TEXT NOT NULL,
    source_version TEXT NOT NULL,
    load_batch_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_active_ingredients_canonical ON active_ingredients(canonical_name);

CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    brand_name TEXT NOT NULL,
    normalized_brand_name TEXT NOT NULL,
    manufacturer TEXT,
    dose_form TEXT NOT NULL,
    strength_text TEXT NOT NULL,
    is_fdc BOOLEAN NOT NULL DEFAULT 0,
    source_name TEXT NOT NULL,
    source_version TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    load_batch_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand_name);
CREATE INDEX IF NOT EXISTS idx_products_norm_brand ON products(normalized_brand_name);

CREATE TABLE IF NOT EXISTS product_ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    ingredient_name TEXT NOT NULL,
    canonical_ingredient_id TEXT REFERENCES active_ingredients(ingredient_id),
    strength_value REAL,
    strength_unit TEXT NOT NULL DEFAULT 'mg',
    position_order INTEGER NOT NULL DEFAULT 1,
    confidence_score REAL NOT NULL DEFAULT 1.0,
    decomposition_method TEXT NOT NULL DEFAULT 'CATALOG_EXACT',
    source_name TEXT NOT NULL,
    source_version TEXT NOT NULL,
    load_batch_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_product_ingredients_prod ON product_ingredients(product_id);
CREATE INDEX IF NOT EXISTS idx_product_ingredients_name ON product_ingredients(ingredient_name);
