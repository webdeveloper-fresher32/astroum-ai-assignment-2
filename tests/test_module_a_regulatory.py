"""
Tests for Module A: Event-Sourced Regulatory Register.
Law 7: Regulatory truth is event-sourced. Status derives from effective-dated regulatory events.
Cites notification ID and effective date; traverses supersession chains.
"""

import pytest
from src.module_a.regulatory_engine import RegulatoryEngine

def test_event_sourced_supersession_chain():
    engine = RegulatoryEngine()

    # 1. As of 2018-10-01: EV001 should be PROHIBITED
    status_2018 = engine.check_regulatory_status(
        ingredients=["Nimesulide", "Paracetamol"],
        as_of_date="2018-10-01"
    )
    assert status_2018 is not None
    assert status_2018.event_id == "EV001"
    assert status_2018.action == "PROHIBITED"
    assert status_2018.notification_id == "GSR 704(E)"

    # 2. As of 2020-01-01: High Court stay EV002 was in effect
    status_2020 = engine.check_regulatory_status(
        ingredients=["Nimesulide", "Paracetamol"],
        as_of_date="2020-01-01"
    )
    assert status_2020 is not None
    assert status_2020.event_id == "EV002"
    assert status_2020.action == "STAY_GRANTED"
    assert "EV001" in status_2020.supersession_chain

    # 3. As of today (post-2023): EV003 re-prohibited the FDC, superseding EV002
    status_today = engine.check_regulatory_status(
        ingredients=["Nimesulide", "Paracetamol"],
        as_of_date="2026-09-19"
    )
    assert status_today is not None
    assert status_today.event_id == "EV003"
    assert status_today.action == "PROHIBITED"
    assert status_today.notification_id == "GSR 411(E)"
    assert status_today.effective_date == "2023-06-15"
    assert "EV002" in status_today.supersession_chain

def test_paediatric_population_scoping():
    engine = RegulatoryEngine()

    # EV012: Ibuprofen + Paracetamol restricted in paediatric suspensions
    status_adult_tab = engine.check_regulatory_status(
        ingredients=["Ibuprofen", "Paracetamol"],
        dose_form="Tablet",
        is_paediatric=False
    )
    assert status_adult_tab is None # Adult tablets unaffected per EV012 note

    status_paed_susp = engine.check_regulatory_status(
        ingredients=["Ibuprofen", "Paracetamol"],
        dose_form="Suspension",
        is_paediatric=True
    )
    assert status_paed_susp is not None
    assert status_paed_susp.event_id == "EV012"
    assert status_paed_susp.action == "RESTRICTED"
    assert status_paed_susp.notification_id == "GSR 850(E)"
