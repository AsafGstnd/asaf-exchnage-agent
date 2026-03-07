
# Fez Exchange Agent

A multi-agent AI system that recommends university exchange programs tailored to a student's academic profile, language skills, budget, and preferences.

## Architecture

LangGraph pipeline with 4 specialist agents. Module names (Filter, Ranker, CourseFinder, Analyzer) must be consistent in the architecture diagram, steps logging, and descriptions.

```
START → Filter → Ranker → CourseFinder → Analyzer → END
```

| Module | Role |
|--------|------|
| **Filter** | Queries Supabase for universities matching hard eligibility criteria (GPA, language, dates, Erasmus, restricted majors) |
| **Ranker** | LLM scores filtered universities across 7 categories and returns the top-k |
| **CourseFinder** | ReAct agent that finds courses matching the student's major and languages using DuckDuckGo web search + Pinecone factsheets |
| **Analyzer** | Pinecone RAG + Supabase → per-university logistics (credits, housing, visa, buddy program); merges CourseFinder results |

## Stack

- **LLM / Embeddings**: LLMOD API (OpenAI-compatible) via `utils/llmod_client.py`
- **Vector DB**: Pinecone — factsheet chunks with `university`, `country`, `text` metadata
- **Relational DB**: Supabase — eligibility requirements, raw PDF chunks
- **Web Search**: DuckDuckGo (`ddgs`) — real-time course catalog lookup in CourseFinder
- **Orchestration**: LangGraph `StateGraph` with `MemorySaver` for multi-turn conversations
- **API**: FastAPI (`api/main.py`)
- **Frontend**: Streamlit (`frontend/analysis_table.py`)
- **Deployment**: Render (`render.yaml`)

## Quick Setup

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file at the project root:
```
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
PINECONE_API_KEY=
PINECONE_INDEX_NAME=
LLMOD_API_KEY=
```

## Running

```bash
# API server (serves REST API + web UI at http://localhost:8000)
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Streamlit UI (local agent by default)
streamlit run frontend/analysis_table.py
```

### Running Frontend Against Deployed API

To use the Streamlit UI with your deployed Render API:
```bash
export USE_API=true
export API_URL=https://your-render-app.onrender.com/api
streamlit run frontend/analysis_table.py
```
Or use the sidebar "Use deployed API" toggle when running the frontend.

## Tests

```bash
pytest                                  # all tests
pytest tests/test_course_finder.py -s  # course finder (unit + e2e)
pytest tests/test_supervisor.py -s     # full pipeline e2e
pytest -k "not e2e"                    # unit tests only
```

## Data Pipeline (run once)

```bash
python -m data_pipeline.universities_requirments  # populate Supabase
python -m data_pipeline.rag_embedding             # chunk PDFs → Supabase → Pinecone
```