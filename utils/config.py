import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# --- Supabase Setup (Relational/SQL) ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# --- Supabase Client Initialization ---
# Guard against missing credentials so that import-time errors don't crash the app.
supabase = None
try:
    from supabase import create_client
    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    else:
        logger.warning(
            "⚠️  SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is not set. "
            "Supabase client is disabled; DB-backed features will be unavailable."
        )
except ImportError:
    logger.warning("⚠️  supabase-py is not installed. Supabase client is disabled.")
except Exception as _supa_err:
    logger.error("❌  Failed to create Supabase client: %s", _supa_err)
    supabase = None

# --- Pinecone Setup (Vector/RAG) ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
PINECONE_BATCH_SIZE = 100

# --- Embedding/LLM Configuration ---
EMBEDDING_MAX_TOKENS_PER_BATCH = 250000
EMBEDDING_MAX_CHUNKS_PER_BATCH = 2000

# Chunking configuration
BASE_DIR = "data/external_universities"
CHUNK_SIZE = 2000  # characters per chunk
CHUNK_OVERLAP = 400  # overlap between chunks
TOP_K_RESULTS = 7  # For Pinecone queries

LLMOD_BASE_URL = "https://api.llmod.ai"
LLMOD_EMBEDDING_MODEL = "RPRTHPB-text-embedding-3-small"
LLMOD_CHAT_MODEL = "RPRTHPB-gpt-5-mini"

# --- Startup Validation ---
# Warn clearly about missing critical env vars so misconfigured deployments
# produce actionable log output rather than silent failures downstream.
_REQUIRED_VARS = [
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "PINECONE_API_KEY",
    "PINECONE_INDEX_NAME",
    "LLMOD_API_KEY",
]
_missing_vars = [v for v in _REQUIRED_VARS if not os.getenv(v)]
if _missing_vars:
    logger.warning(
        "⚠️  Missing required environment variables: %s. "
        "Some features (DB filtering, RAG search, LLM calls) will be unavailable.",
        _missing_vars,
    )
