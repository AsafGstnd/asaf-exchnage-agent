"""
Test and utility functions for standardizing university names in all relevant tables.
"""
from utils.config import supabase
from utils.pdf_processor import format_university_name

def standardize_extracted_texts_university_names():
    response = supabase.table("extracted_texts").select("country,university,file_name").execute()
    rows = response.data if response and hasattr(response, 'data') else []
    updated = 0
    updated_names = []
    for row in rows:
        raw_name = row["university"]
        mapped_name = format_university_name(raw_name)
        if raw_name != mapped_name:
            collision_resp = supabase.table("extracted_texts").select("*").eq("country", row["country"]).eq("university", mapped_name).eq("file_name", row["file_name"]).execute()
            collision_exists = collision_resp.data and len(collision_resp.data) > 0
            if collision_exists:
                print(f"Deleting duplicate row for: country={row['country']}, university={raw_name}, file_name={row['file_name']}")
                supabase.table("extracted_texts").delete().eq("country", row["country"]).eq("university", raw_name).eq("file_name", row["file_name"]).execute()
                updated += 1
                updated_names.append((row["country"], raw_name, mapped_name, row["file_name"]))
            else:
                print(f"Updating university name: {raw_name} -> {mapped_name}")
                supabase.table("extracted_texts").update({"university": mapped_name}).eq("country", row["country"]).eq("university", raw_name).eq("file_name", row["file_name"]).execute()
                updated += 1
                updated_names.append((row["country"], raw_name, mapped_name, row["file_name"]))
    print(f"Total updated university names: {updated}")
    return updated_names

def standardize_factsheets_chunks_university_names():
    response = supabase.table("factsheets_chunks").select("country,university,file_name,chunk_index").execute()
    rows = response.data if response and hasattr(response, 'data') else []
    updated = 0
    updated_names = []
    for row in rows:
        raw_name = row["university"]
        mapped_name = format_university_name(raw_name)
        if raw_name != mapped_name:
            collision_resp = supabase.table("factsheets_chunks").select("*") \
                .eq("country", row["country"]) \
                .eq("university", mapped_name) \
                .eq("file_name", row["file_name"]) \
                .eq("chunk_index", row["chunk_index"]) \
                .execute()
            collision_exists = collision_resp.data and len(collision_resp.data) > 0
            if collision_exists:
                print(f"Deleting duplicate row for: country={row['country']}, university={raw_name}, file_name={row['file_name']}, chunk_index={row['chunk_index']}")
                supabase.table("factsheets_chunks").delete() \
                    .eq("country", row["country"]) \
                    .eq("university", raw_name) \
                    .eq("file_name", row["file_name"]) \
                    .eq("chunk_index", row["chunk_index"]) \
                    .execute()
                updated += 1
                updated_names.append((row["country"], raw_name, mapped_name, row["file_name"], row["chunk_index"]))
            else:
                print(f"Updating university name: {raw_name} -> {mapped_name}")
                supabase.table("factsheets_chunks").update({"university": mapped_name}) \
                    .eq("country", row["country"]) \
                    .eq("university", raw_name) \
                    .eq("file_name", row["file_name"]) \
                    .eq("chunk_index", row["chunk_index"]) \
                    .execute()
                updated += 1
                updated_names.append((row["country"], raw_name, mapped_name, row["file_name"], row["chunk_index"]))
    print(f"Total updated university names in factsheets_chunks: {updated}")
    return updated_names

def standardize_universities_requirements_names():
    response = supabase.table("universities_requirements").select("name,country").execute()
    rows = response.data if response and hasattr(response, 'data') else []
    updated = 0
    updated_names = []
    for row in rows:
        raw_name = row["name"]
        mapped_name = format_university_name(raw_name)
        if raw_name != mapped_name:
            collision_resp = supabase.table("universities_requirements").select("*") \
                .eq("country", row["country"]) \
                .eq("name", mapped_name) \
                .execute()
            collision_exists = collision_resp.data and len(collision_resp.data) > 0
            if collision_exists:
                print(f"Deleting duplicate row for: country={row['country']}, name={raw_name}")
                supabase.table("universities_requirements").delete() \
                    .eq("country", row["country"]) \
                    .eq("name", raw_name) \
                    .execute()
                updated += 1
                updated_names.append((row["country"], raw_name, mapped_name))
            else:
                print(f"Updating university name: {raw_name} -> {mapped_name}")
                supabase.table("universities_requirements").update({"name": mapped_name}) \
                    .eq("country", row["country"]) \
                    .eq("name", raw_name) \
                    .execute()
                updated += 1
                updated_names.append((row["country"], raw_name, mapped_name))
    print(f"Total updated university names in universities_requirements: {updated}")
    return updated_names

def standardize_factsheets_chunks_country_names():
    """
    Standardizes country names in factsheets_chunks table to lowercase and spaces (not underscores).
    If a row with the standardized country name already exists for the same (university, file_name, chunk_index), deletes the current row.
    Otherwise, updates the country name.
    """
    from utils.config import supabase

    response = supabase.table("factsheets_chunks").select("country,university,file_name,chunk_index").execute()
    rows = response.data if response and hasattr(response, 'data') else []
    updated = 0
    updated_countries = []
    for row in rows:
        raw_country = row["country"]
        std_country = raw_country.lower().replace("_", " ").strip()
        if raw_country != std_country:
            # Check for collision: does a row with the standardized country already exist?
            collision_resp = supabase.table("factsheets_chunks").select("*") \
                .eq("country", std_country) \
                .eq("university", row["university"]) \
                .eq("file_name", row["file_name"]) \
                .eq("chunk_index", row["chunk_index"]) \
                .execute()
            collision_exists = collision_resp.data and len(collision_resp.data) > 0
            if collision_exists:
                print(f"Deleting duplicate row for: country={raw_country}, university={row['university']}, file_name={row['file_name']}, chunk_index={row['chunk_index']}")
                supabase.table("factsheets_chunks").delete() \
                    .eq("country", raw_country) \
                    .eq("university", row["university"]) \
                    .eq("file_name", row["file_name"]) \
                    .eq("chunk_index", row["chunk_index"]) \
                    .execute()
                updated += 1
                updated_countries.append((raw_country, std_country, row["university"], row["file_name"], row["chunk_index"]))
            else:
                print(f"Updating country name: {raw_country} -> {std_country}")
                supabase.table("factsheets_chunks").update({"country": std_country}) \
                    .eq("country", raw_country) \
                    .eq("university", row["university"]) \
                    .eq("file_name", row["file_name"]) \
                    .eq("chunk_index", row["chunk_index"]) \
                    .execute()
                updated += 1
                updated_countries.append((raw_country, std_country, row["university"], row["file_name"], row["chunk_index"]))
    print(f"Total updated country names in factsheets_chunks: {updated}")
    return updated_countries

def standardize_universities_requirements_country_names():
    """
    Standardizes country names in universities_requirements table to lowercase and spaces (not underscores).
    If a row with the standardized country name already exists for the same name, deletes the current row.
    Otherwise, updates the country name.
    """
    from utils.config import supabase

    response = supabase.table("universities_requirements").select("name,country").execute()
    rows = response.data if response and hasattr(response, 'data') else []
    updated = 0
    updated_countries = []
    for row in rows:
        raw_country = row["country"]
        std_country = raw_country.lower().replace("_", " ").strip()
        if raw_country != std_country:
            # Check for collision: does a row with the standardized country already exist?
            collision_resp = supabase.table("universities_requirements").select("*") \
                .eq("country", std_country) \
                .eq("name", row["name"]) \
                .execute()
            collision_exists = collision_resp.data and len(collision_resp.data) > 0
            if collision_exists:
                print(f"Deleting duplicate row for: country={raw_country}, name={row['name']}")
                supabase.table("universities_requirements").delete() \
                    .eq("country", raw_country) \
                    .eq("name", row["name"]) \
                    .execute()
                updated += 1
                updated_countries.append((raw_country, std_country, row["name"]))
            else:
                print(f"Updating country name: {raw_country} -> {std_country}")
                supabase.table("universities_requirements").update({"country": std_country}) \
                    .eq("country", raw_country) \
                    .eq("name", row["name"]) \
                    .execute()
                updated += 1
                updated_countries.append((raw_country, std_country, row["name"]))
    print(f"Total updated country names in universities_requirements: {updated}")
    return updated_countries

if __name__ == "__main__":
    print("\n--- Standardizing University Names in extracted_texts ---")
    updated_names = standardize_extracted_texts_university_names()
    if updated_names:
        print("\nUpdated university names in extracted_texts:")
        for country, old_name, new_name, file_name in updated_names:
            print(f"  country={country}, old='{old_name}', new='{new_name}', file='{file_name}'")
    else:
        print("No university names needed updating in extracted_texts.")

    print("\n--- Standardizing University Names in factsheets_chunks ---")
    updated_chunk_names = standardize_factsheets_chunks_university_names()
    if updated_chunk_names:
        print("\nUpdated university names in factsheets_chunks:")
        for country, old_name, new_name, file_name, chunk_index in updated_chunk_names:
            print(f"  country={country}, old='{old_name}', new='{new_name}', file='{file_name}', chunk_index={chunk_index}")
    else:
        print("No university names needed updating in factsheets_chunks.")

    print("\n--- Standardizing University Names in universities_requirements ---")
    updated_req_names = standardize_universities_requirements_names()
    if updated_req_names:
        print("\nUpdated university names in universities_requirements:")
        for country, old_name, new_name in updated_req_names:
            print(f"  country={country}, old='{old_name}', new='{new_name}'")
    else:
        print("No university names needed updating in universities_requirements.")

    print("\n--- Standardizing Country Names in factsheets_chunks ---")
    updated_country_names = standardize_factsheets_chunks_country_names()
    if updated_country_names:
        print("\nUpdated country names in factsheets_chunks:")
        for raw_country, std_country, university, file_name, chunk_index in updated_country_names:
            print(f"  old='{raw_country}', new='{std_country}', university='{university}', file='{file_name}', chunk_index={chunk_index}")
    else:
        print("No country names needed updating in factsheets_chunks.")

    print("\n--- Standardizing Country Names in universities_requirements ---")
    updated_country_names = standardize_universities_requirements_country_names()
    if updated_country_names:
        print("\nUpdated country names in universities_requirements:")
        for raw_country, std_country, name in updated_country_names:
            print(f"  old='{raw_country}', new='{std_country}', name='{name}'")
    else:
        print("No country names needed updating in universities_requirements.")
