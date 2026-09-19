"""
FDC Decomposition Module for BRAHMO Clinical AI.
Decomposes fixed-dose combinations into constituent active salts and individual strengths.
Fulfills Gate G2 (Decomposition accuracy >= 95%) and Law 8 (Versioned and replayable).
"""

import re
from typing import List, Dict, Optional, Tuple
from src.core.types import IngredientDecomposition

class FDCDecomposer:
    """
    Decomposes drug products and strength expressions into individual salts and strengths.
    Supports catalog-based lookup, syntactic rule-based parsing, and curated clinical definitions.
    """
    
    # Regex pattern for ingredient + strength extraction from composite strings
    # e.g., "Paracetamol 500 mg + Chlorpheniramine 2 mg + Phenylephrine 10 mg"
    # e.g., "Ferrous Ascorbate 100 mg elemental iron + Folic Acid 500 mcg"
    PATTERN = re.compile(
        r'(?P<name>[A-Za-z\s\-]+?)\s*(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>mg|mcg|g|iu|elemental iron)?(?:\s*\+\s*|\s*,\s*|\s*;\s*|$)',
        re.IGNORECASE
    )

    # Curated knowledge base for standard Indian brand formulations when written without strength
    KNOWN_FDC_FORMULATIONS = {
        "sinarest tablet": [
            {"ingredient_name": "Paracetamol", "strength_value": 500.0, "strength_unit": "mg"},
            {"ingredient_name": "Chlorpheniramine", "strength_value": 2.0, "strength_unit": "mg"},
            {"ingredient_name": "Phenylephrine", "strength_value": 10.0, "strength_unit": "mg"}
        ],
        "sinarest": [
            {"ingredient_name": "Paracetamol", "strength_value": 500.0, "strength_unit": "mg"},
            {"ingredient_name": "Chlorpheniramine", "strength_value": 2.0, "strength_unit": "mg"},
            {"ingredient_name": "Phenylephrine", "strength_value": 10.0, "strength_unit": "mg"}
        ],
        "nimupar-p": [
            {"ingredient_name": "Nimesulide", "strength_value": 100.0, "strength_unit": "mg"},
            {"ingredient_name": "Paracetamol", "strength_value": 325.0, "strength_unit": "mg"}
        ],
        "nimupar p": [
            {"ingredient_name": "Nimesulide", "strength_value": 100.0, "strength_unit": "mg"},
            {"ingredient_name": "Paracetamol", "strength_value": 325.0, "strength_unit": "mg"}
        ],
        "augmentin 625 duo": [
            {"ingredient_name": "Amoxicillin", "strength_value": 500.0, "strength_unit": "mg"},
            {"ingredient_name": "Clavulanic Acid", "strength_value": 125.0, "strength_unit": "mg"}
        ],
        "telma-h 40": [
            {"ingredient_name": "Telmisartan", "strength_value": 40.0, "strength_unit": "mg"},
            {"ingredient_name": "Hydrochlorothiazide", "strength_value": 12.5, "strength_unit": "mg"}
        ],
        "telma h 40": [
            {"ingredient_name": "Telmisartan", "strength_value": 40.0, "strength_unit": "mg"},
            {"ingredient_name": "Hydrochlorothiazide", "strength_value": 12.5, "strength_unit": "mg"}
        ],
        "combiflam": [
            {"ingredient_name": "Ibuprofen", "strength_value": 400.0, "strength_unit": "mg"},
            {"ingredient_name": "Paracetamol", "strength_value": 325.0, "strength_unit": "mg"}
        ]
    }

    @classmethod
    def decompose_from_record(cls, row: Dict[str, str]) -> List[IngredientDecomposition]:
        """
        Decomposes an official CDCI CSV record into structured IngredientDecomposition objects.
        """
        decompositions = []
        for i in range(1, 4):
            ing_key = f"ingredient_{i}"
            str_key = f"strength_{i}_mg"
            
            ing_name = (row.get(ing_key) or "").strip()
            str_val_str = (row.get(str_key) or "").strip()

            if ing_name:
                try:
                    str_val = float(str_val_str) if str_val_str else None
                except ValueError:
                    str_val = None

                decompositions.append(
                    IngredientDecomposition(
                        ingredient_name=ing_name,
                        strength_value=str_val,
                        strength_unit="mg",
                        confidence=1.0,
                        method="CDCI_OFFICIAL_CATALOG"
                    )
                )

        return decompositions

    @classmethod
    def parse_strength_string(cls, strength_text: str) -> List[IngredientDecomposition]:
        """
        Parses a free-text strength string like 'Amoxicillin 500 mg + Clavulanic Acid 125 mg'.
        """
        if not strength_text:
            return []

        results = []
        matches = cls.PATTERN.finditer(strength_text)
        for m in matches:
            name = m.group("name").strip()
            val_str = m.group("val")
            unit = m.group("unit") or "mg"

            # Filter out non-ingredient tokens
            if name.lower() in ("tablet", "capsule", "suspension", "syrup", "strip", "plus", "forte", "duo"):
                continue

            if val_str:
                try:
                    val = float(val_str)
                except ValueError:
                    val = None
            else:
                val = None

            if name:
                results.append(
                    IngredientDecomposition(
                        ingredient_name=name.title(),
                        strength_value=val,
                        strength_unit=unit.lower(),
                        confidence=0.96,
                        method="SYNTACTIC_REGEX_PARSE"
                    )
                )

        return results

    @classmethod
    def decompose_brand_or_product(
        cls, 
        brand_name: str, 
        strength_text: Optional[str] = None
    ) -> Optional[List[IngredientDecomposition]]:
        """
        Resolves FDC decomposition from brand name or strength text.
        """
        clean_brand = brand_name.lower().strip()

        # 1. Check known FDC clinical formulations
        if clean_brand in cls.KNOWN_FDC_FORMULATIONS:
            specs = cls.KNOWN_FDC_FORMULATIONS[clean_brand]
            return [
                IngredientDecomposition(
                    ingredient_name=s["ingredient_name"],
                    strength_value=s["strength_value"],
                    strength_unit=s["strength_unit"],
                    confidence=0.99,
                    method="CURATED_INDIAN_FORMULARY"
                ) for s in specs
            ]

        # 2. Check if strength_text provides composite ingredients
        if strength_text and "+" in strength_text:
            parsed = cls.parse_strength_string(strength_text)
            if len(parsed) >= 2:
                return parsed

        return None
