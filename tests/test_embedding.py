import unittest
from utils.llmod_client import get_embedding, batch_embed_texts
from pinecone_db.pinecone_client import upsert_embeddings, query_embedding

class TestGetEmbedding(unittest.TestCase):
    def test_embedding_output_shape(self):
        text = "This is a test sentence for embedding."
        embedding = get_embedding(text)
        self.assertIsInstance(embedding, (list, tuple), "Embedding should be a list or tuple.")
        self.assertTrue(len(embedding) > 0, "Embedding should not be empty.")
        self.assertTrue(all(isinstance(x, (float, int)) for x in embedding), "All elements should be numeric.")

    def test_embedding_consistency(self):
        text = "Consistency test sentence."
        emb1 = get_embedding(text)
        emb2 = get_embedding(text)
        self.assertEqual(emb1, emb2, "Embeddings for the same text should be identical.")

    def test_embedding_different_texts(self):
        text1 = "First sentence."
        text2 = "Second sentence."
        emb1 = get_embedding(text1)
        emb2 = get_embedding(text2)
        self.assertNotEqual(emb1, emb2, "Embeddings for different texts should not be identical.")
    
def test_single_string_embedding_upsert():
    test_text = "This is a sample string to embed and upsert."
    print(f"Embedding text: {test_text}")
    embedding = get_embedding(test_text)
    print(f"Embedding (first 10 values): {embedding[:10]}")
    chunk_id = "test_country_test_university_test_file_0"
    metadata = {
        "country": "test_country",
        "university": "test_university",
        "file_name": "test_file",
        "text": test_text
    }
    print("Upserting embedding to Pinecone...")
    upsert_embeddings([(chunk_id, embedding)], metadatas=[metadata])
    print("Upsert complete.")


def embed_and_upsert_chunks_for_university(university):
    """
    Fetches all chunks for a given university from factsheets_chunks,
    embeds them, and upserts to Pinecone.
    """
    from utils.config import supabase
    response = supabase.table("factsheets_chunks").select("*").eq("university", university).execute()
    rows = response.data if response and hasattr(response, 'data') else []
    if not rows:
        print(f"No chunks found for university={university}")
        return []
    chunk_texts = [row["text"] for row in rows]
    print(f"Embedding {len(chunk_texts)} chunks...")
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
            "text": row.get("text", "")
        })
    print(f"Upserting {len(vectors)} embeddings to Pinecone...")
    upsert_embeddings(vectors, metadatas=metadatas)
    print("Upsert complete.")
    return chunk_texts

def sample_large_university(min_chunks=12):
    """
    Finds a random university with more than min_chunks in factsheets_chunks.
    Returns (university, country, total_chunks).
    """
    from utils.config import supabase
    from collections import defaultdict
    import random
    response = supabase.table("factsheets_chunks").select("country,university").execute()
    rows = response.data if response and hasattr(response, 'data') else []
    chunk_counts = defaultdict(int)
    country_map = {}
    for row in rows:
        key = row["university"]
        chunk_counts[key] += 1
        country_map[key] = row["country"]
    eligible = [(uni, country_map[uni], count) for uni, count in chunk_counts.items() if count > min_chunks]
    if not eligible:
        print(f"No university found with more than {min_chunks} chunks.")
        return None
    selected = random.choice(eligible)
    print(f"Random university with >{min_chunks} chunks: {selected[0]} ({selected[1]}) - {selected[2]} chunks")
    return selected

def test_single_query_retrieval(university, test_query):
    """
    Tests a single search query against a specific university, 
    printing the text and the similarity score.
    """
    print(f"\n=== Running Smoke Test for {university} ===")
    print(f"[Search] '{test_query}'")
    
    pinecone_filter = {
        "university": {"$eq": university}
    }
    
    results = query_embedding(
        query=test_query, 
        top_k=5, 
        filter=pinecone_filter
    )
    
    print(f"Retrieved {len(results)} chunks.\n")
    
    for i, match in enumerate(results, 1):
        meta = match.get("metadata", {})
        score = match.get("score", 0.0)
        text = meta.get("text", "")
        
        print(f"--- MATCH {i} (Score: {score:.4f}) ---")
        print(f"{text}\n")
        print("-" * 40)

def test_factsheet_retrieval_for_llm(university, file_name):
    queries = [
        "academic course load, minimum credits required, maximum ECTS allowed",
        "campus dormitory housing guaranteed, estimated monthly rent and living expenses",
        "student visa application process, processing months, mandatory health insurance",
        "mandatory orientation program, international student buddy program"
    ]
    
    unique_chunks = []
    seen_ids = set()
    
    print(f"\n=== Testing Retrieval for {university} ===")
    
    for q in queries:
        print(f"\n[Search] '{q}'")
        
        # Query Pinecone, filtering ONLY for this specific factsheet
        results = query_embedding(q, top_k=2, 
                                  filter={
            "university": {"$eq": university},
            }
        )
        
        for match in results.get("matches", []):
            chunk_id = match["id"]
            score = match["score"]
            text = match["metadata"].get("text", "")
            
            # Show the score to see how confident Pinecone is
            print(f" -> Found match! (Confidence Score: {score:.2f})")
            
            # Deduplicate (in case Visa and Housing pull the same chunk)
            if chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                unique_chunks.append(text)
                
    print(f"\n=== FINAL RESULT ===")
    print(f"Total unique chunks pulled for the LLM: {len(unique_chunks)}")
    
    # Print the master context block to visually inspect if the answers are inside
    print("\n--- WHAT THE LLM WILL READ ---")
    for i, chunk_text in enumerate(unique_chunks, 1):
        print(f"\n[CHUNK {i}]\n{chunk_text}")

    return unique_chunks


if __name__ == "__main__":
    # unittest.main()
    # test_single_string_embedding_upsert()

    # result = sample_large_university()
    # if result:
    #     university, country, total_chunks = result
    #     print(university, country, total_chunks)
    
    university = "University of Erlangen-Nuremberg"
    # embed_and_upsert_chunks_for_university(university)

    test_query = "academic requirements, credit system, ECTS, course load, grading scale, teaching methodology, prerequisites"
    test_single_query_retrieval(university, test_query)
