"""
Supervisor agent for orchestrating calls to other agents in the orchestration layer.
"""
from typing import TypedDict, Any, List
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from orchestration.specialists.ranker import rank_universities
from orchestration.specialists.analyzer import analyze_universities
from orchestration.specialists.filter import filter_universities
from utils import config 

# 1. Define the State Schema
class AgentState(TypedDict):
    valid_universities_list: list
    user_iformation: dict
    user_requests: List[str]
    top_k: int
    extracted_data_dict: dict
    rag_factsheet_func: Any
    top_universities: list
    analysis: str
    request_count: int

# 2. Define the Nodes
def filter_node(state: AgentState):
    filtered_universities = filter_universities(state["user_iformation"])
    state["valid_universities_list"] = filtered_universities
    return state

def rank_node(state: AgentState):
    preferences = state["user_iformation"].get("preferences", {})
    free_language_preferences = preferences.get("free_language_preferences", "")
    state["top_universities"] = rank_universities(
        state["valid_universities_list"],
        free_language_preferences,
        state["top_k"]
    )
    return state

def analyze_node(state: AgentState):
    state["analysis"] = analyze_universities(
        state.get("top_universities", []), # Uses empty list if not ranked yet
        state["extracted_data_dict"],
        state["rag_factsheet_func"]
    )
    return state

# 3. Define the Routing Logic
def choose_entry_point(state: AgentState) -> str:
    """
    Analyzes the free-form user text to decide which task fits best using LLM, falls back to rules if LLM is unavailable.
    """
    # If this is the first user request, always start with filter
    if state.get("request_count", 1) == 1:
        return "filter"
    user_text = state["user_iformation"].get("free_text", "")
    try:
        from utils.llmod_client import llmod_chat
        system_prompt = "You are an expert workflow router for a university exchange agent. Given a user's free-form input, decide which task fits best: 'filter', 'rank', or 'analyze'. Prefer small tweaks (rank) over big changes (filter), but do whatever is required. Respond ONLY with one of: filter, rank, analyze."
        user_prompt = f"User input: {user_text}"
        task = llmod_chat(system_prompt, user_prompt, use_json=False).strip().lower()
        if task in {"filter", "rank", "analyze"}:
            return task
    except Exception:
        pass

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

    def run(self, user_input, request_count=1):
        # Only initialize user_input and request_count for the first request
        initial_state = {
            "user_input": user_input,
            "request_count": request_count,
            "valid_universities_list": [],
            "top_k": 5,
            "extracted_data_dict": {},
            "rag_factsheet_func": None,
            "top_universities": [],
            "analysis": ""
        }
        # Run the LangGraph app
        result = self.app.invoke(initial_state)
        # Return the final analysis from the finished state
        return result["analysis"]
    
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
                "user_input": user_profile_dict, # Set the JSON profile once
                "user_requests": updated_requests,
                "request_count": new_count,
                "valid_universities_list": [], 
                "top_k": 5,
                "extracted_data_dict": {},
                "rag_factsheet_func": None,
                "top_universities": [],
                "analysis": ""
            }
        else:
            payload = {
                "user_requests": updated_requests,
                "request_count": new_count
            }

        result = self.app.invoke(payload, config=config)
        return result["analysis"]