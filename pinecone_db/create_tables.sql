CREATE TABLE IF NOT EXISTS public.factsheets_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    country TEXT NOT NULL,
    university TEXT NOT NULL,
    file_name TEXT NOT NULL,
    chunk_index INT NOT NULL,
    text TEXT NOT NULL,
    headers JSONB,
    CONSTRAINT unique_chunk_per_file UNIQUE (country, university, file_name, chunk_index)
);
CREATE TABLE IF NOT EXISTS public.extracted_texts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    country TEXT NOT NULL,
    university TEXT NOT NULL,
    file_name TEXT NOT NULL,
    text TEXT NOT NULL, -- The Markdown content
    -- The "Upsert" Rule: Prevents duplicates
    CONSTRAINT unique_uni_file UNIQUE (country, university, file_name)
);
CREATE TABLE IF NOT EXISTS public.universities_requirements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    -- Academic Requirements
    min_gpa FLOAT,
    msc_allowed BOOLEAN,
    min_semesters_completed INT,
    restricted_majors TEXT[],
    -- Language Requirements
    non_english_languages TEXT[],
    english_test_type TEXT[],
    english_test_level TEXT,
    english_only_possible BOOLEAN,
    test_required BOOLEAN,
    -- Semester Dates
    fall_semester JSONB,
    spring_semester JSONB,
    -- Miscellaneous
    erasmus_available BOOLEAN,
    CONSTRAINT unique_uni_name_country UNIQUE (name, country)
);
-- Refresh the API cache
NOTIFY pgrst, 'reload schema';