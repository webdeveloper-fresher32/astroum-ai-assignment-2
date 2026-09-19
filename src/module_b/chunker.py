"""
Clinical Decision-Unit Chunker for BRAHMO Clinical AI.
Law 8 & Module B Spec:
Chunks documents into clinically meaningful decision units (recommendation, workflow step, contraindication, red flag)
NEVER blind token slices.
Preserves rich metadata: source code, version, effective date, supersession, specialty, condition, page anchor.
"""

import re
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from src.core.config import config

class DecisionUnit(BaseModel):
    unit_id: str
    document_code: str
    title: str
    condition: str
    specialty: str
    version: str
    effective_date: str
    section_title: str
    unit_type: str # 'FIRST_LINE_RECOMMENDATION', 'CONTRAINDICATION', 'RED_FLAG_REFERRAL', 'DIAGNOSTIC_CRITERIA', 'MONITORING_FOLLOWUP'
    content_text: str
    consequential_numbers: List[str] = Field(default_factory=list)
    page_anchor: str = "p.1"
    is_superseded: bool = False
    superseded_by: Optional[str] = None
    is_clinic_internal: bool = False
    citation_tag: str

class ClinicalChunker:
    """
    Parses STW PDFs and clinic SOPs into semantic, clinically meaningful decision units.
    """
    
    KNOWN_SECTION_HEADERS = [
        "ASSESS",
        "ASSESS DEHYDRATION",
        "AVOID",
        "CLASSIFY",
        "CONFIRM",
        "COUNSEL",
        "DIAGNOSE",
        "DO NOT",
        "FIRST-LINE MANAGEMENT",
        "FIRST-LINE MANAGEMENT (CURRENT)",
        "FIRST-LINE MANAGEMENT (THIS 2021 EDITION)",
        "FOLLOW-UP",
        "MONITOR",
        "OPD MANAGEMENT",
        "RED FLAGS — IMAGE/REFER",
        "RED FLAGS — REFER",
        "REFER",
        "REVIEW",
        "SCREEN",
        "STATUS",
        "SUSPECT",
        "TARGETS",
        "WARNING SIGNS — ADMIT"
    ]

    @staticmethod
    def extract_text_from_pdf(pdf_path: Path) -> str:
        try:
            res = subprocess.run(["pdftotext", str(pdf_path), "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return res.stdout
        except Exception:
            return ""

    @classmethod
    def parse_pdf_document(cls, pdf_path: Path) -> List[DecisionUnit]:
        raw_text = cls.extract_text_from_pdf(pdf_path)
        if not raw_text:
            return []

        # Parse header metadata
        doc_code_match = re.search(r"Code:\s*([A-Z0-9\-]+)", raw_text)
        version_match = re.search(r"Version:\s*([0-9\.]+)", raw_text)
        effective_match = re.search(r"Effective:\s*([0-9\-]+)", raw_text)
        supersedes_match = re.search(r"Supersedes:\s*([A-Z0-9\-\.\s]+)", raw_text, re.IGNORECASE)
        superseded_by_match = re.search(r"superseded by\s*([A-Z0-9\-\.\sv]+)", raw_text, re.IGNORECASE)

        doc_code = doc_code_match.group(1) if doc_code_match else pdf_path.stem
        version = version_match.group(1) if version_match else "1.0"
        effective_date = effective_match.group(1) if effective_match else "2024-01-01"
        is_superseded = "ARCHIVE COPY" in raw_text or bool(superseded_by_match)
        superseded_by = superseded_by_match.group(1).strip() if superseded_by_match else None

        # Determine Title, Condition & Specialty
        lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
        title = ""
        for idx, line in enumerate(lines[:8]):
            if "STANDARD TREATMENT WORKFLOW" not in line and "Code:" not in line and "Version:" not in line:
                if len(line) > 5 and not line.startswith("•") and not line.startswith("Effective:"):
                    title = line
                    break

        if "—" in title:
            condition_part, specialty_part = title.split("—", 1)
            condition = condition_part.strip()
            specialty = specialty_part.strip()
        elif "-" in title:
            condition_part, specialty_part = title.split("-", 1)
            condition = condition_part.strip()
            specialty = specialty_part.strip()
        else:
            condition = title
            specialty = "General"

        if "PED" in doc_code:
            specialty = "Pediatrics"
        elif "GYN" in doc_code:
            specialty = "Gynaecology & Obstetrics"
        elif "ORT" in doc_code:
            specialty = "Orthopaedics"
        elif "GP" in doc_code:
            specialty = "General Practice"

        # Locate section headings and their positions
        header_positions = []
        for h in cls.KNOWN_SECTION_HEADERS:
            # Look for header as standalone line
            pattern = re.compile(rf"^(?:•\s*)?{re.escape(h)}\s*$", re.MULTILINE)
            for m in pattern.finditer(raw_text):
                header_positions.append((m.start(), m.end(), h))

        # Sort by position
        header_positions.sort(key=lambda x: x[0])

        decision_units = []
        for i, (start, end, header) in enumerate(header_positions):
            next_start = header_positions[i + 1][0] if i + 1 < len(header_positions) else len(raw_text)
            body = raw_text[end:next_start].strip()

            # Clean out footer notice
            body = re.sub(r"SYNTHETIC ASSESSMENT DOCUMENT.*", "", body, flags=re.DOTALL).strip()
            body = re.sub(r"Supersedes:.*", "", body, flags=re.DOTALL).strip()

            if not body:
                continue

            # Determine Unit Type
            header_upper = header.upper()
            if "DO NOT" in header_upper or "AVOID" in header_upper:
                unit_type = "CONTRAINDICATION"
            elif "RED FLAGS" in header_upper or "WARNING SIGNS" in header_upper or "REFER" in header_upper:
                unit_type = "RED_FLAG_REFERRAL"
            elif "FIRST-LINE" in header_upper or "OPD MANAGEMENT" in header_upper:
                unit_type = "FIRST_LINE_RECOMMENDATION"
            elif any(k in header_upper for k in ["DIAGNOSE", "CLASSIFY", "ASSESS", "CONFIRM", "SCREEN", "SUSPECT"]):
                unit_type = "DIAGNOSTIC_CRITERIA"
            elif any(k in header_upper for k in ["MONITOR", "REVIEW", "FOLLOW-UP", "TARGETS"]):
                unit_type = "MONITORING_FOLLOWUP"
            else:
                unit_type = "CLINICAL_WORKFLOW_STEP"

            # Extract numbers/dosages
            numbers = re.findall(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|kg|h|hours|days|weeks|months|years|y|%|elements)\b", body, re.IGNORECASE)

            unit_id = f"{doc_code}-{re.sub(r'[^A-Za-z0-9]', '_', header)[:20]}-{i+1}"
            citation_tag = f"[{doc_code} v{version}: {header}, p.1]"

            decision_units.append(
                DecisionUnit(
                    unit_id=unit_id,
                    document_code=doc_code,
                    title=title,
                    condition=condition,
                    specialty=specialty,
                    version=version,
                    effective_date=effective_date,
                    section_title=header,
                    unit_type=unit_type,
                    content_text=body,
                    consequential_numbers=numbers,
                    page_anchor="p.1",
                    is_superseded=is_superseded,
                    superseded_by=superseded_by,
                    is_clinic_internal=False,
                    citation_tag=citation_tag
                )
            )

        return decision_units

    @classmethod
    def parse_local_protocol(cls, md_path: Path) -> List[DecisionUnit]:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        units = []
        doc_code = "SUNRISE-SOP-CLIN-014"
        version = "2.1"
        effective_date = "2026-03-10"

        # Split steps
        steps = re.findall(r"(\d+\.\s+.*?)(?=(?:\n\d+\.|\n\*Internal|$))", content, re.DOTALL)
        for idx, step in enumerate(steps, start=1):
            clean_step = step.strip()
            sec_title = f"Step {idx}"
            unit_type = "LOCAL_CLINIC_PROTOCOL_STEP"
            if idx == 2 and "Azithromycin" in clean_step:
                sec_title = "Step 2: Empirical Antibiotic Rule (>48h Persistent Fever)"
                unit_type = "FIRST_LINE_RECOMMENDATION"

            numbers = re.findall(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|kg|h|hours|days|weeks|y|%)\b", clean_step, re.IGNORECASE)

            units.append(
                DecisionUnit(
                    unit_id=f"{doc_code}-STEP-{idx}",
                    document_code=doc_code,
                    title="Sunrise Multi-speciality Clinic — Adult Acute Undifferentiated Fever",
                    condition="Adult Acute Undifferentiated Fever",
                    specialty="Internal Clinic Protocol (Sunrise OPD)",
                    version=version,
                    effective_date=effective_date,
                    section_title=sec_title,
                    unit_type=unit_type,
                    content_text=clean_step,
                    consequential_numbers=numbers,
                    page_anchor="p.1",
                    is_superseded=False,
                    is_clinic_internal=True,
                    citation_tag=f"[{doc_code} v{version} (Internal Clinic Protocol): {sec_title}, p.1]"
                )
            )

        return units

    @classmethod
    def load_entire_corpus(cls) -> List[DecisionUnit]:
        corpus_dir = config.corpus_dir
        if not corpus_dir.exists():
            corpus_dir = config.base_dir / "corpus"

        units = []
        for pdf_file in sorted(corpus_dir.glob("STW_*.pdf")):
            units.extend(cls.parse_pdf_document(pdf_file))

        local_md = config.data_dir / "local_protocol_acute_fever.md"
        if not local_md.exists():
            local_md = config.base_dir / "local_protocol_acute_fever.md"

        if local_md.exists():
            units.extend(cls.parse_local_protocol(local_md))

        return units
