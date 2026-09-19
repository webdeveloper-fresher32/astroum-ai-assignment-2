"""
Configuration Module for BRAHMO Clinical AI.
Adheres to rule: No hardcoded constants; all paths, thresholds, and version strings load from config.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class AppConfig(BaseModel):
    # Base paths
    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    corpus_dir: Path = BASE_DIR / "corpus"
    output_dir: Path = BASE_DIR / "output"
    migrations_dir: Path = BASE_DIR / "migrations"
    db_path: Path = BASE_DIR / "brahmo_clinical.db"

    # System & Pipeline Versions
    system_version: str = "BRAHMO-AI-v1.0.0"
    safety_rule_version: str = "RULES-SAFE-2026.1"
    cdci_source_version: str = "CDCI-SUBSET-2026Q2"
    regulatory_gazette_version: str = "2026-REG-EVENT-SET"
    stw_corpus_version: str = "ICMR-STW-2026.1"
    local_protocol_version: str = "SUNRISE-SOP-CLIN-014-v2.1"
    load_batch_id: str = "BATCH-20260919-PROD01"

    # Clinical Thresholds (Loadable from env or default clinical standards)
    paracetamol_max_daily_mg: float = float(os.getenv("PARACETAMOL_MAX_DAILY_MG", "3000.0"))
    paracetamol_warning_daily_mg: float = float(os.getenv("PARACETAMOL_WARN_DAILY_MG", "2000.0"))
    normalization_high_confidence_threshold: float = float(os.getenv("NORM_HIGH_CONF", "0.90"))
    normalization_ambiguity_threshold: float = float(os.getenv("NORM_AMBIG_THRESH", "0.75"))

    # RAG / Retrieval Configuration
    bm25_k1: float = float(os.getenv("BM25_K1", "1.5"))
    bm25_b: float = float(os.getenv("BM25_B", "0.75"))
    retrieval_top_k: int = int(os.getenv("RETRIEVAL_TOP_K", "4"))
    similarity_abstention_threshold: float = float(os.getenv("SIM_ABSTAIN_THRESH", "0.28"))

    # LLM Optional Settings
    use_llm_for_grounded_generation: bool = os.getenv("USE_LLM_GENERATION", "false").lower() == "true"
    llm_model_name: str = os.getenv("LLM_MODEL_NAME", "gemini-1.5-pro")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")

    # Multi-tenant Clinic Identifier
    default_tenant_id: str = "CLINIC-SUNRISE-001"

config = AppConfig()
