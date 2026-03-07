"""
Supervisor agent for orchestrating calls to other agents in the orchestration layer.
"""
from typing import TypedDict, Any, List, Dict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from pathlib import Path
import json

from orchestration.specialists.ranker import score_universities_with_llm, process_llm_scores
from orchestration.specialists.analyzer import analyze_universities
from orchestration.specialists.filter import filter_universities
from utils import config 

# 1. Define the State Schema
class AgentState(TypedDict, total=False):
    valid_universities_list: list       # List of universities after filtering
    user_iformation: dict               # Student profile input data
    user_requests: List[str]            # History of user requests/messages
    top_k: int                          # Number of top universities to select
    top_universities: list              # Final ranked university names
    analysis: List[dict]                # Final recommendation/analysis string
    request_count: int                  # Number of requests in session
    universities_fit_text: List[str]    # Reasoning for university fit
    steps: List[Dict[str,Any]]                   # Execution trace of agent steps
    courses: List[dict]                          # Matched courses per university (from CourseFinder)

# 2. Define the Nodes
def filter_node(state: AgentState):
    filtered_result = filter_universities(state["user_iformation"])
    step = {
        "module": "Filter",
        "prompt": {"action": "Query Supabase", "criteria": state["user_iformation"]},
        "response": {"found_universities": len(filtered_result["universities"]), "traced_steps": filtered_result.get("traced_steps", [])}
    }
    return {
        "valid_universities_list": filtered_result["universities"],
        "steps": (state.get("steps") or []) + [step]
    }

def rank_node(state: AgentState):
    universities = state.get("valid_universities_list", []) or []

    # Cost-aware optimization: skip expensive LLM ranking when the candidate set is already very small
    # to reduce token usage and latency.
    if len(universities) <= 3:
        top_universities = [
            u.get("name")
            for u in universities
            if isinstance(u, dict) and u.get("name")
        ]
        step = {
            "module": "Ranker",
            "prompt": {
                "action": "skip_llm_ranking",
                "reason": "few_candidates",
                "candidate_count": len(universities),
            },
            "response": {
                "scored_universities": [],
                "top_universities": top_universities,
            },
        }
        return {
            "universities_fit_text": [],
            "top_universities": top_universities,
            "steps": (state.get("steps") or []) + [step],
        }

    preferences = state["user_iformation"].get("preferences", {})
    free_language_preferences = preferences.get("free_language_preferences", "")
    llm_json_response, rank_prompt = score_universities_with_llm(
        state["valid_universities_list"],
        free_language_preferences,
        state["top_k"],
        return_prompt=True,
    )
    reasonings = [uni.get("reasoning", "") for uni in llm_json_response.get("scored_universities", [])]
    top_universities = process_llm_scores(llm_json_response, top_k=state["top_k"])
    step = {
        "module": "Ranker",
        "prompt": {"llm_prompt": rank_prompt},
        "response": {
            "scored_universities": llm_json_response.get("scored_universities", []),
            "top_universities": top_universities,
        },
    }
    return {
        "universities_fit_text": reasonings,
        "top_universities": top_universities,
        "steps": (state.get("steps") or []) + [step],
    }

def course_finder_node(state: AgentState):
    from orchestration.specialists.course_finder import find_courses_react
    courses = find_courses_react(
        state.get("top_universities", []),
        state.get("user_iformation", {})
    )
    step = {
        "module": "CourseFinder",
        "prompt": {
            "universities": state.get("top_universities", []),
            "major": state.get("user_iformation", {}).get("academic_profile", {}).get("major"),
            "languages": state.get("user_iformation", {}).get("language_profile", {}).get("non_english_languages", [])
        },
        "response": {"courses_found": len(courses), "courses": courses}
    }
    return {"courses": courses, "steps": (state.get("steps") or []) + [step]}

def analyze_node(state: AgentState):
    analysis_results, analyze_steps = analyze_universities(
        state.get("top_universities", []),
        state.get("universities_fit_text", None),
        courses=state.get("courses", []),
        return_steps=True
    )
    # formatted = _format_analysis_as_string(analysis_results)
    return {
        "analysis": analysis_results,
        "steps": (state.get("steps") or []) + analyze_steps
    }

def _format_analysis_as_string(analysis_results: list) -> str:
    """Format analysis list into a human-readable string for API response."""
    if not analysis_results:
        return "No universities matched your criteria."
    parts = []
    for i, uni in enumerate(analysis_results, 1):
        name = uni.get("university_name", uni.get("name", "Unknown"))
        reasoning = uni.get("general_fit_reasoning", "")
        logistics = uni.get("logistics_and_experience", {})
        parts.append(f"**{i}. {name}**")
        if reasoning:
            parts.append(f"   Fit: {reasoning}")
        if logistics:
            ac = logistics.get("academic", {})
            housing = logistics.get("housing_and_logistics", {})
            if ac.get("academic_summary_notes"):
                parts.append(f"   Academic: {ac['academic_summary_notes']}")
            if housing.get("logistics_summary_notes"):
                parts.append(f"   Logistics: {housing['logistics_summary_notes']}")
        parts.append("")
    return "\n".join(parts).strip()

# 3. Define the Routing Logic
def choose_entry_point(state: AgentState) -> str:
    """
    Conversation-aware router. First turn always runs full pipeline.
    Follow-ups: LLM decides filter | rank | courses | analyze.
    """
    if state.get("request_count", 1) == 1:
        return "filter"
    requests = state.get("user_requests", [])
    user_text = str(requests[-1]) if requests else state.get("user_iformation", {}).get("free_text", "")
    try:
        from utils.llmod_client import llmod_chat
        system_prompt = """You are an expert workflow router for a university exchange agent.
Given a user's free-form input, decide which task fits best:
- filter: New criteria, first message, or major preference change (e.g. "I want universities with strong nightlife")
- rank: Change preferences like budget, nightlife, "show me more universities" (e.g. "Actually I prefer something cheaper", "Show me more universities")
- courses: Find courses, computer science, language of instruction (e.g. "Find computer science courses there")
- analyze: Re-analyze logistics only

Respond ONLY with one word: filter, rank, courses, or analyze."""
        user_prompt = f"User input: {user_text}"
        task = llmod_chat(system_prompt, user_prompt, use_json=False).strip().lower()
        if task in {"filter", "rank", "courses", "analyze"}:
            return task
    except Exception:
        pass
    return "filter"

# 4. Build the Supervisor Graph
# Pipeline order: filter -> rank -> course_finder -> analyze (Analyzer runs last as reasoning layer)
class Supervisor:
    def __init__(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("filter", filter_node)
        workflow.add_node("rank", rank_node)
        workflow.add_node("course_finder", course_finder_node)
        workflow.add_node("analyze", analyze_node)

        workflow.add_conditional_edges(
            START,
            choose_entry_point,
            {
                "filter": "filter",
                "rank": "rank",
                "courses": "course_finder",
                "analyze": "analyze",
            },
        )

        workflow.add_edge("filter", "rank")
        workflow.add_edge("rank", "course_finder")
        workflow.add_edge("course_finder", "analyze")
        workflow.add_edge("analyze", END)
        
        # Compile the graph into an executable app
        memory = MemorySaver()        
        self.app = workflow.compile(checkpointer=memory)
    
    def _save_snapshot(self, state_values: dict, count: int, thread_id: str):
        """Saves state to root/outputs/ using Thread ID and Request Index"""
        try:
            # 1. Path Setup (Root/outputs/)
            root_dir = Path(__file__).resolve().parent.parent
            output_dir = root_dir / "outputs"
            output_dir.mkdir(parents=True, exist_ok=True)

            # 2. Unique Filename: Includes both Thread ID and Turn Count
            # Example: snapshot_user_123_turn_1.json
            file_name = f"snapshot_{thread_id}_turn_{count}.json"
            file_path = output_dir / file_name

            clean_state = {k: v for k, v in state_values.items() if k != "rag_factsheet_func"}
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(clean_state, f, ensure_ascii=False, indent=2, default=str)
                
        except Exception as e:
            print(f"⚠️ Warning: Snapshot failed for {thread_id}: {e}")

    def run(self, new_chat_message: str = "", user_profile_dict: dict = None, thread_id="user_123"):        
        config = {"configurable": {"thread_id": thread_id}}
        current_memory = self.app.get_state(config).values        
        current_count = current_memory.get("request_count", 0)
        current_requests = current_memory.get("user_requests", [])
        
        new_count = current_count + 1  
        updated_requests = list(current_requests)
        if new_chat_message.strip():
            updated_requests.append(new_chat_message.strip())      
        
        if new_count == 1:
            if not user_profile_dict:
                raise ValueError("user_profile_dict is required for the first request!")
            payload = {
                "user_iformation": user_profile_dict,   # Set the JSON profile once
                "user_requests": updated_requests,      # Will be [] if no message was passed
                "request_count": new_count,
                "valid_universities_list": [], 
                "top_k": 5,
                "extracted_data_dict": {},
                "rag_factsheet_func": None,
                "top_universities": [],
                "analysis": [],
                "universities_fit_text": [],
                "steps": [],
                "courses": []
            }
        else:
            payload = {
                "user_requests": updated_requests,
                "request_count": new_count
            }

        result = self.app.invoke(payload, config=config)
        final_state = self.app.get_state(config).values
        self._save_snapshot(final_state, new_count, thread_id)

        return {
            "analysis": result.get("analysis", []),
            "courses": result.get("courses", []),
            "steps": result.get("steps", [])
        }