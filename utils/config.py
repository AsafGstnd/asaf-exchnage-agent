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
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

# Chunking configuration
BASE_DIR = "data/external_universities"
CHUNK_SIZE = 2000  # characters per chunk
CHUNK_OVERLAP = 300  # overlap between chunks

LLMOD_BASE_URL = "https://api.llmod.ai"
LLMOD_EMBEDDING_MODEL = "RPRTHPB-text-embedding-3-small"
LLMOD_CHAT_MODEL = "RPRTHPB-gpt-5-mini"

