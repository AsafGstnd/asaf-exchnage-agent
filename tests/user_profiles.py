
def get_student_profiles():
    """
    Returns a dictionary of named student profiles for filtering tests.
    """
    return {
        "default": {
            "academic_profile": {
                "gpa": 3.2,
                "major": "Computer Science",
                "study_level": "bsc",
                "semesters_completed": 4
            },
            "language_profile": {
                "non_english_languages": ["Spanish"],
                "english_test_type": ["TOEFL", "IELTS"],
                "english_test_level": "B2"
            },
            "availability": {
                "start_month": 8,
                "start_day": 15,
                "end_month": 12,
                "end_day": 31
            },
            "preferences": {
                "must_be_erasmus": True,
                "free_language_preferences": """
                    I want a traditional, unified campus where it's easy to make friends, 
                    rather than commuting in a massive, overwhelming city.

                    I'd love a place with cool museums, historical sites, good nightlife, 
                    and winters that aren't completely freezing.

                    Financially, I need an affordable city where rent and groceries won't 
                    drain my savings. My absolute max budget is $9,000 for the semester.
                """.strip()
            }
        },
        "high_gpa": {
            "academic_profile": {
                "gpa": 4.0,
                "major": "Physics",
                "study_level": "msc",
                "semesters_completed": 6
            },
            "language_profile": {
                "non_english_languages": [],
                "english_test_type": ["TOEFL"],
                "english_test_level": "C1"
            },
            "availability": {
                "start_month": 2,
                "start_day": 1,
                "end_month": 6,
                "end_day": 30
            },
            "preferences": {
                "must_be_erasmus": False,
                "free_language_preferences": "quiet campus, research focus"
            }
        },
        "low_gpa": {
            "academic_profile": {
                "gpa": 2.0,
                "major": "Business",
                "study_level": "bsc",
                "semesters_completed": 2
            },
            "language_profile": {
                "non_english_languages": ["French"],
                "english_test_type": ["IELTS"],
                "english_test_level": "B1"
            },
            "availability": {
                "start_month": 9,
                "start_day": 1,
                "end_month": 1,
                "end_day": 15
            },
            "preferences": {
                "must_be_erasmus": True,
                "free_language_preferences": "urban, business hub"
            }
        },
        "european_master" : {
                "academic_profile": {
                "gpa": 3.8,                 
                "major": "Medicine",        # Highly restricted globally; should cause a big drop
                "study_level": "msc",       # Triggers the query.eq("msc_allowed", True) database filter
                "semesters_completed": 6    
            },
            "language_profile": {
                "non_english_languages": ["French"], 
                "english_test_type": ["IELTS"],  
                "english_test_level": "C1"  # Higher requirement
            },
            "availability": {
                "start_month": 2,           # February
                "start_day": 1,
                "end_month": 7,             # July
                "end_day": 15               # Creates a Spring Semester window
            },
            "preferences": {
                "must_be_erasmus": True,    # Triggers the query.eq("erasmus_available", True) DB filter
                "free_language_preferences": "" 
            }
        },
        "english_only_freshman": {
                "academic_profile": {
                "gpa": 2.5,                 # Low GPA: Should aggressively filter out elite schools
                "major": "Business",        
                "study_level": "bsc",       
                "semesters_completed": 1    # Triggers drops for schools requiring 2-4 semesters
            },
            "language_profile": {
                "non_english_languages": [], # EMPTY: Triggers query.eq("english_only_possible", True)
                "english_test_type": ["Duolingo"], # Tests a less common English exam
                "english_test_level": "B1"   # Low CEFR: Will fail B2/C1 requirements
            },
            "availability": {
                "start_month": None,        # Bypasses dates to isolate the other strict filters
                "start_day": None,
                "end_month": None,          
                "end_day": None             
            },
            "preferences": {
                "must_be_erasmus": False,   
                "free_language_preferences": "" 
            }
        }
    }
