from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uvicorn
import os
import json
import re
import logging

from orchestration.supervisor import Supervisor
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = Supervisor()

# --- STRICT SCHEMA DEFINITIONS ---
PROMPT_MAX_LENGTH = 15000

class ExecuteRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=PROMPT_MAX_LENGTH)

class StepLog(BaseModel):
    module: str
    prompt: Dict[str, Any]
    response: Dict[str, Any]

class ExecuteResponse(BaseModel):
    status: str
    error: Optional[str]
    response: Any
    steps: List[StepLog]

def _sanitize_error(e: Exception) -> str:
    """Remove sensitive data (API keys, URLs) from error messages."""
    msg = str(e)
    msg = re.sub(r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', '[REDACTED]', msg)
    msg = re.sub(r'sk-[A-Za-z0-9_-]+', '[REDACTED]', msg)
    msg = re.sub(r'pcsk_[A-Za-z0-9_-]+', '[REDACTED]', msg)
    msg = re.sub(r'https?://[^\s]+', '[REDACTED_URL]', msg)
    return msg[:500]

# --- HEALTH CHECK ---
@app.get("/api/health")
def health_check():
    ok = True
    issues = []
    try:
        from utils.config import supabase
        if not supabase:
            ok = False
            issues.append("Supabase not configured")
    except Exception as e:
        ok = False
        issues.append(f"Supabase: {_sanitize_error(e)}")
    try:
        from utils.config import PINECONE_API_KEY, PINECONE_INDEX_NAME
        if not PINECONE_API_KEY or not PINECONE_INDEX_NAME:
            ok = False
            issues.append("Pinecone not configured")
    except Exception as e:
        ok = False
        issues.append(f"Pinecone: {_sanitize_error(e)}")
    return {"status": "ok" if ok else "degraded", "issues": issues}

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
        "description": "Multi-agent orchestration system for global university exchange placement. Uses Filter (Supabase), Ranker (LLM), and Analyzer (Pinecone RAG + LLM + Wikipedia web enrichment) to recommend universities. Accepts natural language or JSON.",
        "purpose": "Filters universities by academic/language/availability criteria, ranks by preferences, and analyzes top matches with real-time web data (Wikipedia), RAG factsheets, and personalized executive summaries.",
        "prompt_template": {
            "template": '{"academic_profile": {"gpa": 85, "major": "Computer Science"}, "preferences": {"free_language_preferences": "social scene, party vibe"}, "language_profile": {}, "availability": {}}'
        },
        "prompt_examples": [
            {
                "prompt": '{"academic_profile": {"gpa": 85}, "preferences": {"free_language_preferences": "party vibe, easy to make friends"}}',
                "full_response": "**1. CTU (Prague)**\n   Fit: Strong social scene, Erasmus presence...\n   Academic: 30 ECTS min...\n   Logistics: Housing lottery, ~$3.5k/semester.",
                "steps": [
                    {"module": "Filter", "prompt": {"action": "Query Supabase", "criteria": {}}, "response": {"found_universities": 12}},
                    {"module": "Ranker", "prompt": {"top_k": 5}, "response": {"top_universities": ["CTU (Prague)", "DTU", "Politecnico di Milano"]}},
                    {"module": "Analyzer", "prompt": {"target_university": "CTU (Prague)"}, "response": {"logistics_and_experience": {}}}
                ]
            }
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
@limiter.limit("30/minute")
def execute_agent(request: Request, execute_request: ExecuteRequest):
    req = execute_request  # avoid shadowing Request
    try:
        prompt = req.prompt.strip()
        if not prompt:
            return ExecuteResponse(status="error", error="Prompt cannot be empty", response=None, steps=[])

        try:
            parsed = json.loads(prompt)
        except json.JSONDecodeError:
            parsed = {}

        if not isinstance(parsed, dict):
            return ExecuteResponse(status="error", error="Prompt must be a JSON object", response=None, steps=[])

        # Use profile extractor for free-text or minimal input (enables natural language)
        from orchestration.profile_extractor import extract_profile_from_text
        user_profile = extract_profile_from_text(prompt)
        if not user_profile:
            return ExecuteResponse(status="error", error="Could not extract profile from input", response=None, steps=[])

        result = agent.run(prompt, user_profile_dict=user_profile)
        return ExecuteResponse(
            status="ok",
            error=None,
            response=result.get("analysis", ""),
            steps=result.get("steps", [])
        )
    except Exception as e:
        logger.exception("Execute failed")
        return ExecuteResponse(
            status="error",
            error=_sanitize_error(e),
            response=None,
            steps=[]
        )

# Serve minimal UI at / (connects to /api when deployed on same host, e.g. Render)
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
