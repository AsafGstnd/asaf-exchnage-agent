import os
import pymupdf4llm
from utils.db import supabase

BASE_DIR = "data\external_universities"

def extract_markdown_from_pdf(pdf_path: str) -> str:
    """Extracts markdown text from PDF using pymupdf4llm."""
    try:
        md_text = pymupdf4llm.to_markdown(pdf_path)
        if not md_text:
            print(f"No markdown text found in {pdf_path}.")
        return md_text
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return ""

def save_text(pdf_path):
    """Extract markdown from PDF and save to Supabase, extracting info from path."""
    text = extract_markdown_from_pdf(pdf_path)
    rel_path = os.path.relpath(pdf_path, BASE_DIR)
    print(f"[DEBUG] rel_path: {rel_path}")
    parts = rel_path.split(os.sep)
    print(f"[DEBUG] parts: {parts}")
    country = parts[0] if len(parts) > 0 else ""
    university = parts[1] if len(parts) > 1 else ""
    file = parts[2] if len(parts) > 2 else os.path.basename(pdf_path)
    data = {
        "country": country,
        "university": university,
        "file": file,
        "text": text
    }
    print(f"[DEBUG] data to upsert: {data}")
    supabase.table("extracted_texts").upsert(data).execute()
    return f"{country}/{university}/{file}"

def load_text(pdf_path):
    """Load the full row from Supabase extracted_texts table, else return None."""
    rel_path = os.path.relpath(pdf_path, BASE_DIR)
    parts = rel_path.split(os.sep)
    country = parts[0] if len(parts) > 0 else ""
    university = parts[1] if len(parts) > 1 else ""
    file = parts[2] if len(parts) > 2 else os.path.basename(pdf_path)
    response = supabase.table("extracted_texts").select("*").eq("country", country).eq("university", university).eq("file", file).execute()
    if response.data and len(response.data) > 0:
        return response.data[0]
    return None

def load_text_by_key(country, university, file):
    """Load text from Supabase extracted_texts table using key fields."""
    response = supabase.table("extracted_texts").select("text").eq("country", country).eq("university", university).eq("file", file).execute()
    if response.data and len(response.data) > 0:
        return response.data[0]["text"]
    return None


def fill_full_texts_table():
    """Walk through BASE_DIR and save all PDF texts to Supabase using save_text."""
    if not os.path.exists(BASE_DIR):
        print(f"Error: Directory {BASE_DIR} not found.")
        return

    for country in os.listdir(BASE_DIR):
        country_path = os.path.join(BASE_DIR, country)
        if not os.path.isdir(country_path):
            continue
        for uni in os.listdir(country_path):
            uni_path = os.path.join(country_path, uni)
            if not os.path.isdir(uni_path):
                continue
            print(f"--- Processing: {uni} ({country}) ---")
            for file in os.listdir(uni_path):
                if file.endswith(".pdf"):
                    pdf_path = os.path.join(uni_path, file)
                    print(f"Saving: {pdf_path}")
                    save_text(pdf_path)




