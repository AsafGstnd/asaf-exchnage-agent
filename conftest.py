"""
Pytest configuration: load .env from the project root before any test imports.
This ensures credentials (Pinecone, Supabase, LLMOD) are available for e2e tests.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Always load .env from the project root, regardless of where pytest is invoked from
load_dotenv(Path(__file__).parent / ".env", override=True)
