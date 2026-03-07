from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os
import json
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Fez Exchange Agent API",
    description="University exchange recommendation AI agent"
)

agent = None
try:
    from orchestration.supervisor import Supervisor as RealSupervisor
    agent = RealSupervisor()
    logger.info("✅ Supervisor initialized successfully")
except Exception as _init_err:
    logger.error("❌ Failed to initialize real Supervisor: %s", _init_err, exc_info=True)
    try:
        from orchestration.mock_supervisor import Supervisor as MockSupervisor
        agent = MockSupervisor()
        logger.warning("⚠️ Using MockSupervisor as fallback")
    except Exception as _mock_err:
        logger.error("❌ Failed to initialize MockSupervisor: %s", _mock_err, exc_info=True)

# ---------------- WEB UI ---------------- #

UI_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Fez Exchange Agent</title>
<style>
body {font-family: sans-serif; background:#0f172a; color:#e2e8f0; padding:20px;}
textarea{width:100%;height:150px;background:#1e293b;color:white;border-radius:6px;padding:10px;}
button{padding:10px 20px;margin-top:10px;background:#3b82f6;color:white;border:none;border-radius:6px;cursor:pointer;}
pre{background:#020617;padding:10px;border-radius:6px;overflow-x:auto;}
</style>
</head>
<body>

<h2>Fez Exchange Agent</h2>

<textarea id="prompt">
{"academic_profile":{"gpa":3.2,"major":"Computer Science"},"preferences":{"free_language_preferences":"nightlife, affordable"}}
</textarea>

<br>
<button onclick="runAgent()">Run Agent</button>

<div id="output"></div>

<script>
async function runAgent(){

 const prompt = document.getElementById("prompt").value;

 const res = await fetch("/api/execute",{
  method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({prompt})
 });

 const data = await res.json();

 let html="<h3>Response</h3><pre>"+JSON.stringify(data.response,null,2)+"</pre>";

 html+="<h3>Steps</h3>";

 (data.steps||[]).forEach(s=>{
   html+="<pre>"+JSON.stringify(s,null,2)+"</pre>";
 });

 document.getElementById("output").innerHTML=html;

}
</script>

</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def serve_ui():
    return UI_HTML


# ---------------- REQUEST SCHEMAS ---------------- #

class ExecuteRequest(BaseModel):
    prompt: str


class StepLog(BaseModel):
    module: str
    prompt: Dict[str, Any]
    response: Dict[str, Any]


class ExecuteResponse(BaseModel):
    status: str
    error: Optional[str] = None
    response: Optional[Any] = None
    steps: List[StepLog] = []


# ---------------- REQUIRED ENDPOINTS ---------------- #

@app.get("/api/team_info")
def get_team_info():
    return {
        "group_batch_order_number": "1_1",
        "team_name": "Fez Exchange Agent Team",
        "students": [
            {
                "name": "Yam Ben Tob",
                "email": "yam.b@campus.technion.ac.il"
            },
            {
                "name": "Asaf Greenstein",
                "email": "asaf.g@campus.technion.ac.il"
            }
        ]
    }


@app.get("/api/agent_info")
def get_agent_info():
    return {
        "description": "Conversation-aware multi-agent orchestration system for global university exchange placement. Uses Filter (Supabase), Ranker (LLM), CourseFinder (ReAct + RAG + Web), and Analyzer (Pinecone RAG + LLM) to recommend universities and matched courses.",

        "purpose": "Filters universities by academic/language/availability criteria, ranks by preferences, finds courses, and analyzes top matches for logistics and fit. Supports follow-up prompts such as 'show more', 'find courses', or 'something cheaper'.",

        "prompt_template": {
            "template": '{"academic_profile":{"gpa":85,"major":"Computer Science"},"preferences":{"free_language_preferences":"social scene, party vibe"},"language_profile":{},"availability":{}}'
        },

        "prompt_examples": [
            {
                "prompt": '{"academic_profile":{"gpa":85},"preferences":{"free_language_preferences":"party vibe, easy to make friends"}}',

                "full_response": "The agent recommends universities such as CTU Prague, DTU, and Politecnico di Milano because they combine strong computer science programs with vibrant student life.",

                "steps": [

                    {
                        "module": "Filter",
                        "prompt": {
                            "action": "Query Supabase",
                            "criteria": "user academic profile"
                        },
                        "response": {
                            "found_universities": 12
                        }
                    },

                    {
                        "module": "Ranker",
                        "prompt": {
                            "llm_prompt": "Rank universities based on social life and academic strength"
                        },
                        "response": {
                            "top_universities": [
                                "CTU Prague",
                                "DTU",
                                "Politecnico di Milano"
                            ]
                        }
                    },

                    {
                        "module": "CourseFinder",
                        "prompt": {
                            "universities": ["CTU Prague"],
                            "major": "Computer Science"
                        },
                        "response": {
                            "courses_found": 5,
                            "courses": [
                                "Algorithms",
                                "Machine Learning",
                                "Data Structures"
                            ]
                        }
                    },

                    {
                        "module": "Analyzer",
                        "prompt": {
                            "target_university": "CTU Prague"
                        },
                        "response": {
                            "logistics": {
                                "housing": "student dorm lottery",
                                "estimated_cost": "3500 USD per semester"
                            }
                        }
                    }

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
    logger.debug("[execute] Received prompt: %.200s", request.prompt)

    if agent is None:
        logger.error("[execute] Agent is not initialized")
        return {
            "status": "error",
            "error": "Agent failed to initialize at startup. Check server logs.",
            "response": None,
            "steps": []
        }

    try:

        try:
            user_profile = json.loads(request.prompt)
            chat_msg = ""
            logger.debug("[execute] Parsed JSON profile with keys: %s", list(user_profile.keys()))

        except json.JSONDecodeError:
            user_profile = {}
            chat_msg = request.prompt
            logger.debug("[execute] Using free-text prompt: %.100s", chat_msg)

        logger.debug("[execute] Invoking supervisor...")
        result = agent.run(
            new_chat_message=chat_msg,
            user_profile_dict=user_profile
        )

        analysis = result.get("analysis", [])
        courses = result.get("courses", [])
        steps = result.get("steps", [])
        logger.debug("[execute] analysis=%d items, courses=%d items, steps=%d items",
                     len(analysis) if isinstance(analysis, list) else 0,
                     len(courses) if isinstance(courses, list) else 0,
                     len(steps) if isinstance(steps, list) else 0)

        response_payload = json.dumps({
            "analysis": analysis,
            "courses": courses
        })

        return {
            "status": "ok",
            "error": None,
            "response": response_payload,
            "steps": steps
        }

    except Exception as e:
        logger.error("[execute] Unhandled error: %s", e, exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "response": None,
            "steps": []
        }


# ---------------- RUN SERVER ---------------- #

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
