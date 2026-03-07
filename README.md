
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

## Tools and Infrastructure

- **Supabase (primary database)**: stores universities' hard requirements and metadata (`universities_requirements`, `factsheets_chunks`).
- **Pinecone (vector database)**: stores embedded factsheet chunks with `university`, `country`, `text` metadata for RAG.
- **DuckDuckGo search**: used by `CourseFinder` for live course catalog and exchange information.
- **LLMod.ai LLM**: OpenAI‑compatible chat and embedding API used for ranking, analysis, and embeddings (`utils/llmod_client.py`).
- **LangGraph orchestration**: `StateGraph` + `MemorySaver` manage the multi‑turn, conversation‑aware supervisor.
- **FastAPI backend**: exposes `/api/team_info`, `/api/agent_info`, `/api/model_architecture`, `/api/execute`.
- **Frontend UIs**:
  - Minimal HTML UI served at the API root (`/`) for quick manual testing.
  - Streamlit dashboard in `frontend/analysis_table.py` for rich inspection.
- **Render deployment**: `render.yaml` config for deploying the FastAPI service.

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

## GUI

You have two main ways to interact with the agent:

- **FastAPI Web UI (root `/`)**
  - Simple HTML page with:
    - a prompt textarea (JSON profile or chat message),
    - a **Run Agent** button that calls `POST /api/execute`,
    - a panel showing the final `response` payload,
    - and a full steps trace where each step shows `module`, `prompt`, and `response`.

- **Streamlit Dashboard (`frontend/analysis_table.py`)**
  - Sidebar:
    - Profile JSON or free‑text input,
    - toggle to use the local agent or deployed API.
  - Main view:
    - per‑university tabs with eligibility and logistics summaries,
    - matched courses table (from `CourseFinder`),
    - and an expandable execution trace that mirrors the `steps` returned by the API.

## Deployment (Render)

The project includes a `render.yaml` that configures a Python web service:

- Build: `pip install -r requirements.txt`
- Start: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- Environment variables:
  - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
  - `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`
  - `LLMOD_API_KEY`

Once deployed, your Render URL (e.g. `https://your-app.onrender.com`) will serve:

- The API endpoints under `/api/*`.
- The minimal web UI at `/`.

## Repository Structure

- `api/` – FastAPI application, including all required endpoints and the HTML web UI.
- `orchestration/` – LangGraph supervisor and specialist agents (Filter, Ranker, CourseFinder, Analyzer).
- `tools/` – Central tool registry and caching helpers for RAG and web search.
- `utils/` – Shared utilities (LLM client, configuration, PDF helpers, etc.).
- `data_pipeline/` – Scripts to ingest PDFs, extract requirements, and push data into Supabase and Pinecone.
- `pinecone_db/` – Pinecone client and helper functions for querying/upserting embeddings.
- `frontend/` – Streamlit UI for interactive exploration of recommendations and traces.
- `tests/` – Unit and e2e tests for filters, ranking, course finding, supervisor, and embeddings.
- `docs/` – High‑level documentation (e.g. `docs/architecture.md`).

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