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
    <title>BRAHMO Clinical AI — Doctor Safety & Grounding Dashboard</title>
    <style>
        :root {
            --bg: #0b0f19;
            --surface: #151c2e;
            --surface-border: #232f48;
            --text: #f0f4fc;
            --text-muted: #8c9eb5;
            --primary: #3b82f6;
            --danger: #ef4444;
            --warning: #f59e0b;
            --success: #10b981;
            --accent: #8b5cf6;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: var(--bg); color: var(--text); padding: 24px; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--surface-border); padding-bottom: 16px; margin-bottom: 24px; }
        .header h1 { font-size: 22px; font-weight: 700; color: #fff; }
        .header .badge { background: #1e293b; color: var(--primary); padding: 6px 12px; border-radius: 9999px; font-size: 13px; font-weight: 600; border: 1px solid var(--surface-border); }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
        .card { background: var(--surface); border: 1px solid var(--surface-border); border-radius: 12px; padding: 20px; }
        .card h2 { font-size: 16px; font-weight: 600; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }
        textarea, input, select { width: 100%; background: #0f1523; border: 1px solid var(--surface-border); color: #fff; padding: 10px; border-radius: 8px; margin-bottom: 12px; font-size: 14px; }
        button { background: var(--primary); color: #fff; border: none; padding: 10px 18px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: 0.2s; }
        button:hover { opacity: 0.9; }
        .verdict-box { margin-top: 14px; padding: 14px; border-radius: 8px; background: #0f1523; border: 1px solid var(--surface-border); }
        .verdict-badge { display: inline-block; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 13px; margin-bottom: 10px; }
        .state-HIT { background: #ef444422; color: var(--danger); border: 1px solid var(--danger); }
        .state-CHECKED_NO_HIT { background: #10b98122; color: var(--success); border: 1px solid var(--success); }
        .state-UNVERIFIED_INPUT { background: #ef444422; color: var(--danger); border: 1px solid var(--danger); }
        .state-PARTIAL_COVERAGE { background: #f59e0b22; color: var(--warning); border: 1px solid var(--warning); }
        .finding-item { font-size: 13px; margin-bottom: 8px; line-height: 1.5; color: #cbd5e1; }
        .citation-tag { display: inline-block; background: #1e293b; color: #93c5fd; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-top: 6px; }
        .full-width { grid-column: span 2; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>BRAHMO Clinical AI — Doctor Inspection Surface</h1>
            <p style="color: var(--text-muted); font-size: 13px; margin-top: 4px;">Deterministic Safety Rail (Pure Lookup) & Grounded Clinical RAG with ICMR Citations</p>
        </div>
        <div class="badge">Rule: RULES-SAFE-2026.1 · CDCI 2026Q2 · 8-State Mandate</div>
    </div>

    <div class="grid">
        <!-- Module A: Prescription Safety Rail -->
        <div class="card">
            <h2>🛡️ Prescription Safety Rail (Module A)</h2>
            <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 10px;">Test multi-item prescriptions for duplicate active ingredients, prohibited FDCs, and severe interactions.</p>
            <textarea id="rx-input" rows="4">Dolo 650 (650 mg, 1-0-1 x 5d)
Sinarest Tablet (1-0-1 x 5d)</textarea>
            <button onclick="runRxCheck()">Check Medication Safety</button>

            <div id="rx-output" class="verdict-box" style="display:none;">
                <div id="rx-badge" class="verdict-badge"></div>
                <div id="rx-findings"></div>
            </div>
        </div>

        <!-- Module B: Grounded Clinical Q&A -->
        <div class="card">
            <h2>📚 Grounded Clinical Assistant (Module B)</h2>
            <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 10px;">Ask clinical guideline questions grounded strictly in the 13 ICMR STWs & local protocol.</p>
            <input type="text" id="qa-input" value="Which analgesic class must be avoided in suspected dengue, and why?" />
            <button onclick="runQA()">Query Clinical Guidelines</button>

            <div id="qa-output" class="verdict-box" style="display:none;">
                <div id="qa-text" style="font-size: 13px; line-height: 1.6; white-space: pre-wrap;"></div>
                <div id="qa-citations" style="margin-top: 10px;"></div>
            </div>
        </div>

        <!-- Ambiguity Review Queue -->
        <div class="card full-width">
            <h2>🔍 Ambiguity Review Queue (Law 6: Zero Silent Guessing)</h2>
            <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 12px;">Uncertain or unrecognized drugs are never silently auto-resolved. They are queued here with structured reason codes.</p>
            <div id="queue-list" style="font-size: 13px; max-height: 250px; overflow-y: auto;">
                Loading review queue...
            </div>
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
            badge.innerText = 'VERDICT: ' + data.overall_state;

            let html = '';
            data.findings.forEach(f => {
                html += `<div class="finding-item"><b>[${f.state}] ${f.check_type}:</b> ${f.evidence}</div>`;
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
                citHtml += `<div class="citation-tag">📌 ${c.source_document} v${c.version}: ${c.section_title} (${c.page_anchor})</div> `;
            });
            document.getElementById('qa-citations').innerHTML = citHtml;
        }

        async function loadQueue() {
            const res = await fetch('/api/review-queue');
            const data = await res.json();
            let html = `<div style="margin-bottom: 10px;"><b>Pending Reason Summary:</b> `;
            for (const [k, v] of Object.entries(data.counts)) {
                html += `<span style="background:#1e293b; padding:3px 8px; border-radius:4px; margin-right:8px;">${k}: ${v}</span>`;
            }
            html += `</div><table style="width:100%; border-collapse: collapse; text-align:left; font-size:12px;">`;
            html += `<tr style="border-bottom:1px solid var(--surface-border); color:var(--text-muted);"><th style="padding:6px;">ID</th><th>Raw Text</th><th>Reason Code</th><th>Confidence</th><th>Status</th></tr>`;
            data.items.slice(0, 10).forEach(it => {
                html += `<tr style="border-bottom:1px solid #1a2234;"><td style="padding:6px;">#${it.queue_id}</td><td>${it.raw_input_text}</td><td><code>${it.reason_code}</code></td><td>${(it.confidence_score*100).toFixed(0)}%</td><td><span style="color:var(--warning);">${it.status}</span></td></tr>`;
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
