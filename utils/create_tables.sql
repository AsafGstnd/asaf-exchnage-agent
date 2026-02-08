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
    min_gpa FLOAT,
    lang_instruction TEXT,
    lang_level_req TEXT,
    test_required BOOLEAN,
    waiver_conditions TEXT[],
    restricted_majors TEXT[],
    level_allowed TEXT,
    min_semesters_completed INT,
    semester_dates TEXT,
    erasmus_available BOOLEAN,
    CONSTRAINT unique_uni_name_country UNIQUE (name, country)
);

-- Refresh the API cache
NOTIFY pgrst, 'reload schema';