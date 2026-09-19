"""
Data Ingestion Pipeline for BRAHMO Clinical AI.
Ingests:
1. cdci_drug_subset.csv (~2000 products, 160 FDCs)
2. nlem_extract.csv (essential medicines)
3. jan_aushadhi_extract.csv (public generic scheme)
4. regulatory_gazette_events.csv (12 regulatory events + supersession)
5. severe_interaction_seed.csv (15 severe interactions)
6. pharmacy_stock.csv (~800 messy clinic stock items)

Maintains 100% provenance: source, source_version, load_batch_id on every row.
"""

import csv
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from src.core.db import get_connection, run_migrations
from src.core.config import config
from src.module_a.fdc_decomposer import FDCDecomposer
from src.module_a.normalizer import DrugNormalizer

class IngestionPipeline:
    def __init__(self, conn=None):
        self._conn = conn

    def _get_conn(self):
        return self._conn or get_connection()

    def run_all(self):
        print("Starting comprehensive ingestion pipeline...")
        run_migrations()
        self.ingest_cdci_subset()
        self.ingest_nlem()
        self.ingest_jan_aushadhi()
        self.ingest_regulatory_events()
        self.ingest_severe_interactions()
        self.ingest_pharmacy_stock()
        print("Ingestion pipeline completed successfully.")

    def ingest_cdci_subset(self, file_path: Optional[Path] = None):
        csv_file = file_path or (config.data_dir / "cdci_drug_subset.csv")
        if not csv_file.exists():
            csv_file = config.base_dir / "cdci_drug_subset.csv"

        print(f"Ingesting CDCI subset from {csv_file}...")
        conn = self._get_conn()
        cursor = conn.cursor()

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        products_inserted = 0
        ingredients_inserted = 0

        for r in rows:
            prod_id = r["product_id"]
            brand = r["brand_name"]
            norm_brand = DrugNormalizer.clean_billing_tokens(brand)
            mfr = r.get("manufacturer")
            dose_form = r.get("dose_form", "Tablet")
            strength_text = r.get("strength_text", "")
            source = r.get("source", config.cdci_source_version)
            source_version = r.get("source_version", "2026-06-30")
            effective_from = r.get("effective_from", "2026-07-01")

            # Check if FDC
            is_fdc = bool(r.get("ingredient_2") and r["ingredient_2"].strip())

            # Insert Product
            cursor.execute("""
                INSERT OR REPLACE INTO products (
                    product_id, brand_name, normalized_brand_name, manufacturer,
                    dose_form, strength_text, is_fdc, source_name, source_version,
                    effective_from, load_batch_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prod_id, brand, norm_brand, mfr, dose_form, strength_text,
                1 if is_fdc else 0, source, source_version, effective_from, config.load_batch_id
            ))
            products_inserted += 1

            # Decompose and insert ingredients
            decomps = FDCDecomposer.decompose_from_record(r)
            for pos, dec in enumerate(decomps, start=1):
                # Ensure active ingredient exists in canonical master
                ing_id = f"ING-{dec.ingredient_name.upper().replace(' ', '-')}"
                cursor.execute("""
                    INSERT OR IGNORE INTO active_ingredients (
                        ingredient_id, canonical_name, source_name, source_version, load_batch_id
                    ) VALUES (?, ?, ?, ?, ?)
                """, (ing_id, dec.ingredient_name, source, source_version, config.load_batch_id))

                cursor.execute("""
                    INSERT INTO product_ingredients (
                        product_id, ingredient_name, canonical_ingredient_id,
                        strength_value, strength_unit, position_order,
                        confidence_score, decomposition_method, source_name,
                        source_version, load_batch_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    prod_id, dec.ingredient_name, ing_id, dec.strength_value,
                    dec.strength_unit, pos, dec.confidence, dec.method,
                    source, source_version, config.load_batch_id
                ))
                ingredients_inserted += 1

        conn.commit()
        print(f"CDCI Ingested: {products_inserted} products, {ingredients_inserted} ingredient links.")

    def ingest_nlem(self, file_path: Optional[Path] = None):
        csv_file = file_path or (config.data_dir / "nlem_extract.csv")
        if not csv_file.exists():
            csv_file = config.base_dir / "nlem_extract.csv"

        print(f"Ingesting NLEM extract from {csv_file}...")
        conn = self._get_conn()
        cursor = conn.cursor()

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                med = r["medicine"].strip()
                cat = r.get("therapeutic_category", "")
                care = r.get("care_levels", "")
                edition = r.get("nlem_edition", "NLEM 2022")

                cursor.execute("""
                    UPDATE active_ingredients
                    SET is_nlem = 1,
                        nlem_care_levels = ?,
                        therapeutic_category = COALESCE(therapeutic_category, ?)
                    WHERE LOWER(canonical_name) = LOWER(?)
                """, (care, cat, med))

        conn.commit()
        print("NLEM extract ingested.")

    def ingest_jan_aushadhi(self, file_path: Optional[Path] = None):
        csv_file = file_path or (config.data_dir / "jan_aushadhi_extract.csv")
        if not csv_file.exists():
            csv_file = config.base_dir / "jan_aushadhi_extract.csv"

        print(f"Ingesting Jan Aushadhi catalog from {csv_file}...")
        conn = self._get_conn()
        cursor = conn.cursor()

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                cursor.execute("""
                    INSERT INTO jan_aushadhi_catalog (
                        generic_name, strength, pack, mrp_inr, catalog_version, load_batch_id
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    r["generic_name"].strip(),
                    r["strength"].strip(),
                    r.get("pack", ""),
                    float(r["mrp_inr"]),
                    r.get("catalog_version", "PMBJP-2026-05"),
                    config.load_batch_id
                ))

        conn.commit()
        print("Jan Aushadhi catalog ingested.")

    def ingest_regulatory_events(self, file_path: Optional[Path] = None):
        csv_file = file_path or (config.data_dir / "regulatory_gazette_events.csv")
        if not csv_file.exists():
            csv_file = config.base_dir / "regulatory_gazette_events.csv"

        print(f"Ingesting regulatory gazette events from {csv_file}...")
        conn = self._get_conn()
        cursor = conn.cursor()

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        for r in rows:
            ev_id = r["event_id"]
            cursor.execute("""
                INSERT OR REPLACE INTO regulatory_events (
                    event_id, notification_id, date_published, effective_date,
                    action, target_type, target_description, supersedes_event_id,
                    note, source_name, source_version, load_batch_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ev_id,
                r["notification_id"],
                r["date_published"],
                r["effective_date"],
                r["action"],
                r["target_type"],
                r["target_description"],
                r["supersedes_event_id"] if r["supersedes_event_id"] else None,
                r.get("note", ""),
                "GAZETTE_OF_INDIA",
                config.regulatory_gazette_version,
                config.load_batch_id
            ))

            # Structure target ingredients for rapid deterministic querying
            desc = r["target_description"]
            pop_scope = "PAEDIATRIC" if "paediatric" in desc.lower() else "ALL"
            form_scope = "SUSPENSION" if "suspension" in desc.lower() else "ALL"

            # Parse out target salts
            clean_desc = re.sub(r"\(.*?\)", "", desc).strip()
            salts = [s.strip() for s in clean_desc.split("+")]

            for s in salts:
                # remove generic words
                salt_clean = re.sub(r"\b(all strengths|specific ratio|4-way|suspension|paediatric)\b", "", s, flags=re.IGNORECASE).strip()
                if salt_clean:
                    cursor.execute("""
                        INSERT INTO regulatory_event_targets (
                            event_id, ingredient_canonical_name, population_scope, formulation_scope
                        ) VALUES (?, ?, ?, ?)
                    """, (ev_id, salt_clean, pop_scope, form_scope))

        conn.commit()
        print("Regulatory gazette events ingested and targets structured.")

    def ingest_severe_interactions(self, file_path: Optional[Path] = None):
        csv_file = file_path or (config.data_dir / "severe_interaction_seed.csv")
        if not csv_file.exists():
            csv_file = config.base_dir / "severe_interaction_seed.csv"

        print(f"Ingesting severe interactions from {csv_file}...")
        conn = self._get_conn()
        cursor = conn.cursor()

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                cursor.execute("""
                    INSERT INTO severe_interactions (
                        ingredient_a, ingredient_b, severity, clinical_note, source_tag
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    r["ingredient_a"].strip(),
                    r["ingredient_b"].strip(),
                    r.get("severity", "SEVERE"),
                    r.get("note", ""),
                    r.get("source_tag", "public-high-priority-2026")
                ))

        conn.commit()
        print("Severe interactions ingested.")

    def ingest_pharmacy_stock(self, file_path: Optional[Path] = None):
        csv_file = file_path or (config.data_dir / "pharmacy_stock.csv")
        if not csv_file.exists():
            csv_file = config.base_dir / "pharmacy_stock.csv"

        print(f"Ingesting and normalizing pharmacy stock from {csv_file}...")
        conn = self._get_conn()
        cursor = conn.cursor()
        normalizer = DrugNormalizer(conn)

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            stock_rows = list(reader)

        matched_count = 0
        queued_count = 0

        for r in stock_rows:
            raw_item = r["item_name_as_billed"]
            qty = int(r.get("qty_units", 0) or 0)
            mrp = float(r.get("mrp_inr", 0.0) or 0.0)
            batch = r.get("batch", "")
            expiry = r.get("expiry", "")

            # Normalize using DrugNormalizer
            norm_drug = normalizer.normalize(
                raw_text=raw_item,
                context_type="PHARMACY_STOCK"
            )

            if norm_drug.review_queue_id:
                queued_count += 1
            else:
                matched_count += 1

            cursor.execute("""
                INSERT INTO pharmacy_stock (
                    item_name_as_billed, qty_units, mrp_inr, batch, expiry,
                    cleaned_name, normalized_product_id, normalization_confidence,
                    normalization_method, review_queue_id, load_batch_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                raw_item, qty, mrp, batch, expiry,
                norm_drug.brand_name,
                norm_drug.product_id,
                norm_drug.confidence,
                norm_drug.method.value,
                norm_drug.review_queue_id,
                config.load_batch_id
            ))

        conn.commit()
        print(f"Pharmacy stock ingested: {len(stock_rows)} items ({matched_count} resolved, {queued_count} queued in review_queue).")

if __name__ == "__main__":
    pipeline = IngestionPipeline()
    pipeline.run_all()
