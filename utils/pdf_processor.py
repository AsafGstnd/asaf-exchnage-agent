import os
import pymupdf4llm
from utils.config import supabase

BASE_DIR = "data\external_universities"

def format_university_name(raw_name: str) -> str:
    """Maps raw directory names to clean, formatted university names."""
    
    name_mapping = {
        "technical_university_of_crete": "Technical University of Crete",
        "institut_supbiotech_de_paris": "Institut Supbiotech de Paris",
        "ece_engineering_school": "ECE Engineering School",
        "Alexandru Ioan Cuza University of Iasi": "Alexandru Ioan Cuza University of Iasi",
        "Politecnico di Torino": "Politecnico di Torino",
        "politecnico_di_milano": "Politecnico di Milano",
        "Instituto Tecnológico de Buenos Aires": "Instituto Tecnológico de Buenos Aires",
        "Universidad de Palermo": "Universidad de Palermo",
        "MCI Management Center Innsbruck": "MCI Management Center Innsbruck",
        "Concordia University": "Concordia University",
        "McGill University": "McGill University",
        "Polytechnique Montréal": "Polytechnique Montréal",
        "Universidad Francisco de Vitoria (Madrid)": "Universidad Francisco de Vitoria (Madrid)",
        "University of British Columbia": "University of British Columbia",
        "University of Manitoba": "University of Manitoba",
        "University of Toronto": "University of Toronto",
        "kaist": "KAIST",
        "itesm_monterrey": "ITESM Monterrey",
        "university_of_erlangen_nuremberg": "University of Erlangen-Nuremberg",
        "Pontificia Universidad Catolica de Chile (PUC)": "Pontificia Universidad Catolica de Chile (PUC)",
        "East China Normal University": "East China Normal University",
        "Tongji University": "Tongji University",
        "Shanghai Jiao Tong University (SJTU)": "Shanghai Jiao Tong University (SJTU)",
        "Nanjing University": "Nanjing University",
        "Nankai University": "Nankai University",
        "Guangdong Technion - Israel Institute of Technology": "Guangdong Technion - Israel Institute of Technology",
        "Peking University": "Peking University",
        "Shandong University": "Shandong University",
        "University of Science and Technology of China": "University of Science and Technology of China",
        "Tsinghua University": "Tsinghua University",
        "friedrich_schiller_university_jena": "Friedrich Schiller University Jena",
        "technical_university_of_munich": "Technical University of Munich",
        "technical_university_of_berlin": "Technical University of Berlin",
        "University of Cyprus": "University of Cyprus",
        "Czech Technical University": "Czech Technical University",
        "Inteli Institute of Technology and Leadership": "Inteli Institute of Technology and Leadership",
        "Technical University of Denmark (DTU)": "Technical University of Denmark (DTU)",
        "HEC School of Management": "HEC School of Management",
        "ENSCM National School of Chemistry Montpellier": "ENSCM National School of Chemistry Montpellier",
        "Ecole Polytechnique Paris": "Ecole Polytechnique Paris",
        "Ecole Centrale Marseille": "Ecole Centrale Marseille",
        "CentraleSupélec": "CentraleSupélec",
        "PSL Dauphine": "PSL Dauphine",
        "EPF – Engineering School": "EPF – Engineering School",
        "ECAM Strasbourg": "ECAM Strasbourg",
        "vinuniversity": "VinUniversity",
        "university_of_connecticut": "University of Connecticut",
        "university_of_oregon": "University of Oregon",
        "anhalt_university_of_applied_sciences": "Anhalt University of Applied Sciences",
        "karlsruhe_institute_of_technology": "Karlsruhe Institute of Technology",
        "leibniz_universität_hannover": "Leibniz Universität Hannover",
        "technical_university_darmstadt": "Technical University Darmstadt",
        "university_of_applied_sciences_bielefeld": "University of Applied Sciences Bielefeld",
        "rwth_aachen_university": "RWTH Aachen University",
        "hong_kong_university_of_science_and_technology": "Hong Kong University of Science and Technology",
        "city_university_of_hong_kong": "City University of Hong Kong",
        "iiit_pune": "IIIT Pune",
        "sapienza_university_of_rome": "Sapienza University of Rome",
        "national_university_corporation_kyushu_university": "Kyushu University",
        "udlap": "UDLAP",
        "wroclaw_university_of_technology": "Wroclaw University of Technology",
        "handong_global_university": "Handong Global University",
        "postech_university": "POSTECH University",
        "ajou_university": "Ajou University",
        "sungkyunkwan_university": "Sungkyunkwan University",
        "école_polytechnique_fédérale_de_lausanne": "École Polytechnique Fédérale de Lausanne",
        "academia_sinica": "Academia Sinica",
        "national_cheng_kung_university": "National Cheng Kung University",
        "national_taiwan_university": "National Taiwan University",
        "national_tsing_hua_university": "National Tsing Hua University",
        "national_yang_ming_chiao_tung_university": "National Yang Ming Chiao Tung University",
        "universidad_ort_uruguay": "Universidad ORT Uruguay",
        "carnegie_mellon_university": "Carnegie Mellon University",
        "cornell_university": "Cornell University"
    }

    return name_mapping.get(raw_name, raw_name)

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
    formatted_university = format_university_name(university)
    file_name = parts[2] if len(parts) > 2 else os.path.basename(pdf_path)
    data = {
        "country": country,
        "university": formatted_university,
        "file_name": file_name,
        "text": text
    }
    supabase.table("extracted_texts").upsert(
        data, 
        on_conflict="country,university,file_name"
        ).execute()
    return f"{country}/{university}/{file_name}"

def load_text(pdf_path):
    """Load the full row from Supabase extracted_texts table, else return None."""
    rel_path = os.path.relpath(pdf_path, BASE_DIR)
    parts = rel_path.split(os.sep)
    country = parts[0] if len(parts) > 0 else ""
    university = parts[1] if len(parts) > 1 else ""
    file_name = parts[2] if len(parts) > 2 else os.path.basename(pdf_path)
    response = supabase.table("extracted_texts").select("*").eq("country", country).eq("university", university).eq("file_name", file_name).execute()
    if response.data and len(response.data) > 0:
        return response.data[0]
    return None

def load_text_by_key(country, university, file_name):
    """Load text from Supabase extracted_texts table using key fields."""
    response = supabase.table("extracted_texts").select("text").eq("country", country).eq("university", university).eq("file_name", file_name).execute()
    if response.data and len(response.data) > 0:
        return response.data[0]["text"]
    return None

def is_target_factsheet(filename: str) -> bool:
    """
    Evaluates a filename to ensure ONLY factsheets, overviews, flyers, 
    and general info sheets are processed, strictly blocking course catalogs.
    """
    lower_name = filename.lower()
    
    # Substrings based checks for Non factsheet indicators
    excluded_keywords = [
        "course", 
        "catalog", 
        "catalogue",
        "syllabus"
    ]
    
    if any(blocked in lower_name for blocked in excluded_keywords):
        return False
        
    return True

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
            for file_name in os.listdir(uni_path):
                if file_name.endswith(".pdf"):
                    pdf_path = os.path.join(uni_path, file_name)
                    if is_target_factsheet(file_name):
                        print(f"  [+] Saving: {file_name}")
                        save_text(pdf_path) 
                    else:
                        print(f"  [-] Skipping (Not a factsheet) {file_name}")
                 

if __name__ == "__main__":
    fill_full_texts_table()




