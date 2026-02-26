import os
import json
from dotenv import load_dotenv
from utils.llmod_client import llmod_chat
from utils.config import supabase
from utils.config import BASE_DIR

load_dotenv()

def get_structured_data(row):
    """Takes a row from extracted_texts table and uses llmod_chat to extract requirements."""
    # row schema: {country, university, file, text}
    uni_name = row.get("university", "")
    country = row.get("country", "")
    text = row.get("text", "")
    clean_text = text.strip()

    system_prompt = """You are an expert academic advisor data-extraction bot. 
    Your ONLY job is to extract structured data from university fact sheets.
    You must strictly follow the requested JSON schema.
    Never include conversational filler, markdown formatting outside of the JSON block, or explanations.
    If a piece of information is missing, use null.
    Return ONLY valid, parseable JSON."""

    user_prompt = f"""
    Extract the exchange requirements for {uni_name} in {country} from the text below.

    Extraction Rules:
    1. Academic: `min_gpa` is the absolute lowest baseline. `msc_allowed` is true ONLY if Master's/graduate exchange is explicitly permitted.
    2. Language Chain: 
    - `non_english_languages`: Mandatory non-English languages (else []).
    - `english_only_possible`: true IFF `non_english_languages` is [].
    - `english_test_type`: Mandatory English tests (e.g., 'TOEFL'). Return [] if ANY waivers exist (e.g., native speakers) or no test is required.
    - `test_required`: true IFF `english_test_type` is not [].
    - `english_test_level`: Map the requirement STRICTLY to a CEFR level (A1, A2, B1, B2, C1, C2). Return null if `test_required` is false.
    3. Dates: Teaching dates only (ignore application/nomination deadlines). Months (1-12) and Days (1-31) as integers. Null if missing.
    4. Restrictions (`restricted_majors`): 
    - Extract as a list of standard, universally recognized academic major names (e.g., ["Medicine", "Business"]).
    - Split combined faculties into separate strings (e.g., "Math and Physics" becomes ["Mathematics", "Physics"]).
    - ONLY list a major if the ENTIRE department is restricted.
    - STRICTLY IGNORE individual courses, practicums, administrative offices, language centers, continuing education, and summer programs.   
    5. Erasmus: `erasmus_available` is true if Erasmus+ is explicitly mentioned.
    
    Return ONLY a JSON object with these exact keys:
    {{
        "min_gpa": float or null,
        "non_english_languages": ["list of strings"],
        "english_test_type": ["list of strings"],
        "english_test_level": "string or null",
        "english_only_possible": boolean,
        "test_required": boolean,
        "restricted_majors": ["list of standard major names"],
        "msc_allowed": boolean,
        "min_semesters_completed": int or null,
        "fall_semester": {{
            "start_month": int or null,
            "start_day": int or null,
            "end_month": int or null,
            "end_day": int or null
        }},
        "spring_semester": {{
            "start_month": int or null,
            "start_day": int or null,
            "end_month": int or null,
            "end_day": int or null
        }},
        "erasmus_available": boolean
    }}
    
    Text: {clean_text[:30000]}
    """

    try:
        response_text = llmod_chat(system_prompt, user_prompt, use_json=True)
        return json.loads(response_text)
    except Exception as e:
        print(f"LLM Error for {uni_name}: {e}")
        return None


def run_ingestion():
    all_records = []
    # Fetch all rows from extracted_texts table
    response = supabase.table("extracted_texts").select("*").execute()
    rows = response.data if response and hasattr(response, 'data') else []
    print(f"Found {len(rows)} records in extracted_texts table.")
    for row in rows:
        uni = row.get("university", "")
        country = row.get("country", "")
        print(f"--- Processing: {uni} ({country}) ---")
        structured_data = get_structured_data(row)
        if structured_data:
            record = {
                "name": uni,
                "country": country,
                **structured_data
            }
            all_records.append(record)

    # Bulk upload using upsert to avoid duplicates
    if all_records:
        try:
            supabase.table("universities_requirements").upsert(all_records).execute()
            print(f"\nSuccessfully ingested {len(all_records)} universities to Supabase (universities_requirements table).")
        except Exception as e:
            print(f"Database error: {e}")

if __name__ == "__main__":
    run_ingestion()