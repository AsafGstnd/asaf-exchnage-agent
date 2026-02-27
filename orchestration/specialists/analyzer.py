import os
import json
from pinecone_db.pinecone_client import query_embedding
from utils.config import supabase
from utils.llmod_client import llmod_chat

def analyze_universities(top_universities, universities_fit_text=None, return_steps=False):
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
    # catch all category chunks in the vector DB
    rag_query_keywords = (
        "evaluation cost, minimum ECTS, course requirements, "
        "visa process, health insurance, student accommodation, city life"
    )
    analysis_results = []
    steps = []

    system_prompt = """You are an expert data extraction AI for a university exchange program.
    Your exact job is to read factsheet context and extract specific variables into a strict JSON format.

    EXTRACTION RULES:
    1. Strict Schema: You must output ONLY valid JSON matching the exact structure below. Do not add keys.
    2. Missing Data: If a detail is missing from the text, output null (do not output "N/A" or "None").
    3. Type Enforcement: Booleans must be true/false. Integers must be numbers only (e.g., output 300, not "300 euros").
    4. Cost Estimation: Base your cost estimates on the provided text/tables. If exact figures are missing, you must still provide a brief 
        estimated total cost based on the table, and also slightly include your own knowledge on the specific city and country the university is in.
    5. Summaries: Keep the `_summary_notes` fields STRICTLY to 1-2 sentences. Highlight critical edge cases (e.g., "Visa requires 3 months", 
        "Housing is lottery-only", or note the local currency).

    REQUIRED JSON SCHEMA:
    {
        "academic": {
            "min_credits_required": "int or null",
            "max_credits_allowed": "int or null",
            "academic_summary_notes": "string or null" 
        },
        "housing_and_logistics": {
            "campus_housing_guaranteed": "boolean",
            "university_sponsors_visa": "boolean",
            "estimated_visa_processing_months": "int or null",
            "mandatory_insurance_required": "boolean",
            "estimated_housing_cost_per_month": "int or null",
            "estimated_living_cost_per_month": "int or null",
            "logistics_summary_notes": "string or null"
        },
        "student_integration": {
            "buddy_program_available": "boolean",
            "orientation_program_provided": "boolean",
            "orientation_is_mandatory": "boolean",
            "integration_summary_notes": "string or null"
        }
    }"""

    for idx, uni_name in enumerate(top_universities):
        filter_param = {"university": uni_name}
        retrieved_chunks = query_embedding(rag_query_keywords, filter=filter_param)        
        context_text = "\n".join(retrieved_chunks) if isinstance(retrieved_chunks, list) else ""

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
        
        # Unpack all fields from supabase row into uni_analysis
        uni_analysis = {
            "university_name": uni_name,
            **eligibility_and_framework,
            "logistics_and_experience": logistics_and_experience_dict,
            "general_fit_reasoning": universities_fit_text[idx] if universities_fit_text and idx < len(universities_fit_text) else None
        }
        
        analysis_results.append(uni_analysis)
    if return_steps:
        return analysis_results, steps
    return analysis_results
