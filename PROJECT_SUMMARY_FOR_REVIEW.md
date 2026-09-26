# BRAHMO Clinical AI: Project Summary & Review Guide

This document is for your personal review before the live defense. It summarizes exactly what this assignment is, what you have built, and the core engineering philosophy behind it.

## 1. What is the Assignment?
**The Goal:** Astroum AI is building "BRAHMO", a clinical AI for Indian doctors. The challenge is that LLMs (like ChatGPT) hallucinate medical facts and guess dosages, which is dangerous and illegal. 

You were tasked with building the foundation of an AI that is:
1. **Patient-aware & Grounded:** It only answers medical questions based on approved Indian medical guidelines (the provided PDFs) and never makes up facts.
2. **Deterministic & Safe:** The medication safety checks (checking for drug interactions, banned drugs, and overdoses) are done using strict, traditional code (lookups and math)—**NOT by an LLM**. The AI is not allowed to guess if a drug is safe.

## 2. What Have You Built? (The Architecture)
You have built a local, fully working backend system using Python and SQLite. The system is split into three main modules:

### Module A: The Drug Master & Deterministic Safety Rail
This is the **non-AI**, strict safety system.
* **Drug Master & Normalization:** You take messy data (Indian brand names, pharmacy stock) and map them to their actual chemical salts (Fixed-Dose Combinations or FDCs). For example, if a doctor prescribes "Calpol", the system knows it is exactly "Paracetamol 500mg".
* **The Safety Rail:** When a doctor writes a draft prescription, this system runs strict rules:
  - **Duplicate Ingredients:** Checks if two different brands contain the same salt, causing an accidental overdose (e.g., prescribing Calpol and Dolo together).
  - **Prohibited Drugs:** Checks if the drug is banned based on official Indian regulatory gazette events.
  - **Severe Interactions:** Checks if Drug A reacts badly with Drug B.
* *Crucial Rule:* This module uses ZERO AI. It is pure database lookups. Missing data is never treated as "safe"; it is flagged as `UNVERIFIED_INPUT`.

### Module B: The Grounded RAG (Retrieval-Augmented Generation)
This is the **AI** part, used to answer the doctor's clinical questions.
* **Chunking & Retrieval:** It breaks down the provided PDF guidelines (Standard Treatment Workflows) into clinical decision units.
* **Grounded Answering:** When the doctor asks a question, the system searches the PDFs and answers using *only* the text from the PDFs. 
* *Crucial Rule:* Every medical fact or number must have a citation linking back to the PDF. If the PDF doesn't contain the answer, the AI must explicitly say "I don't know" (honest abstention). It is never allowed to calculate a patient-specific dose.

### Module C: The End-to-End Trace
This is a single script that ties Module A and Module B together. It takes a draft prescription and a doctor's question, runs the safety rail, runs the RAG answer, and outputs a single JSON file with 100% data provenance (tracking exactly which dataset versions and prompts were used).

## 3. The Core Engineering Principles You Used
During your defense, if they ask why you did something a certain way, lean on these principles:
* **Zero Silent Resolutions:** If the system is unsure about a drug's strength or name, it doesn't guess. It pushes it to a human `review_queue`.
* **Data Provenance:** Every database row has a `source_name` and `effective_date`. If a doctor asks why a drug was flagged, the system can point to the exact source and date.
* **Cost & Speed:** The system uses a local SQLite database and avoids unnecessary external API calls for strict logic, making it fast and reproducible.

## 4. Summary of Your Written Deliverables
You aren't just submitting code; you are submitting an "Architect's Blueprint".
* **`DESIGN.md`:** Explains *why* you built it this way (your architecture decisions and the alternatives you rejected).
* **`SCALE.md`:** Explains how you would upgrade this codebase if 100 doctors were using it simultaneously (e.g., migrating from SQLite to PostgreSQL, adding Redis for caching).
* **`PART_2_PRODUCTION_PLAN.md`:** A realistic 4-week roadmap of how a team would take this prototype and turn it into a production-ready system for a live trial.
* **`GAPS_REGISTER.md`:** A mature reflection on the messy parts of the provided data and what is missing in the real world.
* **`DAY_2_QA.md`:** Your 5 highly strategic questions you "asked" the interviewers to clarify ambiguities.

## Your Mindset for the Defense
You are a **Senior/Staff Engineer**. You built a robust, deterministic safety net combined with a tightly constrained AI. You prioritize patient safety and data traceability over flashy AI features. 
Read through your `DESIGN.md` and this summary, and you will be fully prepared to explain your system!
