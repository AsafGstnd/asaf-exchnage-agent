import os
from pinecone import Pinecone
from utils.config import PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME

# Initialize Pinecone client
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

def upsert_embeddings(vectors, metadatas=None, namespace=None):
    """
    Upsert a batch of embeddings into Pinecone.
    vectors: list of (id, embedding) tuples or dicts
    metadatas: list of metadata dicts (optional)
    namespace: Pinecone namespace (optional)
    """
    # Pinecone upsert expects list of dicts: {"id": ..., "values": ..., "metadata": ...}
    items = []
    for i, (id, embedding) in enumerate(vectors):
        item = {"id": id, "values": embedding}
        if metadatas and i < len(metadatas):
            item["metadata"] = metadatas[i]
        items.append(item)
    index.upsert(items=items, namespace=namespace)

def query_embedding(query_vector, top_k=5, namespace=None, filter=None):
    """
    Query Pinecone for similar embeddings.
    query_vector: embedding vector to search
    top_k: number of results
    namespace: Pinecone namespace (optional)
    filter: metadata filter (optional)
    """
    return index.query(vector=query_vector, top_k=top_k, namespace=namespace, filter=filter)
