import os
from utils.config import BASE_DIR

def test_directories_content():
    """
    Walks through the directory tree and prints all files in a readable tree format 
    to help design an accurate keyword filter.
    """
    if not os.path.exists(BASE_DIR):
        print(f"Error: Directory '{BASE_DIR}' not found. Please check the path.")
        return

    total_files = 0
    total_universities = 0

    print(f"--- Directory Audit for: {BASE_DIR} ---\n")

    for country in os.listdir(BASE_DIR):
        country_path = os.path.join(BASE_DIR, country)
        if not os.path.isdir(country_path):
            continue
            
        print(f"📁 {country}")
        
        for university in os.listdir(country_path):
            university_path = os.path.join(country_path, university)
            if not os.path.isdir(university_path):
                continue
                
            total_universities += 1
            print(f"  └── 🏫 {university}")
            
            # Get all files in the university folder
            files = os.listdir(university_path)
            
            if not files:
                print("      (Empty directory)")
                continue

            for file in files:
                total_files += 1
                # Check if it's a PDF or something else
                if file.lower().endswith('.pdf'):
                    print(f"      📄 {file}")
                else:
                    print(f"      ⚠️  {file} (Not a PDF)")
                
    print(f"\n--- Audit Complete ---")
    print(f"Total Universities: {total_universities}")
    print(f"Total Files Found: {total_files}")

if __name__ == "__main__":
    test_directories_content()