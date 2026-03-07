from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os
import json

from orchestration.supervisor import Supervisor

app = FastAPI(title="Fez Exchange Agent API", description="University exchange recommendation AI agent")
agent = Supervisor()

# --- WEB UI ---
UI_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fez Exchange Agent</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 24px; background: #0f172a; color: #e2e8f0; }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { font-size: 1.5rem; margin-bottom: 8px; }
        .subtitle { color: #94a3b8; font-size: 0.9rem; margin-bottom: 24px; }
        label { display: block; font-weight: 500; margin-bottom: 8px; color: #cbd5e1; }
        textarea { width: 100%; min-height: 160px; padding: 12px; border-radius: 8px; border: 1px solid #334155; background: #1e293b; color: #e2e8f0; font-family: monospace; font-size: 13px; resize: vertical; }
        textarea:focus { outline: none; border-color: #3b82f6; }
        button { padding: 10px 20px; border-radius: 8px; border: none; background: #3b82f6; color: white; font-weight: 600; cursor: pointer; font-size: 14px; }
        button:hover { background: #2563eb; }
        button:disabled { opacity: 0.6; cursor: not-allowed; }
        .output { margin-top: 24px; padding: 20px; border-radius: 8px; background: #1e293b; border: 1px solid #334155; }
        .response { white-space: pre-wrap; word-break: break-word; margin-bottom: 20px; }
        .steps { margin-top: 16px; }
        .step { padding: 12px; margin-bottom: 8px; border-radius: 6px; background: #0f172a; border-left: 3px solid #3b82f6; }
        .step-module { font-weight: 600; color: #60a5fa; margin-bottom: 6px; }
        .step pre { margin: 0; font-size: 12px; color: #94a3b8; overflow-x: auto; white-space: pre-wrap; }
        .error { color: #f87171; }
        .success { color: #34d399; }
        .loading { color: #94a3b8; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Fez Exchange Agent</h1>
        <p class="subtitle">Enter a JSON profile or a follow-up message. Click Run Agent to get university recommendations.</p>
        <label for="prompt">Prompt (JSON profile or chat message)</label>
        <textarea id="prompt" placeholder='{"academic_profile":{"gpa":85,"major":"Computer Science"},"preferences":{"free_language_preferences":"party vibe"}}'>{"academic_profile":{"gpa":3.2,"major":"Computer Science"},"preferences":{"free_language_preferences":"nightlife, affordable"}}</textarea>
        <div style="margin-top: 12px;">
            <button id="run">Run Agent</button>
        </div>
        <div id="output" class="output" style="display:none; margin-top: 24px;"></div>
    </div>
    <script>
        const promptEl = document.getElementById('prompt');
        const runBtn = document.getElementById('run');
        const outputEl = document.getElementById('output');
        runBtn.onclick = async () => {
            outputEl.style.display = 'block';
            outputEl.innerHTML = '<p class="loading">Running agent...</p>';
            runBtn.disabled = true;
            try {
                const res = await fetch('/api/execute', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: promptEl.value.trim() })
                });
                const data = await res.json();
                if (data.status === 'ok') {
                    let parsed = [];
                    try { parsed = JSON.parse(data.response); } catch(e) {}
                    const analysis = Array.isArray(parsed) ? parsed : (parsed.analysis || []);
                    const courses = parsed.courses || [];
                    let html = '<p class="success">Found ' + analysis.length + ' universities.</p>';
                    html += '<div class="response"><strong>Response:</strong><pre>' + JSON.stringify({ analysis, courses }, null, 2) + '</pre></div>';
                    html += '<div class="steps"><strong>Execution Steps:</strong>';
                    (data.steps || []).forEach(s => {
                        html += '<div class="step"><div class="step-module">' + (s.module || 'Unknown') + '</div>';
                        html += '<pre>Prompt: ' + JSON.stringify(s.prompt, null, 2) + '</pre>';
                        html += '<pre>Response: ' + JSON.stringify(s.response, null, 2) + '</pre></div>';
                    });
                    html += '</div>';
                    outputEl.innerHTML = html;
                } else {
                    outputEl.innerHTML = '<p class="error">Error: ' + (data.error || 'Unknown error') + '</p>';
                }
            } catch (e) {
                outputEl.innerHTML = '<p class="error">Request failed: ' + e.message + '</p>';
            }
            runBtn.disabled = false;
        };
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def serve_ui():
    """Serve the web UI for interacting with the agent."""
    return UI_HTML

# --- STRICT SCHEMA DEFINITIONS ---
class ExecuteRequest(BaseModel):
    prompt: str

class StepLog(BaseModel):
    module: str
    prompt: Dict[str, Any]
    response: Dict[str, Any]

class ExecuteResponse(BaseModel):
    status: str
    error: Optional[str] = None
    response: Any = None
    steps: List[StepLog] = []

# --- THE 4 REQUIRED ENDPOINTS ---

@app.get("/api/team_info")
def get_team_info():
    return {
        "group_batch_order_number": "01_01", # Update this later
        "team_name": "Fez Exchange Agent",
        "students": [
            { "name": "Yam Ben Tob", "email": "yam.b@campus.technion.ac.il" },
            { "name": "Asaf Greenstein", "email": "asaf.g@campus.technion.ac.il" }
        ]
    }

@app.get("/api/agent_info")
def get_agent_info():
    return {
        "description": "Conversation-aware multi-agent orchestration system for global university exchange placement. Uses Filter (Supabase), Ranker (LLM), CourseFinder (ReAct + RAG + Web), and Analyzer (Pinecone RAG + LLM) to recommend universities and matched courses.",
        "purpose": "Filters universities by academic/language/availability criteria, ranks by preferences, finds courses, and analyzes top matches for logistics and fit. Supports follow-up prompts (e.g. 'show more', 'find courses', 'something cheaper').",
        "prompt_template": {
            "template": '{"academic_profile": {"gpa": 85, "major": "Computer Science"}, "preferences": {"free_language_preferences": "social scene, party vibe"}, "language_profile": {}, "availability": {}}'
        },
        "prompt_examples": [
            {
                "prompt": '{"academic_profile": {"gpa": 85}, "preferences": {"free_language_preferences": "party vibe, easy to make friends"}}',
                "full_response": "**1. CTU (Prague)**\n   Fit: Strong social scene, Erasmus presence...\n   Academic: 30 ECTS min...\n   Logistics: Housing lottery, ~$3.5k/semester.\n   Courses: Introduction to Algorithms, Data Structures...",
                "steps": [
                    {"module": "Filter", "prompt": {"action": "Query Supabase", "criteria": {}}, "response": {"found_universities": 12}},
                    {"module": "Ranker", "prompt": {"llm_prompt": "..."}, "response": {"top_universities": ["CTU (Prague)", "DTU", "Politecnico di Milano"]}},
                    {"module": "CourseFinder", "prompt": {"universities": ["CTU (Prague)"], "major": "CS"}, "response": {"courses_found": 5, "courses": [...]}},
                    {"module": "Analyzer", "prompt": {"target_university": "CTU (Prague)"}, "response": {"logistics": {...}}}
                ]
            }
        ],
        "full_response": "Structured JSON with analysis (university_name, general_fit_reasoning, requirements, logistics, matched_courses) per university.",
        "steps": [
            {"module": "Filter", "prompt": {"action": "Query Supabase", "criteria": "user profile"}, "response": {"found_universities": int, "traced_steps": [...]}},
            {"module": "Ranker", "prompt": {"llm_prompt": str}, "response": {"scored_universities": [...], "top_universities": [...]}},
            {"module": "CourseFinder", "prompt": {"universities": [...], "major": str, "languages": [...]}, "response": {"courses_found": int, "courses": [...]}},
            {"module": "Analyzer", "prompt": {"target_university": str}, "response": {"logistics": {...}}}
        ]
    }

@app.get("/api/model_architecture")
def get_architecture():
    base = os.path.dirname(os.path.abspath(__file__))
    for name in ("architecture.png", "architecture_placeholder.png"):
        file_path = os.path.join(base, "..", name)
        if os.path.exists(file_path):
            return FileResponse(file_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Image not found")

@app.post("/api/execute", response_model=ExecuteResponse)
def execute_agent(request: ExecuteRequest):
    try:
        try:
            user_profile = json.loads(request.prompt)
            chat_msg = ""
        # 2. If it fails, it's a plain text chat message
        except json.JSONDecodeError:
            user_profile = {}         
            chat_msg = request.prompt  
            
        result = agent.run(new_chat_message=chat_msg, user_profile_dict=user_profile)

        response_payload = json.dumps({
            "analysis": result.get("analysis", []),
            "courses": result.get("courses", []),
        })

        return {
            "status": "ok",
            "error": None,
            "response": response_payload,
            "steps": result.get("steps", []),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "response": None,
            "steps": [],
        }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
