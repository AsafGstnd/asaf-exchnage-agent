from utils.llmod_client import batch_embed_texts
from utils.config import supabase
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from utils.config import BASE_DIR, CHUNK_SIZE, CHUNK_OVERLAP
from pinecone_db.pinecone_client import upsert_embeddings
import json

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
        separators=["\n\n", # 1. Paragraphs (Highest context)
                     "\n",  # 2. New Lines (Critical for Table Rows & Lists)
                     ". ",  # 3. Sentences (Only split a paragraph if it's giant)
                     " ",   # 4. Words
                     ""],   # 5. Characters
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

def chunk_pdf_recursively(row):
    """Chunk markdown text using ONLY RecursiveCharacterTextSplitter for larger, context-rich blocks."""
    md_text = row.get("text", "")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, 
        chunk_overlap=CHUNK_OVERLAP,
        separators=[
            "\n# ", "\n## ", "\n### ", # 1. Section Headers (Keep the big topics together)
            "\n\n",                     # 2. Paragraphs (Highest context)
            "\n",                       # 3. New Lines (Critical for Table Rows & Lists)
            ". ",                       # 4. Sentences (Only split a paragraph if it's giant)
            " ",                        # 5. Words
            ""                          # 6. Characters
        ],
        add_start_index=True 
    )
    
    # We pass the raw text directly into the recursive splitter
    final_chunks = text_splitter.create_documents([md_text])

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
            stripped_text = chunk.page_content.strip()
            if len(stripped_text) < 30:
                continue
            print(f"    Saving chunk {i+1}/{len(chunks)}")
            # Convert headers dict to string for storage
            headers_str = json.dumps(chunk.metadata) if chunk.metadata else ""
            chunk_record = {
                "country": country,
                "university": uni,
                "file_name": file_name,
                "chunk_index": i,
                "text": chunk.page_content,
                # "headers": headers_str
                # Only for chunk_pdf_with_headers method; contains the header structure for context formatting later. 
            }
            all_chunks.append(chunk_record)
    if all_chunks:
        supabase.table("factsheets_chunks").upsert(all_chunks).execute()
        print(f"Saved {len(all_chunks)} chunks to factsheets_chunks table.")
    else:
        print("No chunks to save.")
    return all_chunks


def to_slug(text):
    import re
    # Allows letters, numbers, spaces, AND dots. Removes everything else like ( )
    text = text.replace("-", " ")
    text = re.sub(r'[^a-zA-Z0-9\s\.]', '', text) 
    return text.replace(" ", "_").lower()

def embed_chunks():
    """Embed all chunks from factsheets_chunks table and upsert to Pinecone."""
    response = supabase.table("factsheets_chunks").select("*").execute()
    rows = response.data if response and hasattr(response, 'data') else []
    print(f"Found {len(rows)} chunks in factsheets_chunks table.")
    if not rows:
        print("No chunks to embed.")
        return
    chunk_texts = [row["text"] for row in rows]
    print("Generating embeddings for chunks...")
    embeddings = batch_embed_texts(chunk_texts)
    vectors = []
    metadatas = []
    for i, (row, embedding) in enumerate(zip(rows, embeddings)):
        if i % 100 == 0:
            print(f"Processing chunk {i+1}/{len(rows)}: {row['university']} - {row['file_name']} (chunk {row.get('chunk_index', i)})")
        clean_country = to_slug(row['country'])
        clean_uni = to_slug(row['university'])
        clean_file = to_slug(row['file_name'])
        chunk_id = f"{clean_country}_{clean_uni}_{clean_file}_{row.get('chunk_index', i)}"
        vectors.append((chunk_id, embedding))
        metadatas.append({
            "country": row["country"],
            "university": row["university"],
            "file_name": row["file_name"],
            # "headers": row["headers"],
            "text": (row.get("text") or "")
        })
    print(f"Upserting {len(vectors)} embeddings to Pinecone...")
    if vectors:
        upsert_embeddings(vectors, metadatas=metadatas)
        print(f"Upserted {len(vectors)} embeddings to Pinecone.")
    else:
        print("No embeddings to upsert.")


if __name__ == "__main__":
    # print("Step 1: Chunking and saving to factsheets_chunks table...")
    # save_chunks()
    print("Step 2: Embedding and upserting to Pinecone...")
    embed_chunks()