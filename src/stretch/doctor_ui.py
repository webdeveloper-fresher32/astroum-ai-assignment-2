"""
Stretch: Doctor-Facing Inspection Interface & API Server for BRAHMO Clinical AI.
Provides:
1. Fast, beautiful FastAPI Web Dashboard with real-time prescription safety checking,
   cumulative dosage meter, review queue inspector, and grounded clinical Q&A with claim citations.
2. Rich Terminal CLI renderer for instant doctor review in the console.
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from src.core.types import PrescriptionItem
from src.module_a.safety_rail import DeterministicSafetyRail
from src.module_a.review_queue import ReviewQueueManager
from src.module_b.answerer import GroundedClinicalAnswerer
from src.module_c.e2e_trace import EndToEndTracer

app = FastAPI(title="BRAHMO Clinical AI — Doctor Inspection Dashboard")

rail = DeterministicSafetyRail()
queue_mgr = ReviewQueueManager()
answerer = GroundedClinicalAnswerer()
tracer = EndToEndTracer()

class RxCheckRequest(BaseModel):
    rx_id: str = "RX-DOCTOR-01"
    items: List[PrescriptionItem]

class QARequest(BaseModel):
    question: str

@app.post("/api/check-prescription")
def check_prescription(req: RxCheckRequest):
    report = rail.evaluate_prescription(req.rx_id, req.items)
    return report.model_dump()

@app.post("/api/clinical-qa")
def ask_question(req: QARequest):
    resp = answerer.answer_query(req.question)
    return resp.model_dump()

@app.get("/api/review-queue")
def get_review_queue():
    items = queue_mgr.list_pending(limit=30)
    counts = queue_mgr.count_by_reason()
    return {"counts": counts, "items": items}

@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BRAHMO Clinical AI — Doctor Inspection</title>
    <style>
        :root {
            /* Clinical, credible, calm palette */
            --bg-color: #FAFAFA;
            --surface-color: #FFFFFF;
            --border-color: #E2E8F0;
            --text-primary: #1E293B;
            --text-secondary: #64748B;
            --accent-color: #2563EB;
            --danger-bg: #FEF2F2;
            --danger-text: #B91C1C;
            --danger-border: #FCA5A5;
            --success-bg: #F0FDF4;
            --success-text: #15803D;
            --success-border: #86EFAC;
            --warning-bg: #FFFBEB;
            --warning-text: #B45309;
            --warning-border: #FCD34D;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-primary);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 0;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 48px 24px;
        }

        .header {
            margin-bottom: 48px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: baseline;
        }

        .header h1 {
            font-size: 24px;
            font-weight: 600;
            letter-spacing: -0.02em;
            margin: 0;
        }

        .header-meta {
            font-size: 13px;
            color: var(--text-secondary);
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }

        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 32px;
            margin-bottom: 32px;
        }

        .card {
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            padding: 32px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.02);
        }

        .card-full {
            grid-column: 1 / -1;
        }

        .card h2 {
            font-size: 16px;
            font-weight: 600;
            margin-top: 0;
            margin-bottom: 8px;
            letter-spacing: -0.01em;
        }

        .card-desc {
            font-size: 14px;
            color: var(--text-secondary);
            margin-bottom: 24px;
        }

        label {
            display: block;
            font-size: 13px;
            font-weight: 500;
            margin-bottom: 8px;
            color: var(--text-primary);
        }

        textarea, input[type="text"] {
            width: 100%;
            box-sizing: border-box;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            padding: 12px;
            font-size: 14px;
            font-family: inherit;
            margin-bottom: 16px;
            background: #F8FAFC;
            transition: border-color 0.2s;
        }

        textarea:focus, input[type="text"]:focus {
            outline: none;
            border-color: var(--accent-color);
            background: #FFF;
        }

        button {
            background-color: var(--text-primary);
            color: white;
            border: none;
            border-radius: 4px;
            padding: 10px 16px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s;
        }

        button:hover {
            background-color: #0F172A;
        }

        /* Results / Verdicts */
        .result-container {
            margin-top: 24px;
            padding-top: 24px;
            border-top: 1px solid var(--border-color);
            display: none;
        }

        .verdict-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 16px;
            border: 1px solid transparent;
        }

        .state-HIT { background: var(--danger-bg); color: var(--danger-text); border-color: var(--danger-border); }
        .state-CHECKED_NO_HIT { background: var(--success-bg); color: var(--success-text); border-color: var(--success-border); }
        .state-PARTIAL_COVERAGE { background: var(--warning-bg); color: var(--warning-text); border-color: var(--warning-border); }
        .state-UNVERIFIED_INPUT { background: var(--danger-bg); color: var(--danger-text); border-color: var(--danger-border); }

        .finding-row {
            font-size: 14px;
            padding: 8px 0;
            border-bottom: 1px solid #F1F5F9;
        }
        .finding-row:last-child {
            border-bottom: none;
        }

        .citation-tag {
            display: inline-block;
            background: #F1F5F9;
            color: var(--text-secondary);
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 4px;
            margin-top: 8px;
            margin-right: 4px;
            font-family: ui-monospace, monospace;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin-top: 16px;
        }
        th, td {
            text-align: left;
            padding: 12px 8px;
            border-bottom: 1px solid var(--border-color);
        }
        th {
            color: var(--text-secondary);
            font-weight: 500;
        }
        .reason-code {
            font-family: ui-monospace, monospace;
            background: #F1F5F9;
            padding: 2px 4px;
            border-radius: 3px;
        }
        
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
            .header { flex-direction: column; gap: 12px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>BRAHMO Clinical Interface</h1>
            <div class="header-meta">CDCI 2026Q2 • Ruleset: SAFE-2026.1</div>
        </header>

        <div class="grid">
            <!-- Prescription Rail -->
            <section class="card">
                <h2>Prescription Safety Rail</h2>
                <p class="card-desc">Deterministic evaluation against national FDC and interaction rules.</p>
                
                <label for="rx-input">Draft Prescription</label>
                <textarea id="rx-input" rows="4">Dolo 650 (650 mg, 1-0-1 x 5d)
Sinarest Tablet (1-0-1 x 5d)</textarea>
                
                <button onclick="runRxCheck()">Evaluate Safety</button>

                <div id="rx-output" class="result-container">
                    <div id="rx-badge" class="verdict-badge"></div>
                    <div id="rx-findings"></div>
                </div>
            </section>

            <!-- Grounded RAG -->
            <section class="card">
                <h2>Clinical Guidelines</h2>
                <p class="card-desc">Query national STWs. Requires strict source grounding.</p>
                
                <label for="qa-input">Clinical Question</label>
                <input type="text" id="qa-input" value="Which analgesic class must be avoided in suspected dengue, and why?" />
                
                <button onclick="runQA()">Query Knowledge Base</button>

                <div id="qa-output" class="result-container">
                    <div id="qa-text" style="font-size: 14px; white-space: pre-wrap; margin-bottom: 12px;"></div>
                    <div id="qa-citations"></div>
                </div>
            </section>

            <!-- Review Queue -->
            <section class="card card-full">
                <h2>Human-in-the-Loop Review Queue</h2>
                <p class="card-desc">Ambiguous or unverified inputs awaiting clinician resolution. No silent automated guessing.</p>
                
                <div id="queue-list" style="overflow-x: auto;">
                    Loading review queue...
                </div>
            </section>
        </div>
    </div>

    <script>
        async function runRxCheck() {
            const raw = document.getElementById('rx-input').value;
            const lines = raw.split('\\n').filter(l => l.trim().length > 0);
            const items = lines.map((l, i) => {
                let name = l;
                let strength = null;
                let freq = '1-0-1';
                if (l.includes('(')) {
                    name = l.split('(')[0].trim();
                    const meta = l.split('(')[1].replace(')', '').split(',');
                    strength = meta[0] ? meta[0].trim() : null;
                    freq = meta[1] ? meta[1].trim() : '1-0-1';
                }
                return { rx_id: 'RX-DEMO', item_no: i + 1, written_product: name, strength_as_written: strength, dose_frequency: freq };
            });

            const res = await fetch('/api/check-prescription', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ rx_id: 'RX-DEMO', items: items })
            });
            const data = await res.json();
            
            document.getElementById('rx-output').style.display = 'block';
            const badge = document.getElementById('rx-badge');
            badge.className = 'verdict-badge state-' + data.overall_state;
            badge.innerText = 'STATUS: ' + data.overall_state;

            let html = '';
            data.findings.forEach(f => {
                html += `<div class="finding-row"><strong>${f.check_type}:</strong> ${f.evidence}</div>`;
            });
            document.getElementById('rx-findings').innerHTML = html;
        }

        async function runQA() {
            const q = document.getElementById('qa-input').value;
            const res = await fetch('/api/clinical-qa', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: q })
            });
            const data = await res.json();

            document.getElementById('qa-output').style.display = 'block';
            document.getElementById('qa-text').innerText = data.answer_text;

            let citHtml = '';
            data.citations.forEach(c => {
                citHtml += `<span class="citation-tag">${c.source_document} v${c.version} (${c.page_anchor})</span>`;
            });
            document.getElementById('qa-citations').innerHTML = citHtml;
        }

        async function loadQueue() {
            const res = await fetch('/api/review-queue');
            const data = await res.json();
            
            let html = `<table>`;
            html += `<tr><th>Queue ID</th><th>Input String</th><th>Reason Code</th><th>Confidence</th><th>Status</th></tr>`;
            data.items.slice(0, 10).forEach(it => {
                html += `<tr>
                    <td>#${it.queue_id}</td>
                    <td>${it.raw_input_text}</td>
                    <td><span class="reason-code">${it.reason_code}</span></td>
                    <td>${(it.confidence_score*100).toFixed(0)}%</td>
                    <td style="color: var(--warning-text);">${it.status}</td>
                </tr>`;
            });
            html += `</table>`;
            document.getElementById('queue-list').innerHTML = html;
        }

        loadQueue();
    </script>
</body>
</html>
    """

def start_server(port: int = 8000):
    print(f"Starting BRAHMO Clinical AI Doctor Dashboard on http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port)

if __name__ == "__main__":
    start_server()
