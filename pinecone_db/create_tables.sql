CREATE TABLE IF NOT EXISTS public.extracted_texts (
    -- Primary ID
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Your Python variables
    country TEXT NOT NULL,
    university TEXT NOT NULL,
    file TEXT NOT NULL,
    text TEXT NOT NULL, -- The Markdown content
    
    -- The "Upsert" Rule: Prevents 70 files from becoming 700 duplicates
    CONSTRAINT unique_uni_file UNIQUE (country, university, file)
);

CREATE TABLE IF NOT EXISTS public.universities_requirements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    
    -- Academic Requirements
    min_gpa FLOAT,
    level_allowed TEXT,
    min_semesters_completed INT,
    restricted_majors TEXT[],
    
    -- Language Requirements
    lang_instruction TEXT,
    english_level TEXT,
    english_score TEXT,
    other_languages TEXT[],
    english_only_possible BOOLEAN,
    test_required BOOLEAN,
    
    -- Fall Semester Dates
    fall_start_month INT,
    fall_start_day INT,
    fall_end_month INT,
    fall_end_day INT,
    
    -- Spring Semester Dates
    spring_start_month INT,
    spring_start_day INT,
    spring_end_month INT,
    spring_end_day INT,
    
    -- Miscellaneous
    erasmus_available BOOLEAN,
    
    CONSTRAINT unique_uni_name_country UNIQUE (name, country)
);

-- Refresh the API cache
NOTIFY pgrst, 'reload schema';