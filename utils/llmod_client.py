import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration from .env
LLMOD_BASE_URL = os.getenv("LLMOD_BASE_URL")
LLMOD_API_KEY = os.getenv("LLMOD_API_KEY")
LLMOD_CHAT_MODEL = os.getenv("LLMOD_CHAT_MODEL", "o3-mini")
LLMOD_EMBEDDING_MODEL = os.getenv("LLMOD_EMBEDDING_MODEL", "text-embedding-3-small")

def llmod_chat(system_prompt: str, user_prompt: str, use_json: bool = False) -> str:
    """
    Centralized connection to LLMOD for Chat/Reasoning.
    """
    url = f"{LLMOD_BASE_URL}/chat/completions"
    headers = {"Authorization": f"Bearer {LLMOD_API_KEY}"}
    
    payload = {
        "model": LLMOD_CHAT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    if use_json:
        payload["response_format"] = {"type": "json_object"}

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    
    # Logic for budget tracking can be added here
    result = response.json()
    # print(f"Used {result['usage']['total_tokens']} tokens") 
    
    return result["choices"][0]["message"]["content"]


def get_embedding(text: str) -> list[float]:
    """
    Centralized connection to LLMOD for Vector Embeddings.
    """
    url = f"{LLMOD_BASE_URL}/embeddings"
    headers = {"Authorization": f"Bearer {LLMOD_API_KEY}"}
    payload = {
        "model": LLMOD_EMBEDDING_MODEL,
        "input": text
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]

def batch_embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Sends a list of chunks to the embedding model in one go.
    """
    url = f"{LLMOD_BASE_URL}/embeddings"
    headers = {"Authorization": f"Bearer {LLMOD_API_KEY}"}
    payload = {
        "model": LLMOD_EMBEDDING_MODEL,
        "input": texts
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return [item["embedding"] for item in response.json()["data"]]