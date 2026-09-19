"""
Event-Sourced Regulatory Register Engine for BRAHMO Clinical AI.
Law 7: Regulatory truth is event-sourced. Status derives from effective-dated regulatory events.
A plain `banned = true/false` is a design failure; every check output cites notification ID and effective date.
"""

from typing import List, Dict, Optional, Set, Any
from datetime import datetime
from src.core.db import get_connection
from src.core.types import SafetyVerdictState

class RegulatoryStatus:
    def __init__(
        self,
        event_id: str,
        notification_id: str,
        effective_date: str,
        action: str,
        target_description: str,
        note: Optional[str] = None,
        supersession_chain: Optional[List[str]] = None
    ):
        self.event_id = event_id
        self.notification_id = notification_id
        self.effective_date = effective_date
        self.action = action # PROHIBITED, RESTRICTED, STAY_GRANTED, WITHDRAWN
        self.target_description = target_description
        self.note = note
        self.supersession_chain = supersession_chain or []

    def to_citation(self) -> str:
        chain_info = f" (supersedes {', '.join(self.supersession_chain)})" if self.supersession_chain else ""
        return f"{self.action} under {self.notification_id} (Effective: {self.effective_date}){chain_info}: {self.note or self.target_description}"

class RegulatoryEngine:
    def __init__(self, conn=None):
        self._conn = conn

    def _get_conn(self):
        return self._conn or get_connection()

    def check_regulatory_status(
        self,
        ingredients: List[str],
        dose_form: Optional[str] = None,
        is_paediatric: bool = False,
        as_of_date: Optional[str] = None
    ) -> Optional[RegulatoryStatus]:
        """
        Resolves regulatory status for a given ingredient set as of a specific date (default: today).
        Traverses supersession chains to determine current legal standing.
        """
        eval_date = as_of_date or datetime.now().strftime("%Y-%m-%d")
        conn = self._get_conn()
        cursor = conn.cursor()

        # Fetch all regulatory events effective on or before eval_date
        cursor.execute("""
            SELECT event_id, notification_id, date_published, effective_date, 
                   action, target_type, target_description, supersedes_event_id, note
            FROM regulatory_events
            WHERE effective_date <= ?
            ORDER BY effective_date ASC
        """, (eval_date,))
        all_events = [dict(row) for row in cursor.fetchall()]

        # Build supersession mapping
        superseded_by = {}
        for ev in all_events:
            if ev["supersedes_event_id"]:
                superseded_by[ev["supersedes_event_id"]] = ev["event_id"]

        # Normalize incoming ingredients
        ing_set = {i.strip().lower() for i in ingredients}

        # Check each event against the target ingredients
        matching_events = []
        for ev in all_events:
            event_id = ev["event_id"]
            cursor.execute("""
                SELECT ingredient_canonical_name, population_scope, formulation_scope
                FROM regulatory_event_targets
                WHERE event_id = ?
            """, (event_id,))
            targets = cursor.fetchall()

            if not targets:
                continue

            # Scope checks
            scope_match = True
            for t in targets:
                pop_scope = t["population_scope"]
                form_scope = t["formulation_scope"]

                if pop_scope == "PAEDIATRIC" and not is_paediatric:
                    scope_match = False
                    break
                if form_scope == "SUSPENSION" and dose_form and "susp" not in dose_form.lower():
                    scope_match = False
                    break

            if not scope_match:
                continue

            target_ings = {t["ingredient_canonical_name"].strip().lower() for t in targets}

            if ev["target_type"] == "FDC":
                # For FDC, all target ingredients must be present in the product
                if target_ings.issubset(ing_set):
                    matching_events.append(ev)
            elif ev["target_type"] in ("INGREDIENT", "PRODUCT"):
                # For single ingredient or product, any target ingredient present matches
                if target_ings.intersection(ing_set):
                    matching_events.append(ev)

        if not matching_events:
            return None

        # Resolve active event (latest in supersession chain)
        active_event = None
        supersession_chain = []

        # Start from the last matching event
        curr = matching_events[-1]
        active_event = curr
        
        # Track historical supersession chain
        prev_id = curr.get("supersedes_event_id")
        while prev_id:
            supersession_chain.append(prev_id)
            prev_ev = next((e for e in all_events if e["event_id"] == prev_id), None)
            if prev_ev and prev_ev.get("supersedes_event_id"):
                prev_id = prev_ev["supersedes_event_id"]
            else:
                break

        return RegulatoryStatus(
            event_id=active_event["event_id"],
            notification_id=active_event["notification_id"],
            effective_date=active_event["effective_date"],
            action=active_event["action"],
            target_description=active_event["target_description"],
            note=active_event["note"],
            supersession_chain=supersession_chain
        )
