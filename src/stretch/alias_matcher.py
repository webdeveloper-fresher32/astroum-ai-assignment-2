"""
Stretch: Colloquial & Phonetic Brand Alias Matcher for BRAHMO Clinical AI.
Handles local brand typos, missing spaces, and common clinic abbreviations
(e.g., 'Dolo650' -> 'Dolo 650', 'Azi 500' -> 'Azee 500', 'Aug 625' -> 'Augmentin 625 Duo').
Never silently resolves: assigns explicit confidence score and method tag 'ALIAS_LEXICAL'.
"""

import re
from typing import Optional, Tuple, Dict, Any, List
from src.core.db import get_connection

class BrandAliasMatcher:
    # Curated dictionary of common outpatient brand shorthands in Indian clinics
    COMMON_SHORTHANDS = {
        "dolo650": "Dolo 650",
        "calpol650": "Calpol 650",
        "crocin650": "Crocin 650",
        "azi 500": "Azee 500",
        "azi500": "Azee 500",
        "azithral500": "Azithral 500",
        "aug 625": "Augmentin 625 Duo",
        "aug625": "Augmentin 625 Duo",
        "telma40": "Telma 40",
        "telma20": "Telma 20",
        "telmah40": "Telma-H 40",
        "glyco 500": "Glycomet 500",
        "glycomet500": "Glycomet 500",
        "pan40": "Pan 40",
        "panto 40": "Pan 40",
        "thymo 50": "Thyronorm 50"
    }

    @classmethod
    def match_alias(cls, raw_brand: str) -> Optional[Tuple[str, float, str]]:
        """
        Attempts to match a colloquial abbreviation or squished string.
        Returns (canonical_brand, confidence_score, source_rule).
        """
        clean = re.sub(r"[^a-zA-Z0-9]", "", raw_brand).lower()

        # 1. Shorthand dictionary lookup
        if clean in cls.COMMON_SHORTHANDS:
            return cls.COMMON_SHORTHANDS[clean], 0.88, "CLINIC_SHORTHAND_DICTIONARY"

        # 2. Check for squished number patterns (e.g. BrandName500 -> BrandName 500)
        match = re.match(r"^([a-zA-Z]+)(\d+)$", clean)
        if match:
            reconstructed = f"{match.group(1).title()} {match.group(2)}"
            return reconstructed, 0.85, "SQUISHED_TOKEN_RECONSTRUCTION"

        return None
