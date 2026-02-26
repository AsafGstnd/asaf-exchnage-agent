import json
from utils.config import supabase

def filter_universities(user_input):
    """
    Filters the universities_requirements table based on user input criteria.

    Args:
        user_input (dict): JSON input from the student. Expected structure:
            {
                "academic_profile": {
                    "gpa": float,
                    "major": str,
                    "study_level": str,
                    "semesters_completed": int
                },
                "language_profile": {
                    "non_english_languages": list[str],
                    "english_test_type": str or None,
                    "english_test_level": str or None
                },
                "availability": {
                    "start_month": int or None,
                    "start_day": int or None,
                    "end_month": int or None,
                    "end_day": int or None
                },
                "preferences": {
                    "must_be_erasmus": bool,
                    "free_language_preferences": str  
                }
            }

    Returns:
        list[dict]: A list of valid universities that match the student's criteria. 
    """

    # Extract filtering criteria from user input structure
    academic = user_input.get("academic_profile", {})
    language = user_input.get("language_profile", {})
    availability = user_input.get("availability", {})
    preferences = user_input.get("preferences", {})

    # Build query based on available fields (assumptions can be improved later)
    query = supabase.table("universities_requirements").select("*")
    traced_steps = []

    # Academic profile
    if "gpa" in academic and academic["gpa"] is not None:
        query = query.gte("min_gpa", academic["gpa"])
        traced_steps.append(f"Filtered by min_gpa >= {academic['gpa']}")
    if "study_level" in academic and academic["study_level"]:
        level = academic["study_level"].strip().lower()
        if level == "msc":
            query = query.eq("msc_allowed", True)
            traced_steps.append("Filtered by MSc allowed (msc_allowed = True)")
        # For BSc, always allowed, so no filter needed
    if "semesters_completed" in academic and academic["semesters_completed"] is not None:
        query = query.lte("min_semesters_completed", academic["semesters_completed"])
        traced_steps.append(f"Filtered by semesters_completed >= {academic['semesters_completed']}")

    # Language profile
    user_langs = language.get("non_english_languages", [])
    if not user_langs:
        # User only wants English-taught universities
        query = query.eq("english_only_possible", True)
        traced_steps.append("Filtered for English-only universities (english_only_possible = True)")
   
    # Preferences
    if preferences.get("must_be_erasmus") is True:
        query = query.eq("erasmus_available", True)
        traced_steps.append("Filtered by Erasmus availability")

    # Availability filtering: student dates must overlap with at least one semester
    student_start_month = availability.get("start_month")
    student_start_day = availability.get("start_day", 1)
    student_end_month = availability.get("end_month")
    student_end_day = availability.get("end_day", 31)
    if student_start_month and student_end_month:
        filtered_rows = []
        for row in query.execute().data if query and hasattr(query.execute(), 'data') else []:
            def get_semester_range(sem):
                sm = sem.get("start_month")
                sd = sem.get("start_day", 1)
                em = sem.get("end_month")
                ed = sem.get("end_day", 31)
                if sm and not sd:
                    sd = 1
                if em and not ed:
                    ed = 31
                return sm, sd, em, ed

            def date_to_tuple(month, day):
                return (int(month), int(day)) if month else (None, None)

            student_start = date_to_tuple(student_start_month, student_start_day)
            student_end = date_to_tuple(student_end_month, student_end_day)

            # Check if university has any semester dates
            has_any_semester = False
            overlap = False
            for sem_key in ["fall_semester", "spring_semester"]:
                sem = row.get(sem_key, {})
                sm, sd, em, ed = get_semester_range(sem)
                if sm and em:
                    has_any_semester = True
                    sem_start = (int(sm), int(sd))
                    sem_end = (int(em), int(ed))
                    # Check for overlap
                    if sem_start <= student_end and student_start <= sem_end:
                        overlap = True
                        break
            # If no semester dates at all, keep the university
            if not has_any_semester or overlap:
                filtered_rows.append(row)
        rows = filtered_rows
        traced_steps.append(f"Filtered by student availability: {student_start_month}/{student_start_day} to {student_end_month}/{student_end_day}")
    else:
        response = query.execute()
        rows = response.data if response and hasattr(response, 'data') else []


    rows = response.data if response and hasattr(response, 'data') else []

    # Filter by English test type and CEFR level together
    user_tests = [t.strip().lower() for t in language.get("english_test_type", []) if t]
    user_level = language.get("english_test_level", None)
    cefr_map = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
    filtered_rows = []
    if user_tests:
        for row in rows:
            uni_tests = row.get("english_test_type", [])
            uni_tests_norm = [str(t).strip().lower() for t in uni_tests]
            # Only consider universities that accept at least one of the user's test types
            if any(t in uni_tests_norm for t in user_tests):
                # If user also provided a CEFR level, check it
                if user_level:
                    user_level_num = cefr_map.get(user_level.strip().upper(), 0)
                    uni_level = str(row.get("english_test_level", "")).strip().upper()
                    uni_level_num = cefr_map.get(uni_level, 0)
                    if user_level_num >= uni_level_num:
                        filtered_rows.append(row)
                else:
                    filtered_rows.append(row)
        rows = filtered_rows
        traced_steps.append(f"Filtered by English test type(s): {user_tests}" + (f" and CEFR level: {user_level}" if user_level else ""))
    # If no test type is provided, do not filter by CEFR level (as there won't be a level requirement)

    # Exclude universities where the student's major is in restricted_majors
    if "major" in academic and academic["major"]:
        major = academic["major"].strip().lower()
        filtered_rows = []
        for row in rows:
            restricted = row.get("restricted_majors", [])
            # Normalize for comparison
            restricted_norm = [str(r).strip().lower() for r in restricted]
            if major not in restricted_norm:
                filtered_rows.append(row)
        rows = filtered_rows
        traced_steps.append(f"Excluded restricted major: {academic['major']}")

    # Language filtering: only apply if user specified non-English languages
    if user_langs:
        user_langs_norm = [l.strip().lower() for l in user_langs]
        filtered_rows = []
        for row in rows:
            uni_langs = row.get("other_languages", [])
            uni_langs_norm = [str(l).strip().lower() for l in uni_langs]
            # If university requires a language not in user's list, exclude
            if all(l in user_langs_norm for l in uni_langs_norm):
                filtered_rows.append(row)
        rows = filtered_rows
        traced_steps.append(f"Excluded universities requiring languages not in user's list: {user_langs}")

    # Extract university names and countries for output
    university_list = [
        {"name": row.get("name"), "country": row.get("country")}
        for row in rows if row.get("name") and row.get("country")
    ]

    agent_response = {
        "universities": university_list,
        "traced_steps": traced_steps + [
            "Queried universities_requirements table"
        ]
    }
    return agent_response
