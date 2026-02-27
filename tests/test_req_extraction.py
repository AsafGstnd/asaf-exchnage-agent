from data_pipeline.universities_requirments import get_structured_data

if __name__ == "__main__":
    # Specify the key fields for the row you want to test
    country = "taiwan"
    university = "national_taiwan_university"
    file = "factsheet.pdf"

    # Load the row from extracted_texts table by key
    from utils.config import supabase
    response = supabase.table("extracted_texts").select("*").eq("country", country).eq("university", university).eq("file_name", file).execute()
    row = response.data[0] if response and hasattr(response, 'data') and response.data else None

    if row:
        structured = get_structured_data(row)
        print("Structured requirements:")
        print(structured)
    else:
        print("No row found for the specified keys.")
