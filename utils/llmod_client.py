import os
import time
import requests
from dotenv import load_dotenv
from .config import LLMOD_BASE_URL, LLMOD_CHAT_MODEL, LLMOD_EMBEDDING_MODEL

load_dotenv()

LLMOD_API_KEY = os.getenv("LLMOD_API_KEY")
LLMOD_TIMEOUT = int(os.getenv("LLMOD_TIMEOUT", "90"))
LLMOD_MAX_RETRIES = int(os.getenv("LLMOD_MAX_RETRIES", "2"))

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

    last_err = None
    for attempt in range(LLMOD_MAX_RETRIES + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=LLMOD_TIMEOUT)
            response.raise_for_status()
            result = response.json()
            choices = result.get("choices")
            if not choices or not isinstance(choices, list):
                raise ValueError("Invalid LLM response: no choices")
            msg = choices[0].get("message", {})
            content = msg.get("content")
            if content is None:
                raise ValueError("Invalid LLM response: empty content")
            return str(content)
        except Exception as e:
            last_err = e
            if attempt < LLMOD_MAX_RETRIES and hasattr(e, "response") and getattr(e.response, "status_code", 0) in (429, 502, 503):
                time.sleep(2 ** attempt)
            else:
                raise
    raise last_err or RuntimeError("LLM request failed")


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
    response = requests.post(url, json=payload, headers=headers, timeout=LLMOD_TIMEOUT)
    response.raise_for_status()
    data = response.json().get("data") or []
    if not data:
        raise ValueError("Invalid embedding response: no data")
    return data[0].get("embedding") or []

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
    response = requests.post(url, json=payload, headers=headers, timeout=LLMOD_TIMEOUT)
    response.raise_for_status()
    data = response.json().get("data") or []
    return [item.get("embedding") or [] for item in data]