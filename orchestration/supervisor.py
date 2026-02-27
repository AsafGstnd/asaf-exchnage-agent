"""
Supervisor agent for orchestrating calls to other agents in the orchestration layer.
"""
from typing import TypedDict, Any, List
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from orchestration.specialists.ranker import score_universities_with_llm, process_llm_scores
from orchestration.specialists.analyzer import analyze_universities
from orchestration.specialists.filter import filter_universities
from utils import config 

# 1. Define the State Schema
class AgentState(TypedDict, total=False):
    valid_universities_list: list
    user_iformation: dict
    user_requests: List[str]
    top_k: int
    top_universities: list
    analysis: str
    request_count: int
    universities_fit_text: List[str]
    steps: List[dict]

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
    preferences = state["user_iformation"].get("preferences", {})
    free_language_preferences = preferences.get("free_language_preferences", "")
    llm_json_response, rank_prompt = score_universities_with_llm(
        state["valid_universities_list"],
        free_language_preferences,
        state["top_k"],
        return_prompt=True
    )
    reasonings = [uni.get("reasoning", "") for uni in llm_json_response.get("scored_universities", [])]
    top_universities = process_llm_scores(llm_json_response, top_k=state["top_k"])
    step = {
        "module": "Ranker",
        "prompt": rank_prompt,
        "response": {"scored_universities": llm_json_response.get("scored_universities", []), "top_universities": top_universities}
    }
    return {
        "universities_fit_text": reasonings,
        "top_universities": top_universities,
        "steps": (state.get("steps") or []) + [step]
    }

def analyze_node(state: AgentState):
    analysis_results, analyze_steps = analyze_universities(
        state.get("top_universities", []),
        state.get("universities_fit_text", None),
        return_steps=True
    )
    formatted = _format_analysis_as_string(analysis_results)
    return {
        "analysis": formatted,
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
    Analyzes the free-form user text to decide which task fits best using LLM, falls back to filter if LLM is unavailable.
    """
    if state.get("request_count", 1) == 1:
        return "filter"
    requests = state.get("user_requests", [])
    user_text = str(requests[-1]) if requests else state.get("user_iformation", {}).get("free_text", "")
    try:
        from utils.llmod_client import llmod_chat
        system_prompt = "You are an expert workflow router for a university exchange agent. Given a user's free-form input, decide which task fits best: 'filter', 'rank', or 'analyze'. Prefer small tweaks (rank) over big changes (filter), but do whatever is required. Respond ONLY with one of: filter, rank, analyze."
        user_prompt = f"User input: {user_text}"
        task = llmod_chat(system_prompt, user_prompt, use_json=False).strip().lower()
        if task in {"filter", "rank", "analyze"}:
            return task
    except Exception:
        pass
    return "filter"

# 4. Build the Supervisor Graph
class Supervisor:
    def __init__(self):
        workflow = StateGraph(AgentState)
        
        # Add the nodes
        workflow.add_node("filter", filter_node)
        workflow.add_node("rank", rank_node)
        workflow.add_node("analyze", analyze_node)
        
        # Set the dynamic entry point using the router
        workflow.add_conditional_edges(
            START,
            choose_entry_point,
            {
                "filter": "filter",
                "rank": "rank",
                "analyze": "analyze"
            }
        )
        
        # Set the cascade (waterfall) flow
        workflow.add_edge("filter", "rank")
        workflow.add_edge("rank", "analyze")
        workflow.add_edge("analyze", END)
        
        # Compile the graph into an executable app
        memory = MemorySaver()        
        self.app = workflow.compile(checkpointer=memory)

    def run(self, new_chat_message: str, user_profile_dict: dict = None, thread_id="user_123"):        
        config = {"configurable": {"thread_id": thread_id}}
        current_memory = self.app.get_state(config).values        
        current_count = current_memory.get("request_count", 0)
        current_requests = current_memory.get("user_requests", [])
        
        new_count = current_count + 1        
        updated_requests = current_requests + [new_chat_message] 
        
        if new_count == 1:
            if not user_profile_dict:
                raise ValueError("user_profile_dict is required for the first request!")
            payload = {
                "user_iformation": user_profile_dict, # Set the JSON profile once
                "user_requests": updated_requests,
                "request_count": new_count,
                "valid_universities_list": [], 
                "top_k": 5,
                "extracted_data_dict": {},
                "rag_factsheet_func": None,
                "top_universities": [],
                "analysis": "",
                "universities_fit_text": [],
                "steps": []
            }
        else:
            payload = {
                "user_requests": updated_requests,
                "request_count": new_count
            }

        result = self.app.invoke(payload, config=config)
        return {"analysis": result.get("analysis", ""), "steps": result.get("steps", [])}