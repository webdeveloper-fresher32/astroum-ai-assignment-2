"""
Seed Prescriptions Demonstration Runner for BRAHMO Clinical AI.
Evaluates all 10 seed prescriptions from seed_prescriptions_template.csv.
Fulfills Gate G4 (zero false negatives, unknowns rendered as unknowns, cumulative dosing demonstrated).
Outputs completed seed prescriptions to output/completed_seed_prescriptions.csv and console report.
"""

import csv
from pathlib import Path
from collections import defaultdict
from src.core.config import config
from src.core.types import PrescriptionItem
from src.module_a.safety_rail import DeterministicSafetyRail

def run_seed_evaluation():
    template_path = config.data_dir / "seed_prescriptions_template.csv"
    if not template_path.exists():
        template_path = config.base_dir / "seed_prescriptions_template.csv"

    out_dir = config.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "completed_seed_prescriptions.csv"

    print(f"Reading template from {template_path}...")
    with open(template_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Group items by prescription ID
    rx_items_map = defaultdict(list)
    for r in rows:
        rx_items_map[r["rx_id"]].append(
            PrescriptionItem(
                rx_id=r["rx_id"],
                item_no=int(r["item_no"]),
                written_product=r["written_product"],
                strength_as_written=r.get("strength_as_written") or None,
                dose_frequency=r.get("dose_frequency") or None,
                clinical_note=r.get("clinical_note") or None
            )
        )

    rail = DeterministicSafetyRail()
    rx_reports = {}

    print("\n" + "="*80)
    print("BRAHMO DETERMINISTIC SAFETY RAIL — SEED EVALUATION REPORT")
    print("="*80)

    for rx_id, items in rx_items_map.items():
        report = rail.evaluate_prescription(rx_id, items)
        rx_reports[rx_id] = report

        print(f"\nPrescription {rx_id}: Overall State -> [{report.overall_state.value}]")
        print(f"Items: {', '.join([it.written_product for it in items])}")
        for f in report.findings:
            print(f"  - [{f.state.value}] {f.check_type}: {f.evidence}")

    # Write completed CSV
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "rx_id", "item_no", "written_product", "strength_as_written",
            "dose_frequency", "clinical_note", "candidate_rail_output_state",
            "candidate_evidence_note"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in rows:
            rx_id = r["rx_id"]
            report = rx_reports[rx_id]
            state = report.overall_state.value
            
            # Formulate concise evidence note for this item
            item_product = r["written_product"]
            relevant_findings = [
                f.evidence for f in report.findings 
                if item_product.lower() in f.evidence.lower() or f.check_type in ("DUPLICATE_ACTIVE_INGREDIENT", "SEVERE_INTERACTION", "FULL_SAFETY_PASS")
            ]
            evidence_str = " | ".join(relevant_findings) if relevant_findings else report.findings[0].evidence

            writer.writerow({
                "rx_id": r["rx_id"],
                "item_no": r["item_no"],
                "written_product": r["written_product"],
                "strength_as_written": r.get("strength_as_written", ""),
                "dose_frequency": r.get("dose_frequency", ""),
                "clinical_note": r.get("clinical_note", ""),
                "candidate_rail_output_state": state,
                "candidate_evidence_note": evidence_str
            })

    print(f"\nCompleted CSV written to {out_csv}")
    print("="*80)

if __name__ == "__main__":
    run_seed_evaluation()
