import sys
import os
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from utils.llmod_client import llmod_chat
from utils.config import supabase
from utils.config import BASE_DIR

load_dotenv()


def get_structured_data(combined_row):
    """Takes aggregated text for a university and uses llmod_chat to extract requirements."""
    uni_name = combined_row.get("university", "")
    country = combined_row.get("country", "")
    text = combined_row.get("text", "")

    # Optional: Basic truncation to prevent API overload if texts are massive
    clean_text = text.strip()[:40000]

    system_prompt = """You are an expert academic advisor data-extraction bot. 
    Your ONLY job is to extract structured data from university fact sheets.
    You will be provided with one or more documents for the same university. If information conflicts, prioritize the most specific data. If multiple majors are restricted across different documents, include the union of all restricted majors.
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
    - `english_test_type`: Mandatory English tests (e.g., 'TOEFL'). Return [] ONLY if no test is required for ANYONE.
    - `waiver_available`: true if the test is required but exemptions exist (e.g., for native speakers or specific degree programs).
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
        "waiver_available": boolean,
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

    Text: {clean_text}
    """

    try:
        response_text = llmod_chat(system_prompt, user_prompt, use_json=True)
        return json.loads(response_text)
    except Exception as e:
        print(f"LLM Error for {uni_name}: {e}")
        return None


def process_single_university(uni_data):
    """Helper function to process a single university for multithreading."""
    uni, country, combined_text = uni_data

    combined_row = {
        "university": uni,
        "country": country,
        "text": combined_text
    }

    structured_data = get_structured_data(combined_row)

    if structured_data:
        return {
            "name": uni,
            "country": country,
            **structured_data
        }
    return None


def run_ingestion():
    # Fetch all rows from extracted_texts table
    response = supabase.table("extracted_texts").select("*").execute()
    rows = response.data if response and hasattr(response, 'data') else []
    print(f"Found {len(rows)} raw records in extracted_texts table.")

    # 1. Group Data by University
    grouped_data = defaultdict(list)
    for row in rows:
        key = (row.get("university"), row.get("country"))
        if row.get("text"):
            grouped_data[key].append(row.get("text").strip())

    # Prepare data payloads for the thread pool
    processing_queue = []
    for (uni, country), texts in grouped_data.items():
        combined_text = "\n\n--- NEXT DOCUMENT ---\n\n".join(texts)
        processing_queue.append((uni, country, combined_text))

    print(f"Aggregated into {len(processing_queue)} unique universities to process.")

    all_records = []

    # 2. Process Universities in Parallel (Batching)
    # Adjust max_workers depending on your llmod.ai API rate limits
    max_concurrent_requests = 5

    with ThreadPoolExecutor(max_workers=max_concurrent_requests) as executor:
        # Submit all tasks to the executor
        future_to_uni = {
            executor.submit(process_single_university, uni_data): uni_data[0]
            for uni_data in processing_queue
        }

        # Gather results as they complete
        for future in as_completed(future_to_uni):
            uni_name = future_to_uni[future]
            try:
                result = future.result()
                if result:
                    all_records.append(result)
                    print(f"Successfully processed: {uni_name}")
                else:
                    print(f"Failed to extract valid data for: {uni_name}")
            except Exception as e:
                print(f"Exception occurred processing {uni_name}: {e}")

    # 3. Bulk Upload to Supabase
    if all_records:
        try:
            supabase.table("universities_requirements").upsert(
                all_records,
                on_conflict="name,country"
            ).execute()
            print(f"\nSuccessfully ingested {len(all_records)} universities to Supabase.")
        except Exception as e:
            print(f"\nDatabase error during upsert: {e}")
            # Ensure your Supabase table actually has a unique constraint on (name, country)!


if __name__ == "__main__":
    run_ingestion()