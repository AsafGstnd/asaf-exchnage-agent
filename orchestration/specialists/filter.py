from utils.config import supabase

def apply_academic_filters(rows, academic, traced_steps):
    # GPA
    if academic.get("gpa") is not None:
        gpa_val = academic["gpa"]
        rows = [r for r in rows if (r.get("min_gpa") is None or r.get("min_gpa", 0) <= gpa_val)]
        traced_steps.append(f"Filtered by min_gpa <= {gpa_val} (or no GPA requirement)")
        print(f"[Filter Trace] Records remaining after GPA filter: {len(rows)}")
    # Study level
    if academic.get("study_level", "").strip().lower() == "msc":
        rows = [r for r in rows if r.get("msc_allowed", False)]
        traced_steps.append("Filtered by MSc allowed")
        print(f"[Filter Trace] Records remaining after MSc filter: {len(rows)}")
    # Semesters completed
    if academic.get("semesters_completed") is not None:
        sem_val = academic["semesters_completed"]
        rows = [r for r in rows if (r.get("min_semesters_completed") is None or r.get("min_semesters_completed", 0) <= sem_val)]
        traced_steps.append(f"Filtered by min_semesters <= {sem_val} (or no semester requirement)")
        print(f"[Filter Trace] Records remaining after Semesters filter: {len(rows)}")
    return rows

def apply_availability_filter(rows, availability, traced_steps):
    s_start_m = availability.get("start_month")
    s_start_d = availability.get("start_day") or 1
    s_end_m = availability.get("end_month")
    s_end_d = availability.get("end_day") or 31
    if s_start_m and s_end_m:
        stu_sm, stu_sd = int(s_start_m), int(s_start_d)
        stu_em, stu_ed = int(s_end_m), int(s_end_d)
        if stu_em < stu_sm:
            stu_em += 12
        student_start = (stu_sm, stu_sd)
        student_end = (stu_em, stu_ed)
        filtered = []
        for row in rows:
            has_sem = False
            overlap = False
            for sem_key in ["fall_semester", "spring_semester"]:
                sem = row.get(sem_key) or {}
                sm = sem.get("start_month")
                sd = sem.get("start_day") or 1
                em = sem.get("end_month")
                ed = sem.get("end_day") or 31
                if sm and em:
                    has_sem = True
                    uni_sm, uni_sd = int(sm), int(sd)
                    uni_em, uni_ed = int(em), int(ed)
                    if uni_em < uni_sm:
                        uni_em += 12
                    sem_start = (uni_sm, uni_sd)
                    sem_end = (uni_em, uni_ed)
                    if sem_start <= student_end and student_start <= sem_end:
                        overlap = True
                        break
            if not has_sem or overlap:
                filtered.append(row)
        rows = filtered
        traced_steps.append(f"Filtered by availability: {s_start_m}/{s_start_d} to {s_end_m}/{s_end_d}")
        print(f"[Filter Trace] Records remaining after Date Availability filter: {len(rows)}")
    return rows

def apply_language_filters(rows, language, preferences, traced_steps):
    user_langs = language.get("non_english_languages", [])
    if not user_langs:
        rows = [r for r in rows if r.get("english_only_possible", True)]
        traced_steps.append("Filtered for English-only universities")
    if preferences.get("must_be_erasmus") is True:
        rows = [r for r in rows if r.get("erasmus_available", False)]
        traced_steps.append("Filtered by Erasmus availability")
    return rows

def apply_english_test_filter(rows, language, traced_steps):
    user_tests = [t.strip().lower() for t in (language.get("english_test_type") or []) if t]
    user_level = language.get("english_test_level")
    cefr_map = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
    if user_tests:
        filtered = []
        for row in rows:
            uni_tests = [str(t).strip().lower() for t in (row.get("english_test_type") or [])]
            if not uni_tests:
                filtered.append(row)
                continue
            has_matching_test = False
            for u_test in user_tests:
                if any(u_test in db_test for db_test in uni_tests):
                    has_matching_test = True
                    break
            if has_matching_test:
                if user_level:
                    uni_cefr = str(row.get("english_test_level", "")).upper()
                    if cefr_map.get(user_level.upper(), 0) >= cefr_map.get(uni_cefr, 0):
                        filtered.append(row)
                else:
                    filtered.append(row)
        rows = filtered
        traced_steps.append(f"Filtered by English test: {user_tests}" + (f" CEFR >= {user_level}" if user_level else ""))
        print(f"[Filter Trace] Records remaining after English Test filter: {len(rows)}")
    return rows

def apply_restricted_majors_filter(rows, academic, traced_steps):
    if academic.get("major"):
        major = academic["major"].strip().lower()
        filtered = []
        for row in rows:
            restricted = [str(x).strip().lower() for x in (row.get("restricted_majors") or []) if x]
            if major not in restricted:
                filtered.append(row)
        rows = filtered
        traced_steps.append(f"Excluded restricted major: {academic['major']}")
        print(f"[Filter Trace] Records remaining after Restricted Majors filter: {len(rows)}")
    return rows

def apply_non_english_language_filter(rows, language, traced_steps):
    user_langs = language.get("non_english_languages", [])
    if user_langs:
        user_langs_norm = [str(l).strip().lower() for l in user_langs if l]
        filtered = []
        for row in rows:
            req_langs = [str(x).strip().lower() for x in (row.get("other_languages") or []) if x]
            if not req_langs:
                filtered.append(row)
                continue
            meets_all_reqs = True
            for req_lang in req_langs:
                if not any(u_lang in req_lang or req_lang in u_lang for u_lang in user_langs_norm):
                    meets_all_reqs = False
                    break
            if meets_all_reqs:
                filtered.append(row)
        rows = filtered
        traced_steps.append(f"Filtered by language match: {user_langs}")
        print(f"[Filter Trace] Records remaining after Non-English Language filter: {len(rows)}")
    return rows

def filter_universities(user_input):
    academic = user_input.get("academic_profile", {})
    language = user_input.get("language_profile", {})
    availability = user_input.get("availability", {})
    preferences = user_input.get("preferences", {})

    query = supabase.table("universities_requirements").select("*")
    traced_steps = []

    # Execute query
    response = query.execute()
    rows = response.data if response and hasattr(response, "data") else []
    print(f"\n[Filter Trace] Records retrieved from database: {len(rows)}")

    rows = apply_academic_filters(rows, academic, traced_steps)
    rows = apply_language_filters(rows, language, preferences, traced_steps)
    rows = apply_availability_filter(rows, availability, traced_steps)
    rows = apply_english_test_filter(rows, language, traced_steps)
    rows = apply_restricted_majors_filter(rows, academic, traced_steps)
    rows = apply_non_english_language_filter(rows, language, traced_steps)

    university_list = [
        {"name": r.get("name"), "country": r.get("country")}
        for r in rows if r.get("name") and r.get("country")
    ]

    return {
        "universities": university_list,
        "traced_steps": traced_steps + ["Queried universities_requirements table"]
    }
