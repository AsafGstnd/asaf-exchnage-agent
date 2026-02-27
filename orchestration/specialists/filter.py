from utils.config import supabase

def filter_universities(user_input):
    """
    Filters the universities_requirements table based on user input criteria.
    Returns:
        dict: { "universities": list[dict], "traced_steps": list[str] }
    """
    academic = user_input.get("academic_profile", {})
    language = user_input.get("language_profile", {})
    availability = user_input.get("availability", {})
    preferences = user_input.get("preferences", {})

    query = supabase.table("universities_requirements").select("*")
    traced_steps = []

    # Academic filters
    if academic.get("gpa") is not None:
        query = query.lte("min_gpa", academic["gpa"])
        traced_steps.append(f"Filtered by min_gpa <= {academic['gpa']}")

    if academic.get("study_level", "").strip().lower() == "msc":
        query = query.eq("msc_allowed", True)
        traced_steps.append("Filtered by MSc allowed")

    if academic.get("semesters_completed") is not None:
        query = query.lte("min_semesters_completed", academic["semesters_completed"])
        traced_steps.append(f"Filtered by min_semesters_completed <= {academic['semesters_completed']}")

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
        student_start = (int(s_start_m), int(s_start_d))
        student_end = (int(s_end_m), int(s_end_d))
        filtered = []
        for row in rows:
            has_sem = False
            overlap = False
            for sem_key in ["fall_semester", "spring_semester"]:
                sem = row.get(sem_key) or {}
                sm, sd, em, ed = sem.get("start_month"), sem.get("start_day", 1), sem.get("end_month"), sem.get("end_day", 31)
                if sm and em:
                    has_sem = True
                    if (int(sm), int(sd)) <= student_end and student_start <= (int(em), int(ed)):
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
