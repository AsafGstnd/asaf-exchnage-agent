## Fez Exchange Agent – Architecture

The Fez Exchange Agent is a multi‑agent system that recommends exchange universities and courses by orchestrating several LLM‑driven modules over structured and unstructured data sources.

### High‑Level Flow

1. **User → Supervisor (LangGraph)**
   - The user sends either:
     - an initial JSON profile (academic, language, availability, preferences), or
     - a follow‑up free‑text message.
   - The **Supervisor** (a LangGraph `StateGraph`) maintains conversation state (`AgentState`) and routes each turn.

2. **Supervisor Pipeline**
   - Base pipeline:
     - `Filter` → `Ranker` → `CourseFinder` → `Analyzer`
   - For the **first** user turn, the supervisor always runs the full pipeline.
   - For **follow‑up** turns, the supervisor uses an LLM router to decide whether to:
     - re‑run `Filter` (new constraints),
     - re‑run `Ranker` (re‑scoring existing universities),
     - run `CourseFinder` + `Analyzer` (course‑focused questions),
     - or run `Analyzer` only (logistics/fit questions).

3. **Modules and Responsibilities**

- **Filter**
  - Inputs: user profile (GPA, major, semesters completed, language tests, availability, Erasmus preference).
  - Data source: **Supabase** (`universities_requirements` table).
  - Responsibility: apply hard eligibility filters and output a `valid_universities_list`.
  - Steps logging: emits a `Filter` step with the Supabase query criteria and a count of matching universities.

- **Ranker**
  - Inputs: `valid_universities_list`, free‑text preferences.
  - Tools: **LLMod.ai** chat model.
  - Responsibility: score each university across several dimensions and produce `top_universities` plus reasoning text.
  - Steps logging: emits a `Ranker` step with the LLM prompt and the scored universities.

- **CourseFinder**
  - Inputs: `top_universities`, academic major, language profile.
  - Tools:
    - **Web Search** (DuckDuckGo) for live course catalog results.
    - **Pinecone** (factsheet chunks) for internal course information.
  - Responsibility: ReAct‑style loop that calls tools to find concrete courses per university.
  - Steps logging: emits a `CourseFinder` step with the tool calls and the list of matched courses per university.

- **Analyzer**
  - Inputs: `top_universities`, ranking reasonings, `courses`.
  - Data sources:
    - **Supabase** (requirements and metadata).
    - **Pinecone** (factsheet context via RAG).
    - **LLMod.ai** (structured extraction and summarisation).
  - Responsibility: act as the reasoning layer that combines:
    - eligibility requirements,
    - logistics and integration information,
    - course matches,
    - and the ranker’s fit reasoning,
    into a structured recommendation per university.
  - Steps logging: emits one or more `Analyzer` steps with prompts and structured JSON responses.

4. **API and Frontends**

- **FastAPI backend** (`/api/execute`)
  - Accepts a `prompt` string (JSON profile or free text).
  - Calls the Supervisor and returns:
    - `response`: JSON string containing `analysis` and `courses`.
    - `steps`: full execution trace where each item’s `module` is one of:
      `Filter`, `Ranker`, `CourseFinder`, `Analyzer`.

- **Web UI (FastAPI root `/`)**
  - Minimal HTML+JS page served by the API that:
    - lets the user send a prompt,
    - displays the final response payload,
    - and shows the full `steps` trace.

- **Streamlit UI** (`frontend/analysis_table.py`)
  - Rich dashboard with:
    - profile/Chat input,
    - tables for eligibility, logistics, and matched courses per university,
    - and an expandable trace view where each step is labeled by the same module names: `Filter`, `Ranker`, `CourseFinder`, `Analyzer`.

### Steps Logging and Modules

All LLM‑backed operations that influence the recommendation are logged as steps. The `module` field in each step is **always** one of:

- `Filter`
- `Ranker`
- `CourseFinder`
- `Analyzer`

This convention is used consistently in:

- the LangGraph supervisor implementation,
- the API response schema for `/api/execute`,
- the architecture documentation,
- and the (expected) architecture diagram.

