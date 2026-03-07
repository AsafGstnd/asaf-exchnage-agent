"""
Central tool registry for the exchange agent.
Agents (CourseFinder, Analyzer) call tools dynamically from this registry.
Tools are wrapped with caching to reduce LLM and API usage.
"""
from typing import Any, Callable, Optional

from tools.implementations import rag_search_tool, web_search_tool
from tools.cache import cached_rag_search, cached_web_search


def rag_search(query: str, university: Optional[str] = None, top_k: int = 3, filter: Optional[dict] = None) -> str:
    """RAG search with cache. Use this from agents."""
    filter_dict = filter or {}
    if university:
        filter_dict = {**filter_dict, "university": {"$eq": university}}
    return cached_rag_search(
        query=query,
        university=university,
        top_k=top_k,
        filter_dict=filter_dict or None,
    )


def web_search(query: str, top_k: int = 3) -> str:
    """Web search with cache. top_k limited to 3 for efficiency."""
    return cached_web_search(query=query, top_k=min(top_k, 3))


# Registry: tool names map to callables that agents invoke
# CourseFinder uses search_factsheets and search_web
def search_factsheets_registry(university: str, query: str) -> str:
    """Cached factsheet search. Called by CourseFinder with university + query."""
    return rag_search(query=query, university=university, top_k=3)


def search_web_registry(query: str, top_k: int = 3) -> str:
    """Cached web search. top_k capped at 3."""
    return web_search(query=query, top_k=min(top_k, 3))


TOOLS = {
    "rag_search": rag_search,
    "web_search": web_search,
    "search_factsheets": search_factsheets_registry,
    "search_web": search_web_registry,
}


def get_tool(name: str) -> Optional[Callable]:
    """Get a tool by name."""
    return TOOLS.get(name)
