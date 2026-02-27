from utils.config import supabase

def _safe_int(val, default=None, min_val=None, max_val=None):
    try:
        n = int(val)
        if min_val is not None and n < min_val:
            return default
        if max_val is not None and n > max_val:
            return default
        return n
    except (TypeError, ValueError):
        return default

def filter_universities(user_input):
    """
    Filters the universities_requirements table based on user input criteria.
    Returns:
        dict: { "universities": list[dict], "traced_steps": list[str] }
    """
    if not supabase:
        raise RuntimeError("Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")

    if not isinstance(user_input, dict):
        return {"universities": [], "traced_steps": ["Invalid input: expected dict"]}

    academic = user_input.get("academic_profile") or {}
    language = user_input.get("language_profile") or {}
    availability = user_input.get("availability") or {}
    preferences = user_input.get("preferences") or {}
    if not isinstance(academic, dict):
        academic = {}
    if not isinstance(language, dict):
        language = {}
    if not isinstance(availability, dict):
        availability = {}
    if not isinstance(preferences, dict):
        preferences = {}

    query = supabase.table("universities_requirements").select("*")
    traced_steps = []

    # Academic filters
    gpa = _safe_int(academic.get("gpa"), min_val=0, max_val=100) if academic.get("gpa") is not None else None
    if gpa is not None:
        query = query.lte("min_gpa", gpa)
        traced_steps.append(f"Filtered by min_gpa <= {gpa}")

    study_level = str(academic.get("study_level", "")).strip().lower() if academic.get("study_level") else ""
    if study_level == "msc":
        query = query.eq("msc_allowed", True)
        traced_steps.append("Filtered by MSc allowed")

    semesters = _safe_int(academic.get("semesters_completed"), min_val=0) if academic.get("semesters_completed") is not None else None
    if semesters is not None:
        query = query.lte("min_semesters_completed", semesters)
        traced_steps.append(f"Filtered by min_semesters_completed <= {semesters}")

    # Language filters
    user_langs = language.get("non_english_languages", [])
    if not user_langs:
        query = query.eq("english_only_possible", True)
        traced_steps.append("Filtered for English-only universities")

    if preferences.get("must_be_erasmus") is True:
        query = query.eq("erasmus_available", True)
        traced_steps.append("Filtered by Erasmus availability")

    # Execute query
    response = query.execute()
    rows = response.data if response and hasattr(response, "data") else []

    # Availability overlap filtering
    s_start_m = availability.get("start_month")
    s_start_d = availability.get("start_day", 1)
    s_end_m = availability.get("end_month")
    s_end_d = availability.get("end_day", 31)

    if s_start_m and s_end_m:
        student_start = (_safe_int(s_start_m, 1, 1, 12), _safe_int(s_start_d, 1, 1, 31))
        student_end = (_safe_int(s_end_m, 12, 1, 12), _safe_int(s_end_d, 31, 1, 31))
        filtered = []
        for row in rows:
            has_sem = False
            overlap = False
            for sem_key in ["fall_semester", "spring_semester"]:
                sem = row.get(sem_key) or {}
                sm, sd, em, ed = sem.get("start_month"), sem.get("start_day", 1), sem.get("end_month"), sem.get("end_day", 31)
                if sm and em:
                    has_sem = True
                    sm_i, sd_i = _safe_int(sm, 1, 1, 12), _safe_int(sd, 1, 1, 31)
                    em_i, ed_i = _safe_int(em, 12, 1, 12), _safe_int(ed, 31, 1, 31)
                    if sm_i and em_i and (sm_i, sd_i) <= student_end and student_start <= (em_i, ed_i):
                        overlap = True
                        break
            if not has_sem or overlap:
                filtered.append(row)
        rows = filtered
        traced_steps.append(f"Filtered by availability: {s_start_m}/{s_start_d} to {s_end_m}/{s_end_d}")

    # English test + CEFR filter
    user_tests = [t.strip().lower() for t in (language.get("english_test_type") or []) if t]
    user_level = language.get("english_test_level")
    cefr_map = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
    if user_tests:
        filtered = []
        for row in rows:
            uni_tests = [str(t).strip().lower() for t in (row.get("english_test_type") or [])]
            if any(t in uni_tests for t in user_tests):
                if user_level:
                    if cefr_map.get(user_level.upper(), 0) >= cefr_map.get(str(row.get("english_test_level", "")).upper(), 0):
                        filtered.append(row)
                else:
                    filtered.append(row)
        rows = filtered
        traced_steps.append(f"Filtered by English test: {user_tests}" + (f" CEFR >= {user_level}" if user_level else ""))

    # Restricted majors
    if academic.get("major"):
        major = academic["major"].strip().lower()
        rows = [r for r in rows if major not in [x.strip().lower() for x in (r.get("restricted_majors") or [])]]
        traced_steps.append(f"Excluded restricted major: {academic['major']}")

    # Non-English language requirements
    if user_langs:
        user_langs_norm = [l.strip().lower() for l in user_langs]
        rows = [
            r for r in rows
            if all(l in user_langs_norm for l in [x.strip().lower() for x in (r.get("other_languages") or [])])
        ]
        traced_steps.append(f"Filtered by language match: {user_langs}")

    university_list = [
        {"name": r.get("name"), "country": r.get("country")}
        for r in rows if r.get("name") and r.get("country")
    ]

    return {
        "universities": university_list,
        "traced_steps": traced_steps + ["Queried universities_requirements table"]
    }
