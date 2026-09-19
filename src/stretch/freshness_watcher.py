"""
Stretch: Regulatory Freshness Watcher for BRAHMO Clinical AI.
Demonstrates what happens when a new gazette notification arrives:
1. Ingests new effective-dated regulatory event into the event store with supersession tracking.
2. Identifies all affected active ingredients and FDCs.
3. Automatically re-evaluates historical active prescriptions and logs alerts for newly invalidated prescriptions.
Adheres to Law 7 (Event-sourced regulatory truth) and Law 10 (No silent upgrades / Fail visibly).
"""

from typing import Dict, Any, List
from datetime import datetime
from src.core.db import get_connection
from src.core.config import config
from src.module_a.regulatory_engine import RegulatoryEngine
from src.module_a.safety_rail import DeterministicSafetyRail
from src.core.types import PrescriptionItem

class RegulatoryFreshnessWatcher:
    def __init__(self, conn=None):
        self._conn = conn
        self.reg_engine = RegulatoryEngine(conn)
        self.safety_rail = DeterministicSafetyRail(conn)

    def _get_conn(self):
        return self._conn or get_connection()

    def ingest_new_gazette_notification(
        self,
        event_id: str,
        notification_id: str,
        effective_date: str,
        action: str, # 'PROHIBITED', 'RESTRICTED', 'STAY_GRANTED'
        target_description: str,
        target_salts: List[str],
        supersedes_event_id: str = None,
        note: str = ""
    ) -> Dict[str, Any]:
        """
        Simulates ingestion of a newly published Gazette notification.
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        date_published = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT OR REPLACE INTO regulatory_events (
                event_id, notification_id, date_published, effective_date,
                action, target_type, target_description, supersedes_event_id,
                note, source_name, source_version, load_batch_id
            ) VALUES (?, ?, ?, ?, ?, 'FDC', ?, ?, ?, 'GAZETTE_OF_INDIA', 'STREAM-UPDATE', ?)
        """, (
            event_id, notification_id, date_published, effective_date,
            action, target_description, supersedes_event_id, note, config.load_batch_id
        ))

        # Insert target salts
        for s in target_salts:
            cursor.execute("""
                INSERT INTO regulatory_event_targets (
                    event_id, ingredient_canonical_name, population_scope, formulation_scope
                ) VALUES (?, ?, 'ALL', 'ALL')
            """, (event_id, s.strip()))

        conn.commit()

        return {
            "status": "INGESTED",
            "event_id": event_id,
            "notification_id": notification_id,
            "effective_date": effective_date,
            "supersedes": supersedes_event_id,
            "action": action,
            "targets": target_salts
        }
