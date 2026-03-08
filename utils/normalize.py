"""
Lightweight normalization helpers for university and country name matching.

These functions are used INTERNALLY for fuzzy matching only.
Original names are always preserved for display in the UI and API responses.

Normalization rules:
- Lowercase
- Strip leading/trailing whitespace
- Remove punctuation (except spaces)
- Collapse multiple spaces to one
"""

import re


def normalize_university_name(name: str) -> str:
    """
    Normalize a university name for internal fuzzy matching.

    NULL semantics: returns "" for None/empty input so callers can
    safely compare without crashing.

    Examples:
        "École Polytechnique Fédérale de Lausanne" -> "ecole polytechnique federale de lausanne"
        "  Technical University of Denmark (DTU)  " -> "technical university of denmark dtu"
    """
    if not name:
        return ""
    # Lowercase and strip outer whitespace
    name = name.lower().strip()
    # Remove punctuation (except spaces and word characters including Unicode letters).
    # Note: \w matches Unicode word characters including accented letters (é, ü, etc.).
    # This removes punctuation like parentheses, hyphens, and dots, but preserves
    # accented characters – which is sufficient for fuzzy matching purposes.
    name = re.sub(r"[^\w\s]", " ", name)
    # Collapse multiple whitespace to a single space
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def normalize_country(country: str) -> str:
    """
    Normalize a country name for internal fuzzy matching.

    NULL semantics: returns "" for None/empty input.

    Examples:
        "Czech Republic" -> "czech republic"
        "  South Korea  " -> "south korea"
    """
    if not country:
        return ""
    return re.sub(r"\s+", " ", country.lower().strip())
