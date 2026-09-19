"""
Query Router for BRAHMO Clinical AI.
Architecture boundary §2:
Structured facts (drug identity, strengths, regulatory status, Jan Aushadhi prices) answer from Module A directly.
Narrative clinical questions (protocols, guidelines, first-line management) route to Module B RAG.
"""

import re
from typing import Optional, Dict, Any, Tuple
from src.core.db import get_connection
from src.module_a.normalizer import DrugNormalizer
from src.module_a.regulatory_engine import RegulatoryEngine

class QueryRouter:
    def __init__(self, conn=None):
        self._conn = conn
        self.normalizer = DrugNormalizer(conn)
        self.regulatory_engine = RegulatoryEngine(conn)

    def route_query(self, query: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Determines whether a query is a structured fact query or a narrative clinical question.
        Returns: ("STRUCTURED_FACT" | "NARRATIVE_CLINICAL", structured_result_or_none)
        """
        q_lower = query.lower()

        # 1. Regulatory Status Query (e.g., "Is Nimesulide + Paracetamol banned?", "What is regulatory status of Ranitidine?")
        if any(w in q_lower for w in ["banned", "prohibited", "gazette", "legal status", "regulatory status", "restriction"]):
            # Extract possible drug mentions
            for brand_candidate in ["nimesulide + paracetamol", "ranitidine", "nimupar-p", "tramadol", "codeine"]:
                if brand_candidate in q_lower:
                    norm = self.normalizer.normalize(brand_candidate)
                    ing_names = [i.ingredient_name for i in norm.ingredients] or [brand_candidate.title()]
                    reg = self.regulatory_engine.check_regulatory_status(ing_names)
                    if reg:
                        return "STRUCTURED_FACT", {
                            "type": "REGULATORY_STATUS",
                            "drug": brand_candidate,
                            "citation": reg.to_citation(),
                            "event_id": reg.event_id,
                            "notification_id": reg.notification_id,
                            "effective_date": reg.effective_date,
                            "action": reg.action,
                            "note": reg.note
                        }

        # 2. Composition / Active Ingredient Query (e.g., "What are ingredients of Sinarest?")
        if any(w in q_lower for w in ["ingredients of", "salts in", "composition of", "what is in "]):
            # Extract brand name
            m = re.search(r"(?:ingredients of|salts in|composition of|what is in)\s+([A-Za-z0-9\-\s]+)", q_lower)
            if m:
                brand_target = m.group(1).strip()
                norm = self.normalizer.normalize(brand_target)
                if norm.ingredients:
                    ing_list = [f"{i.ingredient_name} ({i.strength_value} {i.strength_unit})" if i.strength_value else i.ingredient_name for i in norm.ingredients]
                    return "STRUCTURED_FACT", {
                        "type": "DRUG_COMPOSITION",
                        "brand": norm.brand_name or brand_target,
                        "ingredients": ing_list,
                        "is_fdc": norm.is_fdc,
                        "source": "India Drug Master (CDCI)"
                    }

        # Default: Narrative Clinical Guideline Question
        return "NARRATIVE_CLINICAL", None
