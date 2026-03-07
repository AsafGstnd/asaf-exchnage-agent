class Supervisor:
    """
    MOCK SUPERVISOR: 
    This simulates your LangGraph agent. It accepts a user profile 
    and returns a formatted final response and execution trace.
    """
    def __init__(self):
        self.is_mock = True

    def run(self, user_profile_dict: dict, thread_id="user_123"):
        # 1. Simulate a delay for realism
        import time
        time.sleep(2)
        
        # 2. Simulate the final analysis string
        mock_analysis = (
            "Based on your profile, we highly recommend **CTU (Prague)**. "
            "It perfectly matches your criteria for a highly social environment "
            "with an estimated semester cost of $3,500."
        )
        
        # 3. Simulate the EXACT step trace required by the assignment
        mock_steps = [
            {
                "module": "Filter",
                "prompt": {"action": "Query Supabase", "criteria": user_profile_dict},
                "response": {"found_universities": 12, "status": "Success"}
            },
            {
                "module": "Ranker",
                "prompt": {"action": "Score with LLM", "top_k": 5},
                "response": {"top_universities": ["CTU (Prague)", "DTU", "Politecnico di Milano"]}
            },
            {
                "module": "Analyzer",
                "prompt": {"action": "RAG Pinecone Search", "targets": ["CTU (Prague)"]},
                "response": {"extracted_costs": "$3,500", "vibe": "High Social"}
            }
        ]
        
        # Return exactly what your real LangGraph state will eventually return
        return {
            "analysis": mock_analysis,
            "steps": mock_steps
        }
