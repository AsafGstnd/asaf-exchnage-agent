from utils.llmod_client import batch_embed_texts
from utils.db import supabase
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


from utils.config import BASE_DIR, CHUNK_SIZE, CHUNK_OVERLAP

def chunk_pdf_with_headers(row):
    """Chunk markdown text from a row in extracted_texts table using headers and recursive splitting."""
    md_text = row.get("text", "")

    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False
    )
    header_splits = header_splitter.split_text(md_text)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=[
            "\n# ",
            "\n## ",
            "\n\n",
            "\n- ",
            "\n",
            ". ",
            " ",
            ""
        ],
        add_start_index=True
    )
    final_chunks = text_splitter.split_documents(header_splits)
    return final_chunks

def process_pdfs_and_embed():
    all_chunks = []
    all_embeddings = []

    # Fetch all rows from extracted_texts table
    response = supabase.table("extracted_texts").select("*").execute()
    rows = response.data if response and hasattr(response, 'data') else []
    print(f"Found {len(rows)} records in extracted_texts table.")
    for row in rows:
        country = row.get("country", "")
        uni = row.get("university", "")
        file = row.get("file", "")
        try:
            chunks = chunk_pdf_with_headers(row)
        except Exception as e:
            print(f"Error processing {file} ({uni}, {country}): {e}")
            continue
        for chunk in chunks:
            all_chunks.append({
                "country": country,
                "university": uni,
                "file": file,
                "text": chunk.page_content,
                "header_metadata": chunk.metadata
            })
        chunk_texts = [chunk.page_content for chunk in chunks]
        if chunk_texts:
            embeddings = batch_embed_texts(chunk_texts)
            all_embeddings.extend(embeddings)
    return all_chunks, all_embeddings

if __name__ == "__main__":
    chunks, embeddings = process_pdfs_and_embed()
    print(f"Processed {len(chunks)} chunks and embeddings.")
