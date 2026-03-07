import os
import requests
import tiktoken
from dotenv import load_dotenv
from .config import LLMOD_BASE_URL, LLMOD_CHAT_MODEL, LLMOD_EMBEDDING_MODEL, EMBEDDING_MAX_TOKENS_PER_BATCH, EMBEDDING_MAX_CHUNKS_PER_BATCH

load_dotenv()

# Only API key from .env
LLMOD_API_KEY = os.getenv("LLMOD_API_KEY")

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

def batch_embed_texts(
    texts: list[str], 
    max_tokens_per_batch: int = EMBEDDING_MAX_TOKENS_PER_BATCH,   # Adjust based on your API's limit
    max_chunks_per_batch: int = EMBEDDING_MAX_CHUNKS_PER_BATCH    # Adjust based on your API's array limit
) -> list[list[float]]:
    """
    Sends texts to the embedding model, ensuring no single batch exceeds
    the token limit or the array size limit.
    """
    url = f"{LLMOD_BASE_URL}/embeddings"
    headers = {"Authorization": f"Bearer {LLMOD_API_KEY}"}

    # 1. Load the tokenizer 
    # (If LLMOD uses an OpenAI-compatible model, cl100k_base is the standard)
    try:
        encoding = tiktoken.encoding_for_model(LLMOD_EMBEDDING_MODEL)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base") 

    all_embeddings = []
    current_batch = []
    current_batch_tokens = 0

    for idx, text in enumerate(texts):
        # Count tokens for this specific chunk
        tokens = len(encoding.encode(text))
        if idx % 100 == 0:
            print(f"Processing text {idx+1}/{len(texts)} (tokens: {tokens})")
        # Failsafe: If a single chunk is impossibly huge, log it
        if tokens > max_tokens_per_batch:
            print(f"WARNING: Chunk exceeds batch limit ({tokens} > {max_tokens_per_batch})")
        # 2. Check if adding this text pushes us over EITHER limit
        if (current_batch_tokens + tokens > max_tokens_per_batch) or (len(current_batch) >= max_chunks_per_batch):
            print(f"Sending batch of {len(current_batch)} texts to embedding API...")
            # 3. Ship the current bucket to the API
            payload = {"model": LLMOD_EMBEDDING_MODEL, "input": current_batch}
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            # Extract embeddings and add to our master list
            batch_embeddings = [item["embedding"] for item in response.json()["data"]]
            all_embeddings.extend(batch_embeddings)
            # 4. Empty the bucket and put the current text inside
            current_batch = [text]
            current_batch_tokens = tokens
        else:
            # Safe to add to the current bucket
            current_batch.append(text)
            current_batch_tokens += tokens

    # 5. Don't forget to ship the final, partially-full bucket!
    if current_batch:
        print(f"Sending final batch of {len(current_batch)} texts to embedding API...")
        payload = {"model": LLMOD_EMBEDDING_MODEL, "input": current_batch}
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        batch_embeddings = [item["embedding"] for item in response.json()["data"]]
        all_embeddings.extend(batch_embeddings)
    print(f"Total embeddings generated: {len(all_embeddings)}")
    return all_embeddings