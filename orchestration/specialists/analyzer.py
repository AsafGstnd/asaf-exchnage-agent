import json
from tools.registry import rag_search
from utils.config import supabase
from utils.llmod_client import llmod_chat

# Limit RAG chunks for efficiency
RAG_TOP_K = 2


def gather_context_for_llm(university: str) -> str:
    """
    Gathers context for a university using cached RAG search.
    Runs topic-specific queries via the central tool registry.
    """
    search_queries = [
        "academic requirements, credit system, ECTS, course load, grading scale, teaching methodology, prerequisites",
        "student accommodation, dormitory, housing guarantee, student residences, shared flat, rental costs, living expenses, food and personal expenses",
        "student visa application process, residence permit, post-arrival registration, mandatory health insurance, medical certificate, vaccination requirements",
        "orientation program, welcome week, buddy program, international student integration, student support services, career center, language courses for exchange students, pre-semester language course",
    ]

    master_context_blocks = []
    for query in search_queries:
        text = rag_search(query=query, university=university, top_k=RAG_TOP_K)
        if text and text != "No relevant information found in factsheets.":
            master_context_blocks.append(text)

    return "\n\n--- NEXT CHUNK ---\n\n".join(master_context_blocks) if master_context_blocks else "No context found."


def _get_courses_for_university(courses_list: list, university_name: str) -> list:
    """Extract matched courses for a university from CourseFinder output."""
    if not courses_list:
        return []
    for item in courses_list:
        if item.get("university_name") == university_name:
            return item.get("matched_courses", [])
    return []


def analyze_universities(top_universities, universities_fit_text=None, courses=None, return_steps=False):
    """
    Provides a comprehensive analysis for each university by combining:
    - Structured requirements and metadata from Supabase (universities_requirements table)
    - RAG-based category analysis from Pinecone
    - Fit reasoning from the ranking step (if provided)

    Args:
        top_universities (list[str]): List of university names (strings).
        universities_fit_text (list[str], optional): List of reasoning strings from supervisor state, aligned with top_universities.
        return_steps (bool): If True, return (analysis_results, steps) for API step logging.

    Returns:
        list[dict] or tuple: List of analysis dicts; if return_steps, (list, steps).
    """
    analysis_results = []
    steps = []

    system_prompt = """You are an expert data extraction AI for a university exchange program.
    Your job is to parse factsheet context and extract specific variables into a strict JSON format for side-by-side comparison.

    ### EXTRACTION RULES:
    1. **Strict Format**: Output ONLY valid JSON. Do not include markdown code blocks (unless specified) or conversational filler.
    2. **Data Integrity**: Use `null` if a detail is missing or only a hyperlink is provided. Never invent data.
    3. **Boolean Values**: Use `true`, `false`, or `null`. Only use `true` if the text explicitly confirms it (e.g., "guaranteed", "mandatory", "provided").
    4. **Currency**: Extract the 3-letter ISO code (e.g., 'EUR', 'KRW'). If not stated, infer based on the university's country.
    5. **Cost Strings**: Extract housing/living costs as concise strings. Do NOT include currency symbols in these fields. 
    - If costs vary by campus or room type, list them clearly: "Paris: 400-800, Troyes: 330-450" or "Studio: 750, Shared: 400".
    6. **Time Conversion**: Convert visa processing "months" into "weeks" (e.g., "3 months" becomes 12).
    7. **Summary Length**: Keep all `_summary_notes` and `_details` fields to 1-2 concise sentences.

    ### REQUIRED JSON SCHEMA:
    {
        "academic": {
            "min_credits_required": "int or null",
            "max_credits_allowed": "int or null",
            "instruction_languages": "string or null",
            "grading_system_summary": "string or null",
            "academic_summary_notes": "string or null" 
        },
        "housing_and_logistics": {
            "campus_housing_guaranteed": "boolean or null",
            "housing_details": "string or null",
            "university_sponsors_visa": "boolean or null",
            "estimated_visa_processing_weeks": "int or null",
            "mandatory_insurance_required": "boolean or null",
            "medical_and_insurance_details": "string or null",
            "currency": "string or null",
            "estimated_housing_cost_per_month": "string or null",
            "estimated_living_cost_per_month": "string or null",
            "logistics_summary_notes": "string or null"
        },
        "student_integration": {
            "buddy_program_available": "boolean or null",
            "orientation_program_provided": "boolean or null",
            "orientation_is_mandatory": "boolean or null",
            "pre_semester_language_course_available": "boolean or null",
            "language_course_details": "string or null",
            "integration_summary_notes": "string or null"
        }
    }"""
     

    for idx, uni_name in enumerate(top_universities):
        context_text = gather_context_for_llm(uni_name)

        user_prompt = f"""Extract the exchange data for the following university based on the provided context.

        TARGET UNIVERSITY: {uni_name}

        CONTEXT FROM FACTSHEETS:
        ---
        {context_text}
        ---"""

        # Call your LLM, ensuring it returns JSON
        extracted_logistics_json = llmod_chat(system_prompt, user_prompt, use_json=True)
        logistics_and_experience_dict = json.loads(extracted_logistics_json)
        if return_steps:
            steps.append({
                "module": "Analyzer",
                "prompt": {"target_university": uni_name, "user_prompt_preview": user_prompt[:300] + "..."},
                "response": logistics_and_experience_dict
            })

        # Query Supabase for requirements for this university (column is "name", not "university")
        supa_resp = supabase.table("universities_requirements").select("*").eq("name", uni_name).execute()
        eligibility_and_framework = supa_resp.data[0] if supa_resp and hasattr(supa_resp, 'data') and supa_resp.data else {}

        matched_courses = _get_courses_for_university(courses or [], uni_name)

        uni_analysis = {
            "university_name": uni_name,
            "general_fit_reasoning": universities_fit_text[idx] if universities_fit_text and idx < len(universities_fit_text) else None,
            "requirements": eligibility_and_framework,
            "logistics": logistics_and_experience_dict,
            "matched_courses": matched_courses,
        }

        analysis_results.append(uni_analysis)
    if return_steps:
        return analysis_results, steps
    return analysis_results

# Analysis Results Strcture: List[Dict] where each dict has the following format:
# {
#     "university_name": "string",
#     "general_fit_reasoning": "string or null",

#     // --- BUCKET 1: Hard Requirements (eligibility_and_framework) ---
#     "requirements": {
#         "min_gpa": "float or null",
#         "non_english_languages": ["list of strings"],
#         "english_test_type": ["list of strings"],
#         "english_test_level": "string or null",
#         "english_only_possible": "boolean",
#         "test_required": "boolean",
#         "waiver_available": "boolean",
#         "restricted_majors": ["list of standard major names"],
#         "msc_allowed": "boolean",
#         "min_semesters_completed": "int or null",
#         "fall_semester": {
#             "start_month": "int or null",
#             "start_day": "int or null",
#             "end_month": "int or null",
#             "end_day": "int or null"
#         },
#         "spring_semester": {
#             "start_month": "int or null",
#             "start_day": "int or null",
#             "end_month": "int or null",
#             "end_day": "int or null"
#         },
#         "erasmus_available": "boolean"
#     },

#     // --- BUCKET 2: Soft Experience (logistics_and_experience_dict) ---
#     "logistics": {
#         "academic": {
#             "min_credits_required": "int or null",
#             "max_credits_allowed": "int or null",
#             "instruction_languages": "string or null",
#             "grading_system_summary": "string or null",
#             "academic_summary_notes": "string or null" 
#         },
#         "housing_and_logistics": {
#             "campus_housing_guaranteed": "boolean or null",
#             "housing_details": "string or null",
#             "university_sponsors_visa": "boolean or null",
#             "estimated_visa_processing_weeks": "int or null",
#             "mandatory_insurance_required": "boolean or null",
#             "medical_and_insurance_details": "string or null",
#             "currency": "string or null",
#             "estimated_housing_cost_per_month": "string or null",
#             "estimated_living_cost_per_month": "string or null",
#             "logistics_summary_notes": "string or null"
#         },
#         "student_integration": {
#             "buddy_program_available": "boolean or null",
#             "orientation_program_provided": "boolean or null",
#             "orientation_is_mandatory": "boolean or null",
#             "pre_semester_language_course_available": "boolean or null",
#             "language_course_details": "string or null",
#             "integration_summary_notes": "string or null"
#         }
#     }
# }
