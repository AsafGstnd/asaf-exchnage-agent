"""
Tool implementations: RAG search and web search.
These are the raw implementations; the registry wraps them with caching.
"""
from typing import Optional

from pinecone_db.pinecone_client import query_embedding


def rag_search_tool(query: str, university: Optional[str] = None, top_k: int = 3, filter: Optional[dict] = None) -> str:
    """
    Search Pinecone factsheets for course/department info.
    If university is provided, filter by it.
    Returns concatenated text from matching chunks.
    """
    filter_dict = filter or {}
    if university:
        filter_dict = {**filter_dict, "university": {"$eq": university}}

    results = query_embedding(query, top_k=top_k, filter=filter_dict or None)
    texts = [
        r.get("metadata", {}).get("text", "")
        for r in results
        if r.get("metadata", {}).get("text")
    ]
    return "\n---\n".join(texts) if texts else "No relevant information found in factsheets."


def web_search_tool(query: str, top_k: int = 3) -> str:
    """
    Search the web using DuckDuckGo.
    top_k: number of results to return (default 3).
    """
    try:
        from duckduckgo_search import DDGS

        results = DDGS().text(query, max_results=top_k)
        if not results:
            return "No web results found."
        parts = [f"{r['title']}\n{r['body']}" for r in results if r.get("body")]
        return "\n---\n".join(parts) if parts else "No web results found."
    except Exception as e:
        return f"Web search failed: {e}"
