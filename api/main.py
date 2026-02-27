from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os
import json

from orchestration.supervisor import Supervisor

app = FastAPI()
agent = Supervisor()

# --- STRICT SCHEMA DEFINITIONS ---
class ExecuteRequest(BaseModel):
    prompt: str

class StepLog(BaseModel):
    module: str
    prompt: Dict[str, Any]
    response: Dict[str, Any]

class ExecuteResponse(BaseModel):
    status: str
    error: Optional[str]
    response: Any
    steps: List[StepLog]

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
        "description": "Multi-agent orchestration system for global university exchange placement. Uses Filter (Supabase), Ranker (LLM), and Analyzer (Pinecone RAG + LLM) to recommend universities.",
        "purpose": "Filters universities by academic/language/availability criteria, ranks by preferences, and analyzes top matches for logistics and fit.",
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
def execute_agent(request: ExecuteRequest):
    try:
        try:
            user_profile = json.loads(request.prompt)
        except json.JSONDecodeError:
            user_profile = {"free_text": request.prompt, "preferences": {"free_language_preferences": request.prompt}}
        result = agent.run(request.prompt, user_profile_dict=user_profile)
        return {
            "status": "ok",
            "error": None,
            "response": result.get("analysis", ""),
            "steps": result.get("steps", [])
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "response": None, "steps": []}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
