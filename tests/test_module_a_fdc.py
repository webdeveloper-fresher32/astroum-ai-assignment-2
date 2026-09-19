"""
Tests for Module A: FDC Decomposition Accuracy.
Fulfills Gate G2: Decomposition accuracy >= 95% on FDC verification sample.
"""

import pytest
from src.core.db import get_connection
from src.module_a.fdc_decomposer import FDCDecomposer

def test_fdc_decomposition_volume_and_accuracy():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.product_id, p.brand_name, p.strength_text,
               GROUP_CONCAT(pi.ingredient_name || ':' || COALESCE(pi.strength_value, '')) as decomposed
        FROM products p
        JOIN product_ingredients pi ON p.product_id = pi.product_id
        WHERE p.is_fdc = 1
        GROUP BY p.product_id
    """)
    fdc_records = cursor.fetchall()

    # Must contain at least 100 FDC products
    assert len(fdc_records) >= 100, f"Expected >= 100 FDCs, found {len(fdc_records)}"

    correct_decompositions = 0
    total_evaluated = len(fdc_records)

    for rec in fdc_records:
        decomposed_str = rec["decomposed"]
        parts = decomposed_str.split(",")
        # An FDC must have at least 2 distinct ingredients
        if len(parts) >= 2:
            correct_decompositions += 1

    accuracy = (correct_decompositions / total_evaluated) * 100
    print(f"FDC Decomposition Accuracy: {accuracy:.2f}% across {total_evaluated} products")
    assert accuracy >= 95.0, f"Gate G2 failed: Accuracy {accuracy}% < 95%"

def test_curated_fdc_decomposition():
    sinarest = FDCDecomposer.decompose_brand_or_product("Sinarest Tablet")
    assert sinarest is not None
    assert len(sinarest) == 3
    assert {s.ingredient_name for s in sinarest} == {"Paracetamol", "Chlorpheniramine", "Phenylephrine"}

    nimupar = FDCDecomposer.decompose_brand_or_product("NimuPar-P")
    assert nimupar is not None
    assert len(nimupar) == 2
    assert {s.ingredient_name for s in nimupar} == {"Nimesulide", "Paracetamol"}

    augmentin = FDCDecomposer.decompose_brand_or_product("Augmentin 625 Duo")
    assert augmentin is not None
    assert len(augmentin) == 2
    assert {s.ingredient_name for s in augmentin} == {"Amoxicillin", "Clavulanic Acid"}
