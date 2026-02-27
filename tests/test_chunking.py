import os
from data_pipeline.rag_embedding import chunk_pdf_with_headers
from utils.config import BASE_DIR
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
        key = (row["country"], row["university"], row["file_name"])
        factsheet_chunk_counts[key] += 1
    chunk_counts = list(factsheet_chunk_counts.values())
    avg_chunks = sum(chunk_counts) / len(chunk_counts) if chunk_counts else 0
    min_chunks = min(chunk_counts) if chunk_counts else 0
    max_chunks = max(chunk_counts) if chunk_counts else 0
    print(f"Total factsheets: {len(chunk_counts)}")
    print(f"Total chunks: {len(rows)}")
    print(f"Average chunks per factsheet: {avg_chunks:.2f}")
    print(f"Min chunks per factsheet: {min_chunks}")
    print(f"Max chunks per factsheet: {max_chunks}")
    # Optionally, print a histogram
    hist = Counter(chunk_counts)
    print("\nChunks per factsheet histogram:")
    for num_chunks, count in sorted(hist.items()):
        print(f"  {num_chunks} chunks: {count} factsheets")

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
        chunks = chunk_pdf_with_headers(row)
        for i, chunk in enumerate(chunks, 1):
            print(f"\n--- Chunk {i} ---")
            print(f"Content:\n{chunk.page_content}\n")
            print(f"Header Metadata: {chunk.metadata}\n")
        print(f"\nTotal chunks: {len(chunks)}")
    else:
        print("No row found in extracted_texts table.")

if __name__ == "__main__":
    # test_sample_and_chunk()
    print("\n--- Factsheet Chunk Metrics ---")
    print_factsheet_chunk_metrics()
