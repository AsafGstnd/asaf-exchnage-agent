import os
from utils.pdf_processor import save_text, load_text
from data_pipeline.rag_embedding import chunk_pdf_with_headers
from utils.config import BASE_DIR

if __name__ == "__main__":
    sample_pdf = os.path.join(BASE_DIR, 'taiwan', 'national_taiwan_university', 'sample.pdf')
    print(sample_pdf)
    saved_path = save_text(sample_pdf)
    print(f"Saved record path: {saved_path}")
    row = load_text(sample_pdf)
    if row:
        chunks = chunk_pdf_with_headers(row)
        for i, chunk in enumerate(chunks, 1):
            print(f"\n--- Chunk {i} ---")
            print(f"Content:\n{chunk.page_content}\n")
            print(f"Header Metadata: {chunk.metadata}\n")
        print(f"\nTotal chunks: {len(chunks)}")
    else:
        print("No row found in extracted_texts table for the sample PDF.")
