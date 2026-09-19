"""
Review Queue Management Module for BRAHMO Clinical AI.
Law 6 & Gate G3: Zero silent ambiguity.
Uncertain brand/formulation/strength resolutions are never silently auto-resolved.
They land in review_queue with structured reason codes and candidate options.
"""

import json
from typing import List, Dict, Optional, Any
from src.core.db import get_connection
from src.core.types import ReviewReasonCode
from src.core.config import config

class ReviewQueueManager:
    def __init__(self, conn=None):
        self._conn = conn

    def _get_conn(self):
        return self._conn or get_connection()

    def enqueue_unresolved(
        self,
        raw_input_text: str,
        context_type: str,
        reason_code: ReviewReasonCode,
        confidence_score: float,
        inferred_candidate_brand: Optional[str] = None,
        inferred_product_id: Optional[str] = None,
        candidate_matches: Optional[List[Dict[str, Any]]] = None,
        reviewer_note: Optional[str] = None
    ) -> int:
        """
        Inserts an ambiguous or unverified input into the review queue.
        Returns the created queue_id.
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        matches_json = json.dumps(candidate_matches or [])
        cursor.execute("""
            INSERT INTO review_queue (
                raw_input_text, context_type, inferred_candidate_brand, inferred_product_id,
                candidate_matches_json, confidence_score, reason_code, status,
                reviewer_note, load_batch_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING_REVIEW', ?, ?)
        """, (
            raw_input_text,
            context_type,
            inferred_candidate_brand,
            inferred_product_id,
            matches_json,
            confidence_score,
            reason_code.value,
            reviewer_note,
            config.load_batch_id
        ))
        conn.commit()
        return cursor.lastrowid

    def list_pending(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT queue_id, raw_input_text, context_type, inferred_candidate_brand,
                   inferred_product_id, candidate_matches_json, confidence_score,
                   reason_code, status, created_at
            FROM review_queue
            WHERE status = 'PENDING_REVIEW'
            ORDER BY queue_id DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def count_by_reason(self) -> Dict[str, int]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT reason_code, COUNT(*) as cnt
            FROM review_queue
            GROUP BY reason_code
        """)
        return {row["reason_code"]: row["cnt"] for row in cursor.fetchall()}
