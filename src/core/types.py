"""
Data contracts and type definitions for BRAHMO Clinical AI.
Implements the exact 8-state vocabulary mandated by Law 5.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class SafetyVerdictState(str, Enum):
    """The 8-state status vocabulary required by binding law 5."""
    HIT = "HIT"
    CHECKED_NO_HIT = "CHECKED_NO_HIT"
    PARTIAL_COVERAGE = "PARTIAL_COVERAGE"
    UNVERIFIED_INPUT = "UNVERIFIED_INPUT"
    NOT_CHECKED = "NOT_CHECKED"
    DATA_EXPIRED = "DATA_EXPIRED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

class NormalizationMethod(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    TOKEN_CLEANED = "TOKEN_CLEANED"
    ALIAS_LEXICAL = "ALIAS_LEXICAL"
    QUEUED_FOR_REVIEW = "QUEUED_FOR_REVIEW"
    SYNTHETIC_DECOMPOSED = "SYNTHETIC_DECOMPOSED"

class ReviewReasonCode(str, Enum):
    AMBIGUOUS_STRENGTH_MULTIPLE_MATCHES = "AMBIGUOUS_STRENGTH_MULTIPLE_MATCHES"
    UNRECOGNIZED_BRAND = "UNRECOGNIZED_BRAND"
    INCOMPLETE_SPECIFICATION = "INCOMPLETE_SPECIFICATION"
    POSSIBLE_PHONETIC_MATCH = "POSSIBLE_PHONETIC_MATCH"
    UNVERIFIED_INPUT = "UNVERIFIED_INPUT"
    IRRATIONAL_COMBINATION_SUSPECT = "IRRATIONAL_COMBINATION_SUSPECT"

class IngredientDecomposition(BaseModel):
    ingredient_name: str
    strength_value: Optional[float] = None
    strength_unit: str = "mg"
    confidence: float = 1.0
    method: str = "CATALOG_EXACT"

class NormalizedDrug(BaseModel):
    raw_name: str
    product_id: Optional[str] = None
    brand_name: Optional[str] = None
    dose_form: Optional[str] = None
    strength_text: Optional[str] = None
    is_fdc: bool = False
    ingredients: List[IngredientDecomposition] = Field(default_factory=list)
    confidence: float = 0.0
    method: NormalizationMethod = NormalizationMethod.QUEUED_FOR_REVIEW
    review_queue_id: Optional[int] = None
    review_reason: Optional[ReviewReasonCode] = None

class PrescriptionItem(BaseModel):
    rx_id: str
    item_no: int
    written_product: str
    strength_as_written: Optional[str] = None
    dose_frequency: Optional[str] = None
    clinical_note: Optional[str] = None

class SafetyCheckFinding(BaseModel):
    check_type: str # 'DUPLICATE_ACTIVE_INGREDIENT', 'PROHIBITED_RESTRICTED_FDC', 'SEVERE_INTERACTION', 'CUMULATIVE_EXPOSURE'
    state: SafetyVerdictState
    severity: str # 'CRITICAL', 'WARNING', 'INFO', 'UNKNOWN'
    evidence: str
    regulatory_citation: Optional[str] = None
    effective_date: Optional[str] = None
    rule_version: str
    data_version: str

class PrescriptionSafetyReport(BaseModel):
    rx_id: str
    overall_state: SafetyVerdictState
    findings: List[SafetyCheckFinding] = Field(default_factory=list)
    cumulative_exposures: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    unresolved_items: List[str] = Field(default_factory=list)
    data_versions: Dict[str, str] = Field(default_factory=dict)
    rule_versions: Dict[str, str] = Field(default_factory=dict)

class ClaimCitation(BaseModel):
    source_document: str # e.g. 'STW-PED-01' or 'SUNRISE-SOP-CLIN-014'
    section_title: str # e.g. 'FIRST-LINE MANAGEMENT'
    page_anchor: str # e.g. 'p.1'
    version: str # e.g. '2024.1'
    effective_date: str # e.g. '2024-05-01'
    is_clinic_internal: bool = False # True for clinic protocol, False for national STW

class GroundedAnswerResponse(BaseModel):
    question_id: Optional[int] = None
    question: str
    answer_text: str
    citations: List[ClaimCitation] = Field(default_factory=list)
    is_abstained: bool = False
    abstention_reason: Optional[str] = None
    conflict_identified: bool = False
    conflict_notes: Optional[str] = None
    refused_dose_calculation: bool = False
