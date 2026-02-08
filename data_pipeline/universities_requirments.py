import os
import json
from dotenv import load_dotenv
from utils.llmod_client import llmod_chat
from utils.db import supabase
from utils.config import BASE_DIR

load_dotenv()

def get_structured_data(row):
    """Takes a row from extracted_texts table and uses llmod_chat to extract requirements."""
    # row schema: {country, university, file, text}
    uni_name = row.get("university", "")
    country = row.get("country", "")
    text = row.get("text", "")
    clean_text = text.strip()

    system_prompt = "You are an expert academic advisor. You return ONLY valid JSON."

    user_prompt = f"""
    Extract the exchange requirements for {uni_name} in {country} from the text below.

    Rules for extraction:
    1. Look for the general minimum GPA. If faculty-specific GPAs exist, provide the strictest one.
    2. For language, extract the CEFR level (e.g., B2) or specific scores.
    3. Determine if the university is part of the Erasmus+ network based on the text.

    Return ONLY a JSON object with these exact keys:
{{
    "min_gpa": float or null,
    "lang_instruction": "string (e.g., 'English' or 'Danish/English')",
    "lang_level_req": "string (e.g., 'B2' or 'C1')",
    "test_required": boolean,
    "waiver_conditions": ["list of strings"],
    "restricted_majors": ["list of strings"],
    "level_allowed": "string (BSc, MSc, or Both)",
    "min_semesters_completed": int or null,
    "semester_dates": "string summary",
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