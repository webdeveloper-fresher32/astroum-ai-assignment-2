"""
Hybrid Clinical Information Retrieval Engine for BRAHMO Clinical AI.
Implements BM25 lexical ranking + semantic condition scoring + clinical metadata filtering.
Enforces Law 8 & Module B requirements.
"""

import math
import re
from typing import List, Dict, Tuple, Optional, Set
from collections import Counter
from src.core.config import config
from src.module_b.chunker import ClinicalChunker, DecisionUnit

class HybridClinicalRetriever:
    def __init__(self, units: Optional[List[DecisionUnit]] = None):
        self.units = units or ClinicalChunker.load_entire_corpus()
        self.doc_count = len(self.units)
        self.doc_tokens = [self._tokenize(u.title + " " + u.section_title + " " + u.content_text) for u in self.units]
        self.doc_lengths = [len(tokens) for tokens in self.doc_tokens]
        self.avg_doc_len = sum(self.doc_lengths) / max(1, self.doc_count)
        
        # Calculate term frequencies and document frequencies
        self.df = Counter()
        for tokens in self.doc_tokens:
            for term in set(tokens):
                self.df[term] += 1

        self.k1 = config.bm25_k1
        self.b = config.bm25_b

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        # Lowercase, alphanumeric extraction
        return re.findall(r"\b[a-z0-9]+\b", text.lower())

    def _idf(self, term: str) -> float:
        n_t = self.df.get(term, 0)
        if n_t == 0:
            return 0.0
        return math.log(1.0 + (self.doc_count - n_t + 0.5) / (n_t + 0.5))

    def _bm25_score(self, query_tokens: List[str], doc_idx: int) -> float:
        score = 0.0
        tokens = self.doc_tokens[doc_idx]
        t_count = Counter(tokens)
        doc_len = self.doc_lengths[doc_idx]

        for qt in query_tokens:
            freq = t_count.get(qt, 0)
            if freq == 0:
                continue
            idf = self._idf(qt)
            num = freq * (self.k1 + 1.0)
            denom = freq + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
            score += idf * (num / denom)

        return score

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        include_superseded: bool = False,
        specialty_filter: Optional[str] = None
    ) -> List[Tuple[DecisionUnit, float]]:
        """
        Retrieves top_k decision units for a query with metadata filtering.
        """
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scored_units = []
        is_history_query = any(w in query.lower() for w in ["history", "archive", "2021", "edition", "more than one edition", "earlier", "previous"])

        for idx, unit in enumerate(self.units):
            # Exclude superseded archive versions unless query explicitly asks for historical comparison
            if unit.is_superseded and not include_superseded and not is_history_query:
                continue

            if specialty_filter and specialty_filter.lower() not in unit.specialty.lower():
                continue

            score = self._bm25_score(query_tokens, idx)

            # Boost condition keyword match
            cond_words = [w for w in self._tokenize(unit.condition) if w not in ("in", "and", "adult", "child", "opd", "fever", "initial")]
            for cw in cond_words:
                if cw in query_tokens:
                    score += 4.0

            # Boost exact condition match
            if unit.condition.lower() in query.lower():
                score += 5.0

            # Boost section title match
            sec_words = [w for w in self._tokenize(unit.section_title) if w not in ("in", "and")]
            for sw in sec_words:
                if sw in query_tokens:
                    score += 2.0

            scored_units.append((unit, score))

        scored_units.sort(key=lambda x: x[1], reverse=True)
        return scored_units[:top_k]
