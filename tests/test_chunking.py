from data_pipeline.rag_embedding import chunk_pdf_with_headers, chunk_pdf_recursively
from utils.config import BASE_DIR, supabase
import random

def print_factsheet_chunk_metrics():
    """Prints average number of chunks per factsheet and other useful metrics from factsheets_chunks table."""
    from utils.config import supabase
    response = supabase.table("factsheets_chunks").select("country,university,file_name,chunk_index").execute()
    rows = response.data if response and hasattr(response, 'data') else []
    if not rows:
        print("No data in factsheets_chunks table.")
        return
    # Group by (country, university, file_name)
    from collections import defaultdict, Counter
    factsheet_chunk_counts = defaultdict(int)
    for row in rows:
        key = (row["country"], row["university"])  # count per university/country
        factsheet_chunk_counts[key] += 1
    chunk_counts = list(factsheet_chunk_counts.values())
    avg_chunks = sum(chunk_counts) / len(chunk_counts) if chunk_counts else 0
    min_chunks = min(chunk_counts) if chunk_counts else 0
    max_chunks = max(chunk_counts) if chunk_counts else 0
    print(f"Total universities: {len(chunk_counts)}")
    print(f"Total chunks: {len(rows)}")
    print(f"Average chunks per university: {avg_chunks:.2f}")
    print(f"Min chunks per university: {min_chunks}")
    print(f"Max chunks per university: {max_chunks}")
    # Optionally, print a histogram
    hist = Counter(chunk_counts)
    print("\nChunks per university histogram:")
    for num_chunks, count in sorted(hist.items()):
        print(f"  {num_chunks} chunks: {count} universities")

    # Show how many universities have 0 factsheets
    # Get all universities from extracted_texts table
    extracted_resp = supabase.table("extracted_texts").select("country,university").execute()
    extracted_rows = extracted_resp.data if extracted_resp and hasattr(extracted_resp, 'data') else []
    all_university_keys = set((row["country"], row["university"]) for row in extracted_rows)
    with_chunks = set(factsheet_chunk_counts.keys())
    zero_chunk_keys = all_university_keys - with_chunks
    print(f"\nUniversities with 0 factsheet chunks: {len(zero_chunk_keys)}")
    if zero_chunk_keys:
        print("Examples:")
        for key in list(zero_chunk_keys)[:10]:
            print(f"  country={key[0]}, university={key[1]}")

def test_sample_and_chunk():
    import sys
    from utils.config import supabase
    # Optionally take a row id as input
    row_id = sys.argv[1] if len(sys.argv) > 1 else None
    if row_id:
        response = supabase.table("extracted_texts").select("*").eq("id", row_id).execute()
        row = response.data[0] if response.data else None
        print(f"Sampled by id: {row_id}")
    else:
        # Sample a random row (Supabase workaround)
        count_response = supabase.table("extracted_texts").select("*", count="exact").limit(1).execute()
        total_rows = count_response.count if hasattr(count_response, 'count') else 0
        if total_rows > 0:
            random_index = random.randint(0, total_rows - 1)
            response = supabase.table("extracted_texts").select("*").range(random_index, random_index).execute()
            row = response.data[0] if response.data else None
            print(f"Sampled a random row (index {random_index}) from extracted_texts.")
        else:
            row = None
            print("No rows found in extracted_texts table.")
    if row:
        print(f"Sampled row: university={row.get('university')}, country={row.get('country')}")
        chunks = chunk_pdf_recursively(row)
        for i, chunk in enumerate(chunks, 1):
            print(f"\n--- Chunk {i} ---")
            print(f"Content:\n{chunk.page_content}\n")
            print(f"Header Metadata: {chunk.metadata}\n")
        print(f"\nTotal chunks: {len(chunks)}")
    else:
        print("No row found in extracted_texts table.")

def get_factsheets_by_chunk_count(min_chunks=1, max_chunks=25):
    """
    Returns two lists of (university, file_name) pairs:
    - Those with chunk count <= min_chunks
    - Those with chunk count >= max_chunks
    Args:
        min_chunks (int): Maximum allowed chunk count for the first group (inclusive).
        max_chunks (int): Minimum allowed chunk count for the second group (inclusive).
    """
    from utils.config import supabase
    response = supabase.table("factsheets_chunks").select("university,file_name").execute()
    rows = response.data if response and hasattr(response, 'data') else []
    from collections import defaultdict
    chunk_counts = defaultdict(int)
    for row in rows:
        key = (row["university"], row["file_name"])
        chunk_counts[key] += 1
    below = [key for key, count in chunk_counts.items() if count <= min_chunks]
    above = [key for key, count in chunk_counts.items() if count >= max_chunks]
    print(f"Factsheets with <= {min_chunks} chunks: {below}")
    print(f"Factsheets with >= {max_chunks} chunks: {above}")
    return below, above

def chunk_extracted_text_by_uni_file(university, file_name, chunker=chunk_pdf_recursively):
    """
    Fetches the extracted_texts row for the given university and file_name, chunks its text, and returns the chunks.
    Args:
        university (str): University name
        file_name (str): File name
        chunker (callable): Chunking function to use (default: chunk_pdf_recursively)
    Returns:
        List of chunk objects
    """
    from utils.config import supabase
    response = supabase.table("extracted_texts").select("*").eq("university", university).eq("file_name", file_name).limit(1).execute()
    row = response.data[0] if response and hasattr(response, 'data') and response.data else None
    if not row:
        print(f"No extracted_texts row found for university={university}, file_name={file_name}")
        return []
    print(f"Chunking extracted_texts for university={university}, file_name={file_name}")
    chunks = chunk_pdf_recursively(row)
    print(f"Total chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks, 1):
        print(f"\n--- Chunk {i} ---")
        print(f"Content:\n{chunk.page_content}\n")
        print(f"Header Metadata: {chunk.metadata}\n")
    return chunks


if __name__ == "__main__":
    # test_sample_and_chunk()
    print("\n--- Factsheet Chunk Metrics ---")
    print_factsheet_chunk_metrics()
    # below, above = get_factsheets_by_chunk_count()
    # print(f"\nFactsheets with <= 3 chunks: {len(below)}")
    # print(below)
    # print(f"\nFactsheets with >= 20 chunks: {len(above)}")
    # print(above)
    # chunk_extracted_text_by_uni_file("alexandru_ioan_cuza_university_of_iasi", "factsheet.pdf")

   