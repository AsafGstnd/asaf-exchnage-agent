from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os
import json

# 🟢 THE MAGIC SWAP: 
# Right now, this uses the mock. When your real agent is ready, 
# change this to: from orchestration.supervisor import Supervisor
from orchestration.mock_supervisor import Supervisor

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
        "description": "Multi-agent orchestration system for global university exchange placement.",
        "purpose": "Filters, ranks, and analyzes universities based on constraints.",
        "prompt_template": {"template": "A JSON string containing your profile."},
        "prompt_examples": [{"prompt": "Example JSON", "full_response": "...", "steps": []}]
    }

@app.get("/api/model_architecture")
def get_architecture():
    file_path = "architecture.png"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path, media_type="image/png")

@app.post("/api/execute", response_model=ExecuteResponse)
def execute_agent(request: ExecuteRequest):
    try:
        try:
            user_profile = json.loads(request.prompt)
        except json.JSONDecodeError:
            user_profile = {"free_text": request.prompt}
        
        result = agent.run(user_profile)
        
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
