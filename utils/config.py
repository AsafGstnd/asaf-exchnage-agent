import os
from dotenv import load_dotenv

load_dotenv()

# --- Supabase Setup (Relational/SQL) ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# --- Supabase Client Initialization ---
try:
    from supabase import create_client
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
except ImportError:
    supabase = None  # supabase-py not installed

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

