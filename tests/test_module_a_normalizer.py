"""
Tests for Module A: Normalization Pipeline & Ambiguity Review Queue.
Fulfills Gate G3: Zero silent resolutions.
"""

import pytest
from src.module_a.normalizer import DrugNormalizer
from src.core.types import NormalizationMethod, ReviewReasonCode
from src.module_a.review_queue import ReviewQueueManager

def test_clean_billing_tokens():
    assert DrugNormalizer.clean_billing_tokens("MIZITH-FORTE STRIP") == "Mizith Forte"
    assert DrugNormalizer.clean_billing_tokens("MIVIN-FORTE TAB 15'S") == "Mivin Forte"
    assert DrugNormalizer.clean_billing_tokens("KOFEN-2-DUO 100ML SYP") == "Kofen 2 Duo"
    assert DrugNormalizer.clean_billing_tokens("ZYVIN-2 15S") == "Zyvin 2"

def test_exact_brand_match():
    normalizer = DrugNormalizer()
    res = normalizer.normalize("Dolo 650")
    assert res.confidence == 1.0
    assert res.method == NormalizationMethod.EXACT_MATCH
    assert res.brand_name == "Dolo 650"
    assert len(res.ingredients) == 1
    assert res.ingredients[0].ingredient_name == "Paracetamol"
    assert res.ingredients[0].strength_value == 650.0

def test_ambiguous_strength_enters_review_queue():
    normalizer = DrugNormalizer()
    # "Telma" has variants Telma 20, Telma 40, Telma 80 in CDCI
    res = normalizer.normalize("Telma")
    assert res.confidence < 0.70
    assert res.method == NormalizationMethod.QUEUED_FOR_REVIEW
    assert res.review_reason == ReviewReasonCode.AMBIGUOUS_STRENGTH_MULTIPLE_MATCHES
    assert res.review_queue_id is not None

    # Disambiguated by written strength
    res_disambiguated = normalizer.normalize("Telma", strength_as_written="40 mg")
    assert res_disambiguated.confidence >= 0.95
    assert "40" in res_disambiguated.strength_text

def test_unrecognized_brand_never_guesses():
    normalizer = DrugNormalizer()
    res = normalizer.normalize("Zqtrixon Forte")
    assert res.confidence == 0.0
    assert res.method == NormalizationMethod.QUEUED_FOR_REVIEW
    assert res.review_reason == ReviewReasonCode.UNRECOGNIZED_BRAND
    assert res.review_queue_id is not None
    assert len(res.ingredients) == 0

def test_zero_silent_resolutions_in_queue():
    queue_mgr = ReviewQueueManager()
    counts = queue_mgr.count_by_reason()
    assert counts.get(ReviewReasonCode.UNRECOGNIZED_BRAND.value, 0) > 0
    assert counts.get(ReviewReasonCode.AMBIGUOUS_STRENGTH_MULTIPLE_MATCHES.value, 0) > 0
