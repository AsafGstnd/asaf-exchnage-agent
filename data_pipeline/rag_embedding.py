from utils.llmod_client import batch_embed_texts
from utils.config import supabase
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from utils.config import BASE_DIR, CHUNK_SIZE, CHUNK_OVERLAP
from pinecone_db.pinecone_client import upsert_embeddings

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
        "\n# ", "\n## ", "\n### ", # 1. Try Headers first
        "\n\n",                     # 2. Try Paragraphs
        "\n- ", "\n* ",             # 3. Try Bullet points (Keeps lists together!)
        ". ",                       # 4. Try Sentences
        "\n",                       # 5. Try Soft line breaks
        " ",                        # 6. Try Words
        ""                          # 7. Last resort
        ],
        add_start_index=True # Stores the character position where each chunk starts within the original text.
     )
    final_chunks = text_splitter.split_documents(header_splits)
    # Each chunk's structure: 
    # Document(
    #   page_content="The minimum GPA is 3.0...", 
    #   metadata={
    #       "Header 1": "REQUIREMENTS",
    #       "Header 2": "GPA",
    #       "start_index": 1250
    #   }
    # )
    return final_chunks


def save_chunks():
    """Chunk all extracted_texts and save to factsheets_chunks table in Supabase."""
    all_chunks = []
    response = supabase.table("extracted_texts").select("*").execute()
    rows = response.data if response and hasattr(response, 'data') else []
    print(f"Found {len(rows)} records in extracted_texts table.")
    for row in rows:
        country = row.get("country", "")
        uni = row.get("university", "")
        file_name = row.get("file_name", "")
        print(f"Chunking: {uni} ({country}) - {file_name}")
        try:
            chunks = chunk_pdf_with_headers(row)
        except Exception as e:
            print(f"Error processing {file_name} ({uni}, {country}): {e}")
            continue
        print(f"  -> {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            print(f"    Saving chunk {i+1}/{len(chunks)}")
            chunk_record = {
                "country": country,
                "university": uni,
                "file_name": file_name,
                "chunk_index": i,
                "text": chunk.page_content,
                "headers": chunk.metadata
            }
            all_chunks.append(chunk_record)
    if all_chunks:
        supabase.table("factsheets_chunks").upsert(all_chunks).execute()
        print(f"Saved {len(all_chunks)} chunks to factsheets_chunks table.")
    else:
        print("No chunks to save.")
    return all_chunks

def embed_chunks():
    """Embed all chunks from factsheets_chunks table and upsert to Pinecone."""
    response = supabase.table("factsheets_chunks").select("*").execute()
    rows = response.data if response and hasattr(response, 'data') else []
    print(f"Found {len(rows)} chunks in factsheets_chunks table.")
    if not rows:
        print("No chunks to embed.")
        return
    chunk_texts = [row["text"] for row in rows]
    embeddings = batch_embed_texts(chunk_texts)
    vectors = []
    metadatas = []
    for i, (row, embedding) in enumerate(zip(rows, embeddings)):
        chunk_id = f"{row['country']}_{row['university']}_{row['file_name']}_{row.get('chunk_index', i)}"
        vectors.append((chunk_id, embedding))
        metadatas.append({
            "country": row["country"],
            "university": row["university"],
            "file_name": row["file_name"],
            "headers": row["headers"],
            "text": (row.get("text") or "")[:4000]  # Pinecone metadata limit; truncate if needed
        })
    if vectors:
        upsert_embeddings(vectors, metadatas=metadatas)
        print(f"Upserted {len(vectors)} embeddings to Pinecone.")
    else:
        print("No embeddings to upsert.")


if __name__ == "__main__":
    print("Step 1: Chunking and saving to factsheets_chunks table...")
    save_chunks()
    # print("Step 2: Embedding and upserting to Pinecone...")
    # embed_chunks()
