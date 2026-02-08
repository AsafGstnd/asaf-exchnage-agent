import os
from supabase import create_client, Client
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

# --- Supabase Setup (Relational/SQL) ---
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(url, key)

# --- Pinecone Setup (Vector/RAG) ---
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
# This client will be used later in your rag_embedding.py