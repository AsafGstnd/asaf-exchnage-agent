import os
from pinecone import Pinecone
from utils.llmod_client import get_embedding
from utils.config import PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME, TOP_K_RESULTS

def _get_index():
    if not PINECONE_API_KEY or not PINECONE_INDEX_NAME:
        raise ValueError("Pinecone credentials missing. Check your .env/config.")
    
    pc = Pinecone(api_key=PINECONE_API_KEY)
    return pc.Index(PINECONE_INDEX_NAME)

def upsert_embeddings(vectors, metadatas=None, namespace=None):
    """
    Upsert a batch of embeddings into Pinecone.
    vectors: list of (id, embedding) tuples or dicts
    metadatas: list of metadata dicts (optional)
    namespace: Pinecone namespace (optional)
    """
    # Pinecone upsert expects list of dicts: {"id": ..., "values": ..., "metadata": ...}
    index = _get_index()
    items = []
    for i, (id, embedding) in enumerate(vectors):
        item = {"id": id, "values": embedding}
        if metadatas and i < len(metadatas):
            item["metadata"] = metadatas[i]
        items.append(item)
    index.upsert(items=items, namespace=namespace)

def query_embedding(query, top_k=TOP_K_RESULTS, namespace=None, filter=None):
    """
    Query Pinecone for similar embeddings.
    query: string query to embed and search
    top_k: number of results
    namespace: Pinecone namespace (optional)
    filter: metadata filter (optional)
    """
    # You need to embed the query string before querying Pinecone
    index = _get_index()
    query_vector = get_embedding(query)
    return index.query(vector=query_vector, 
                       top_k=top_k, 
                       namespace=namespace, 
                       filter=filter, 
                       include_metadata=True)
