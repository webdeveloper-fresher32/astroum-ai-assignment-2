"""
Deterministic Medication Safety Rail for BRAHMO Clinical AI.
Binding Laws:
- Law 4: Safety outside the LLM. Pure lookup/rules over versioned data. No model call anywhere.
- Law 5: Unknown is first-class. The status vocabulary is exactly:
  HIT · CHECKED_NO_HIT · PARTIAL_COVERAGE · UNVERIFIED_INPUT · NOT_CHECKED · DATA_EXPIRED · SOURCE_CONFLICT · SERVICE_UNAVAILABLE
- Law 7: Event-sourced regulatory status citation.
- Law 8: Everything versioned, everything replayable.
- Law 5 / Spec: Cumulative same-ingredient exposure across the whole prescription with aggregate evidence.
- Missing data must never render as "safe".
"""

import re
from typing import List, Dict, Tuple, Optional, Any, Set
from collections import defaultdict
from src.core.db import get_connection
from src.core.config import config
from src.core.types import (
    PrescriptionItem,
    PrescriptionSafetyReport,
    SafetyCheckFinding,
    SafetyVerdictState,
    NormalizedDrug,
    ReviewReasonCode
)
from src.module_a.normalizer import DrugNormalizer
from src.module_a.regulatory_engine import RegulatoryEngine

class DeterministicSafetyRail:
    def __init__(self, conn=None):
        self._conn = conn
        self.normalizer = DrugNormalizer(conn)
        self.regulatory_engine = RegulatoryEngine(conn)

    def _get_conn(self):
        return self._conn or get_connection()

    @staticmethod
    def parse_daily_frequency(freq_str: Optional[str]) -> Tuple[float, bool]:
        """
        Parses frequency string like '1-0-1 x 5d', '1-1-1', '0-0-1', '1-0-0', 'SOS'
        Returns (daily_multiplier, is_prn).
        """
        if not freq_str:
            return 1.0, False

        clean_freq = freq_str.strip().upper()
        if "SOS" in clean_freq or "PRN" in clean_freq:
            return 1.0, True

        # Check for standard Indian pattern like 1-0-1 or 1-1-1 or 0-0-1
        match = re.search(r'(\d+)\s*[-–]\s*(\d+)(?:\s*[-–]\s*(\d+))?(?:\s*[-–]\s*(\d+))?', clean_freq)
        if match:
            parts = [int(g) for g in match.groups() if g is not None]
            daily_doses = sum(parts)
            return float(daily_doses) if daily_doses > 0 else 1.0, False

        # Check for Latin abbreviations
        if re.search(r'\b(OD|ONCE DAILY|QD)\b', clean_freq):
            return 1.0, False
        if re.search(r'\b(BD|BID|TWICE DAILY)\b', clean_freq):
            return 2.0, False
        if re.search(r'\b(TDS|TID|THRICE DAILY)\b', clean_freq):
            return 3.0, False
        if re.search(r'\b(QID|FOUR TIMES DAILY)\b', clean_freq):
            return 4.0, False

        return 1.0, False

    def evaluate_prescription(
        self,
        rx_id: str,
        items: List[PrescriptionItem],
        patient_is_paediatric: bool = False
    ) -> PrescriptionSafetyReport:
        """
        Performs pure-lookup deterministic safety checks on a multi-item draft prescription.
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        findings: List[SafetyCheckFinding] = []
        normalized_items: List[Tuple[PrescriptionItem, NormalizedDrug]] = []
        unresolved_items: List[str] = []

        has_unverified = False
        has_partial = False

        # Step 1: Normalization & Ambiguity Check
        for item in items:
            norm = self.normalizer.normalize(
                raw_text=item.written_product,
                strength_as_written=item.strength_as_written,
                context_type="PRESCRIPTION_RAIL"
            )
            normalized_items.append((item, norm))

            if norm.confidence == 0.0 or norm.review_reason == ReviewReasonCode.UNRECOGNIZED_BRAND:
                has_unverified = True
                unresolved_items.append(item.written_product)
                findings.append(
                    SafetyCheckFinding(
                        check_type="DRUG_IDENTIFICATION",
                        state=SafetyVerdictState.UNVERIFIED_INPUT,
                        severity="CRITICAL",
                        evidence=f"Product '{item.written_product}' could not be verified in the national drug master or clinic formulary. Queued in review_queue (ID: {norm.review_queue_id}).",
                        rule_version=config.safety_rule_version,
                        data_version=config.cdci_source_version
                    )
                )
            elif norm.confidence < config.normalization_high_confidence_threshold:
                has_partial = True
                unresolved_items.append(item.written_product)
                findings.append(
                    SafetyCheckFinding(
                        check_type="DRUG_IDENTIFICATION",
                        state=SafetyVerdictState.PARTIAL_COVERAGE,
                        severity="WARNING",
                        evidence=f"Product '{item.written_product}' has ambiguous specification: {norm.review_reason.value if norm.review_reason else 'uncertain strength'}. Queued in review_queue (ID: {norm.review_queue_id}).",
                        rule_version=config.safety_rule_version,
                        data_version=config.cdci_source_version
                    )
                )

        # Step 2: Ingredient Decomposition & Cumulative Exposure Aggregation
        # Map: canonical_salt -> list of {product, single_dose_mg, daily_freq, daily_total_mg, is_prn}
        salt_exposures = defaultdict(list)

        for item, norm in normalized_items:
            daily_mult, is_prn = self.parse_daily_frequency(item.dose_frequency)

            for ing in norm.ingredients:
                salt_name = ing.ingredient_name.strip()
                unit = ing.strength_unit
                strength = ing.strength_value or 0.0
                daily_total = strength * daily_mult

                salt_exposures[salt_name.lower()].append({
                    "salt_display_name": salt_name,
                    "written_product": item.written_product,
                    "strength_per_dose": strength,
                    "strength_unit": unit,
                    "daily_multiplier": daily_mult,
                    "daily_total": daily_total,
                    "is_prn": is_prn,
                    "dose_frequency": item.dose_frequency or "Unspecified"
                })

        # Summarize cumulative exposures
        cumulative_exposures_summary = {}
        for salt_lower, exposures in salt_exposures.items():
            salt_display = exposures[0]["salt_display_name"]
            total_mg = sum(e["daily_total"] for e in exposures)
            contributing_brands = [e["written_product"] for e in exposures]
            cumulative_exposures_summary[salt_display] = {
                "total_daily_exposure_mg": total_mg,
                "contributing_products": contributing_brands,
                "exposure_details": exposures
            }

        # Check (a) Duplicate active ingredient & (d) Cumulative exposure across products
        for salt_lower, exposures in salt_exposures.items():
            salt_display = exposures[0]["salt_display_name"]
            if len(exposures) > 1:
                # Duplicate active ingredient HIT
                total_daily = sum(e["daily_total"] for e in exposures)
                breakdown = ", ".join(
                    [f"'{e['written_product']}' ({e['daily_total']:.1f} {e['strength_unit']}/day via {e['dose_frequency']})" for e in exposures]
                )
                evidence_text = (
                    f"Duplicate active ingredient '{salt_display}' prescribed across {len(exposures)} products: {breakdown}. "
                    f"Cumulative same-ingredient exposure: {total_daily:.1f} mg/day."
                )
                
                # Check against paracetamol ceiling
                severity = "CRITICAL"
                if salt_lower == "paracetamol":
                    if total_daily > config.paracetamol_max_daily_mg:
                        evidence_text += f" EXCEEDS adult recommended limit of {config.paracetamol_max_daily_mg:.0f} mg/day (hepatotoxicity danger)."
                    elif total_daily >= config.paracetamol_warning_daily_mg:
                        evidence_text += f" Nearing maximum adult safe limit of {config.paracetamol_max_daily_mg:.0f} mg/day."

                findings.append(
                    SafetyCheckFinding(
                        check_type="DUPLICATE_ACTIVE_INGREDIENT",
                        state=SafetyVerdictState.HIT,
                        severity=severity,
                        evidence=evidence_text,
                        rule_version=config.safety_rule_version,
                        data_version=config.cdci_source_version
                    )
                )

        # Check (b) Prohibited / Restricted FDC per event-sourced status
        for item, norm in normalized_items:
            ing_names = [i.ingredient_name for i in norm.ingredients]
            if ing_names:
                reg_status = self.regulatory_engine.check_regulatory_status(
                    ingredients=ing_names,
                    dose_form=norm.dose_form,
                    is_paediatric=patient_is_paediatric
                )
                if reg_status:
                    if reg_status.action == "PROHIBITED":
                        findings.append(
                            SafetyCheckFinding(
                                check_type="PROHIBITED_RESTRICTED_FDC",
                                state=SafetyVerdictState.HIT,
                                severity="CRITICAL",
                                evidence=f"Product '{item.written_product}' contains prohibited combination ({', '.join(ing_names)}). {reg_status.to_citation()}",
                                regulatory_citation=reg_status.notification_id,
                                effective_date=reg_status.effective_date,
                                rule_version=config.safety_rule_version,
                                data_version=config.regulatory_gazette_version
                            )
                        )
                    elif reg_status.action in ("RESTRICTED", "WITHDRAWN"):
                        findings.append(
                            SafetyCheckFinding(
                                check_type="PROHIBITED_RESTRICTED_FDC",
                                state=SafetyVerdictState.HIT,
                                severity="WARNING",
                                evidence=f"Product '{item.written_product}' is subject to regulatory restriction. {reg_status.to_citation()}",
                                regulatory_citation=reg_status.notification_id,
                                effective_date=reg_status.effective_date,
                                rule_version=config.safety_rule_version,
                                data_version=config.regulatory_gazette_version
                            )
                        )

        # Check (c) Severe Drug-Drug Interactions against seed list
        all_salts = list(salt_exposures.keys())
        for i in range(len(all_salts)):
            for j in range(i + 1, len(all_salts)):
                salt_a = all_salts[i]
                salt_b = all_salts[j]

                cursor.execute("""
                    SELECT ingredient_a, ingredient_b, severity, clinical_note, source_tag
                    FROM severe_interactions
                    WHERE (LOWER(ingredient_a) = ? AND LOWER(ingredient_b) = ?)
                       OR (LOWER(ingredient_a) = ? AND LOWER(ingredient_b) = ?)
                """, (salt_a, salt_b, salt_b, salt_a))
                match = cursor.fetchone()

                if match:
                    products_a = [e["written_product"] for e in salt_exposures[salt_a]]
                    products_b = [e["written_product"] for e in salt_exposures[salt_b]]
                    findings.append(
                        SafetyCheckFinding(
                            check_type="SEVERE_INTERACTION",
                            state=SafetyVerdictState.HIT,
                            severity=match["severity"],
                            evidence=(
                                f"Severe interaction between '{match['ingredient_a']}' ({', '.join(products_a)}) and "
                                f"'{match['ingredient_b']}' ({', '.join(products_b)}): {match['clinical_note']} "
                                f"(Source: {match['source_tag']})."
                            ),
                            rule_version=config.safety_rule_version,
                            data_version=match["source_tag"]
                        )
                    )

        # Determine overall prescription state according to Law 5
        hit_findings = [f for f in findings if f.state == SafetyVerdictState.HIT]
        if hit_findings:
            overall_state = SafetyVerdictState.HIT
        elif has_unverified:
            overall_state = SafetyVerdictState.UNVERIFIED_INPUT
        elif has_partial:
            overall_state = SafetyVerdictState.PARTIAL_COVERAGE
        else:
            overall_state = SafetyVerdictState.CHECKED_NO_HIT
            findings.append(
                SafetyCheckFinding(
                    check_type="FULL_SAFETY_PASS",
                    state=SafetyVerdictState.CHECKED_NO_HIT,
                    severity="INFO",
                    evidence="All prescribed products verified and passed duplicate-salt, prohibited-FDC, and severe-interaction checks.",
                    rule_version=config.safety_rule_version,
                    data_version=f"{config.cdci_source_version}+{config.regulatory_gazette_version}"
                )
            )

        return PrescriptionSafetyReport(
            rx_id=rx_id,
            overall_state=overall_state,
            findings=findings,
            cumulative_exposures=cumulative_exposures_summary,
            unresolved_items=unresolved_items,
            data_versions={
                "cdci": config.cdci_source_version,
                "regulatory": config.regulatory_gazette_version,
                "load_batch": config.load_batch_id
            },
            rule_versions={
                "safety_engine": config.safety_rule_version
            }
        )
