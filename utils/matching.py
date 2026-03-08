"""
Lightweight runtime matching utilities for university/country names.

Preserves original names for UI and API responses.
Uses normalized names only for internal DB matching.

Re-exports normalize_university_name and normalize_country from utils.normalize
and adds match_university_fuzzy for tolerant row lookups.
"""

from typing import Optional
from utils.normalize import normalize_university_name, normalize_country

__all__ = ["normalize_university_name", "normalize_country", "match_university_fuzzy"]


def match_university_fuzzy(query_name: str, db_rows: list, name_column: str = "name") -> Optional[dict]:
    """
    Try exact match first, then normalized match.
    Returns the first matching row dict or None.

    Args:
        query_name: University name to look up.
        db_rows: List of row dicts from Supabase (or similar).
        name_column: Key in each row dict that holds the university name.

    Returns:
        First matching row dict, or None if no match found.
    """
    if not query_name or not db_rows:
        return None

    # 1. Exact match
    for row in db_rows:
        if row.get(name_column) == query_name:
            return row

    # 2. Normalized match (tolerates whitespace/casing/punctuation differences)
    normalized_query = normalize_university_name(query_name)
    for row in db_rows:
        row_name = row.get(name_column, "")
        if normalize_university_name(row_name) == normalized_query:
            return row

    return None
