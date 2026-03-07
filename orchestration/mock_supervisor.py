class Supervisor:
    """
    MOCK SUPERVISOR:
    Simulates the real LangGraph Supervisor when external services are unavailable.
    Accepts the same interface as the real Supervisor.
    """
    def __init__(self):
        self.is_mock = True

    def run(self, new_chat_message: str = "", user_profile_dict: dict = None, thread_id="user_123"):
        import time
        time.sleep(0.5)

        profile = user_profile_dict or {}
        gpa = profile.get("academic_profile", {}).get("gpa", "N/A")
        major = profile.get("academic_profile", {}).get("major", "N/A")
        preferences = profile.get("preferences", {}).get("free_language_preferences", "")

        mock_top_universities = ["CTU (Prague)", "DTU", "Politecnico di Milano"]

        mock_analysis = [
            {
                "university_name": "CTU (Prague)",
                "general_fit_reasoning": (
                    "Strong CS program with vibrant student nightlife in the city centre. "
                    "Erasmus hub with low living costs (~€600/month)."
                ),
                "requirements": {"min_gpa": 2.5, "english_only_possible": True},
                "logistics": {
                    "academic": {"instruction_languages": "English", "academic_summary_notes": "ECTS-based, strong STEM focus."},
                    "housing_and_logistics": {"campus_housing_guaranteed": False, "estimated_housing_cost_per_month": "400-600", "currency": "EUR"},
                    "student_integration": {"buddy_program_available": True, "orientation_program_provided": True}
                },
                "matched_courses": [
                    {"course_name": "Algorithms and Data Structures", "language": "English", "relevance": "Core CS requirement."},
                    {"course_name": "Machine Learning", "language": "English", "relevance": "Popular elective for CS majors."}
                ]
            }
        ]

        mock_courses = [
            {
                "university_name": "CTU (Prague)",
                "matched_courses": [
                    {"course_name": "Algorithms and Data Structures", "language": "English", "relevance": "Core CS requirement."},
                    {"course_name": "Machine Learning", "language": "English", "relevance": "Popular elective for CS majors."}
                ]
            }
        ]

        mock_steps = [
            {
                "module": "Filter",
                "prompt": {"action": "Query Supabase", "criteria": profile},
                "response": {"found_universities": 12, "status": "mock"}
            },
            {
                "module": "Ranker",
                "prompt": {"action": "Score with LLM", "top_k": 5, "preferences": preferences},
                "response": {"top_universities": mock_top_universities, "status": "mock"}
            },
            {
                "module": "CourseFinder",
                "prompt": {"universities": mock_top_universities, "major": major},
                "response": {"courses_found": 2, "status": "mock"}
            },
            {
                "module": "Analyzer",
                "prompt": {"action": "RAG Pinecone Search", "targets": mock_top_universities},
                "response": {"universities_analyzed": len(mock_analysis), "status": "mock"}
            }
        ]

        return {
            "analysis": mock_analysis,
            "courses": mock_courses,
            "steps": mock_steps
        }
