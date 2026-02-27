"""
Extracts structured profile from free-text or partial user input.
Enables natural language input: "I want party vibe, 85 GPA, Europe, Jewish community"
"""
import json
from utils.llmod_client import llmod_chat


PROFILE_EXTRACTION_PROMPT = """You are a university exchange profile extractor. Given a user's free-text or partial input, output a structured JSON profile.

RULES:
- Extract: academic_profile (gpa, major, study_level, semesters_completed), preferences (free_language_preferences, must_be_erasmus), language_profile (non_english_languages, english_test_type, english_test_level), availability (start_month, end_month, start_day, end_day).
- Use sensible defaults when missing: gpa 80 if not stated, empty strings for preferences.
- Preserve any existing structured fields if the input is already JSON.
- free_language_preferences: summarize their vibe, location wishes, social/cultural preferences.
- Output ONLY valid JSON, no markdown.
- If input is empty or unintelligible, return minimal: {"academic_profile": {"gpa": 80}, "preferences": {"free_language_preferences": ""}, "language_profile": {}, "availability": {}}.

OUTPUT SCHEMA:
{
  "academic_profile": {"gpa": float|null, "major": str|null, "study_level": str|null, "semesters_completed": int|null},
  "preferences": {"free_language_preferences": str, "must_be_erasmus": bool|null},
  "language_profile": {"non_english_languages": [], "english_test_type": [], "english_test_level": str|null},
  "availability": {"start_month": int|null, "end_month": int|null, "start_day": int|null, "end_day": int|null}
}
"""


def extract_profile_from_text(user_input: str) -> dict:
    """
    Convert free-text or partial input into a structured profile dict.
    If input is already valid JSON with expected keys, merges/validates it.
    """
    stripped = (user_input or "").strip()
    if not stripped:
        return _default_profile()

    # If it looks like JSON, try to parse and use as base
    base = {}
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                base = _normalize_profile(parsed)
                if _is_adequately_structured(base):
                    return base
        except json.JSONDecodeError:
            pass

    # Use LLM to extract from free text
    try:
        out = llmod_chat(PROFILE_EXTRACTION_PROMPT, f"User input:\n{stripped[:2000]}", use_json=True)
        extracted = json.loads(out)
        if isinstance(extracted, dict):
            return _normalize_profile({**base, **extracted})
    except Exception:
        pass
    return base if base else _default_profile()


def _default_profile() -> dict:
    return {
        "academic_profile": {"gpa": 80},
        "preferences": {"free_language_preferences": "", "must_be_erasmus": None},
        "language_profile": {},
        "availability": {},
    }


def _normalize_profile(p: dict) -> dict:
    """Ensure all expected top-level keys exist."""
    return {
        "academic_profile": p.get("academic_profile") or {},
        "preferences": p.get("preferences") or {},
        "language_profile": p.get("language_profile") or {},
        "availability": p.get("availability") or {},
        "free_text": p.get("free_text", ""),
    }


def _is_adequately_structured(p: dict) -> bool:
    """Check if profile has enough structure to skip LLM extraction."""
    ac = p.get("academic_profile") or {}
    prefs = p.get("preferences") or {}
    return bool(ac.get("gpa") is not None or prefs.get("free_language_preferences"))
