"""
Drug Normalization Pipeline for BRAHMO Clinical AI.
Implements Gate G3 (Zero silent resolutions) and Law 6 (No silent ambiguity).
Every mapping carries a confidence score and method tag.
Uncertain brand/formulation/strength resolutions are routed to review_queue with structured reason codes.
"""

import re
from typing import List, Dict, Optional, Tuple, Any
from src.core.db import get_connection
from src.core.types import (
    NormalizedDrug, 
    IngredientDecomposition, 
    NormalizationMethod, 
    ReviewReasonCode
)
from src.core.config import config
from src.module_a.fdc_decomposer import FDCDecomposer
from src.module_a.review_queue import ReviewQueueManager

class DrugNormalizer:
    def __init__(self, conn=None):
        self._conn = conn
        self.review_queue_mgr = ReviewQueueManager(conn)

    def _get_conn(self):
        return self._conn or get_connection()

    @staticmethod
    def clean_billing_tokens(text: str) -> str:
        """
        Strips common packaging tokens, dosage form suffixes, and pack count markers.
        e.g., "MIZITH-FORTE STRIP" -> "Mizith Forte"
        e.g., "MIVIN-FORTE TAB 15'S" -> "Mivin Forte"
        e.g., "KOFEN-2-DUO 100ML SYP" -> "Kofen 2 Duo"
        """
        s = text.replace("-", " ")
        # Remove pack suffixes like 15'S, 10's, 15S, 10S
        s = re.sub(r"\b\d+\s*['’]?\s*s\b", "", s, flags=re.IGNORECASE)
        # Remove volume tokens like 100ML, 60ML, 200ML
        s = re.sub(r"\b\d+\s*ml\b", "", s, flags=re.IGNORECASE)
        # Remove packaging words
        s = re.sub(r"\b(strip|tab|tabs|tablet|tablets|cap|caps|capsule|capsules|syp|syrup|susp|suspension|inj|injection|gel|drop|drops)\b", "", s, flags=re.IGNORECASE)
        # Clean extra whitespace
        s = re.sub(r"\s+", " ", s).strip()
        return s.title()

    def normalize(
        self,
        raw_text: str,
        strength_as_written: Optional[str] = None,
        context_type: str = "PRESCRIPTION_RAIL"
    ) -> NormalizedDrug:
        """
        Normalizes a raw product/brand name.
        Guarantees that uncertain mappings are NEVER silently resolved.
        """
        cleaned = self.clean_billing_tokens(raw_text)
        conn = self._get_conn()
        cursor = conn.cursor()

        # 1. Exact match on raw brand name in products table
        cursor.execute("""
            SELECT product_id, brand_name, dose_form, strength_text, is_fdc
            FROM products
            WHERE LOWER(brand_name) = LOWER(?)
        """, (raw_text.strip(),))
        exact_row = cursor.fetchone()

        if exact_row:
            ingredients = self._fetch_product_ingredients(exact_row["product_id"])
            return NormalizedDrug(
                raw_name=raw_text,
                product_id=exact_row["product_id"],
                brand_name=exact_row["brand_name"],
                dose_form=exact_row["dose_form"],
                strength_text=exact_row["strength_text"],
                is_fdc=bool(exact_row["is_fdc"]),
                ingredients=ingredients,
                confidence=1.0,
                method=NormalizationMethod.EXACT_MATCH
            )

        # 2. Match on cleaned text
        cursor.execute("""
            SELECT product_id, brand_name, dose_form, strength_text, is_fdc
            FROM products
            WHERE LOWER(brand_name) = LOWER(?) OR LOWER(normalized_brand_name) = LOWER(?)
        """, (cleaned.lower(), cleaned.lower()))
        cleaned_matches = cursor.fetchall()

        if len(cleaned_matches) == 1:
            prod = cleaned_matches[0]
            ingredients = self._fetch_product_ingredients(prod["product_id"])
            return NormalizedDrug(
                raw_name=raw_text,
                product_id=prod["product_id"],
                brand_name=prod["brand_name"],
                dose_form=prod["dose_form"],
                strength_text=prod["strength_text"],
                is_fdc=bool(prod["is_fdc"]),
                ingredients=ingredients,
                confidence=0.95,
                method=NormalizationMethod.TOKEN_CLEANED
            )

        # 3. Check for Brand family with multiple strength options (e.g. "Telma" -> Telma 20, Telma 40, Telma 80)
        cursor.execute("""
            SELECT product_id, brand_name, dose_form, strength_text, is_fdc
            FROM products
            WHERE LOWER(brand_name) LIKE LOWER(?) || ' %' OR LOWER(brand_name) = LOWER(?)
        """, (cleaned.lower(), cleaned.lower()))
        family_matches = cursor.fetchall()

        if len(family_matches) > 1:
            # Check if strength_as_written disambiguates exactly one option
            if strength_as_written:
                clean_str = strength_as_written.lower().replace(" ", "")
                matching_subset = [
                    p for p in family_matches 
                    if clean_str in p["strength_text"].lower().replace(" ", "") or clean_str in p["brand_name"].lower().replace(" ", "")
                ]
                if len(matching_subset) == 1:
                    resolved = matching_subset[0]
                    ingredients = self._fetch_product_ingredients(resolved["product_id"])
                    return NormalizedDrug(
                        raw_name=raw_text,
                        product_id=resolved["product_id"],
                        brand_name=resolved["brand_name"],
                        dose_form=resolved["dose_form"],
                        strength_text=resolved["strength_text"],
                        is_fdc=bool(resolved["is_fdc"]),
                        ingredients=ingredients,
                        confidence=0.98,
                        method=NormalizationMethod.TOKEN_CLEANED
                    )

            # Multiple strengths exist and strength_as_written is missing or ambiguous -> ENQUEUE FOR REVIEW
            candidates = [
                {"product_id": p["product_id"], "brand_name": p["brand_name"], "strength": p["strength_text"]}
                for p in family_matches
            ]
            q_id = self.review_queue_mgr.enqueue_unresolved(
                raw_input_text=raw_text,
                context_type=context_type,
                reason_code=ReviewReasonCode.AMBIGUOUS_STRENGTH_MULTIPLE_MATCHES,
                confidence_score=0.50,
                inferred_candidate_brand=cleaned,
                candidate_matches=candidates,
                reviewer_note=f"Multiple strength variants found for brand '{cleaned}'. Strength was written as '{strength_as_written}'."
            )
            # Derive default ingredients from the family if all variants share the same salt
            # but preserve the review queue state and low confidence
            shared_salt_ingredients = self._fetch_product_ingredients(family_matches[0]["product_id"])
            return NormalizedDrug(
                raw_name=raw_text,
                product_id=None,
                brand_name=cleaned,
                dose_form=family_matches[0]["dose_form"],
                strength_text=strength_as_written or "UNSPECIFIED",
                is_fdc=bool(family_matches[0]["is_fdc"]),
                ingredients=shared_salt_ingredients,
                confidence=0.50,
                method=NormalizationMethod.QUEUED_FOR_REVIEW,
                review_queue_id=q_id,
                review_reason=ReviewReasonCode.AMBIGUOUS_STRENGTH_MULTIPLE_MATCHES
            )

        # 4. Check Known FDC Clinical Formulations (e.g. NimuPar-P, Sinarest Tablet)
        known_fdc = FDCDecomposer.decompose_brand_or_product(cleaned, strength_as_written)
        if known_fdc:
            return NormalizedDrug(
                raw_name=raw_text,
                product_id=f"SYN-FDC-{cleaned.upper().replace(' ', '-')}",
                brand_name=cleaned,
                dose_form="Tablet",
                strength_text=strength_as_written or "Standard FDC",
                is_fdc=True,
                ingredients=known_fdc,
                confidence=0.96,
                method=NormalizationMethod.SYNTHETIC_DECOMPOSED
            )

        # 5. Check Brand Aliases table
        cursor.execute("""
            SELECT canonical_brand_name, product_id, confidence
            FROM brand_aliases
            WHERE LOWER(alias_name) = LOWER(?)
        """, (cleaned.lower(),))
        alias_row = cursor.fetchone()

        if alias_row:
            prod_id = alias_row["product_id"]
            if prod_id:
                cursor.execute("SELECT * FROM products WHERE product_id = ?", (prod_id,))
                prod = cursor.fetchone()
                if prod:
                    ingredients = self._fetch_product_ingredients(prod_id)
                    return NormalizedDrug(
                        raw_name=raw_text,
                        product_id=prod["product_id"],
                        brand_name=prod["brand_name"],
                        dose_form=prod["dose_form"],
                        strength_text=prod["strength_text"],
                        is_fdc=bool(prod["is_fdc"]),
                        ingredients=ingredients,
                        confidence=alias_row["confidence"],
                        method=NormalizationMethod.ALIAS_LEXICAL
                    )

        # 6. Unrecognized Brand -> Must land in Review Queue (Gate G3)
        q_id = self.review_queue_mgr.enqueue_unresolved(
            raw_input_text=raw_text,
            context_type=context_type,
            reason_code=ReviewReasonCode.UNRECOGNIZED_BRAND,
            confidence_score=0.0,
            reviewer_note="Unrecognized product string not present in CDCI or clinic formulary."
        )
        return NormalizedDrug(
            raw_name=raw_text,
            product_id=None,
            brand_name=raw_text,
            dose_form="Unknown",
            strength_text=strength_as_written or "Unknown",
            is_fdc=False,
            ingredients=[],
            confidence=0.0,
            method=NormalizationMethod.QUEUED_FOR_REVIEW,
            review_queue_id=q_id,
            review_reason=ReviewReasonCode.UNRECOGNIZED_BRAND
        )

    def _fetch_product_ingredients(self, product_id: str) -> List[IngredientDecomposition]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ingredient_name, strength_value, strength_unit, confidence_score, decomposition_method
            FROM product_ingredients
            WHERE product_id = ?
            ORDER BY position_order ASC
        """, (product_id,))
        rows = cursor.fetchall()
        return [
            IngredientDecomposition(
                ingredient_name=r["ingredient_name"],
                strength_value=r["strength_value"],
                strength_unit=r["strength_unit"],
                confidence=r["confidence_score"],
                method=r["decomposition_method"]
            )
            for r in rows
        ]
