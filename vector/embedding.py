# vector/embedding.py

import requests
from openai import OpenAI

from vector.embedding_models import EMBEDDING_MODELS


_openai_client = OpenAI()

# Ollama 설정
OLLAMA_HOST = "http://localhost:11434"


def _embed_openai(text: str, model: str) -> list[float]:
    resp = _openai_client.embeddings.create(
        model=model,
        input=text
    )
    return resp.data[0].embedding


def _embed_ollama(text: str, model: str) -> list[float]:
    r = requests.post(
        f"{OLLAMA_HOST}/api/embeddings",
        json={
            "model": model,
            "prompt": text
        },
        timeout=60
    )
    r.raise_for_status()
    return r.json()["embedding"]


def embed_text(text: str, model_key: str) -> list[float]:
    if model_key not in EMBEDDING_MODELS:
        raise ValueError(f"Unknown model_key: {model_key}")

    cfg = EMBEDDING_MODELS[model_key]

    if cfg.engine == "openai":
        return _embed_openai(text, cfg.model_name)

    if cfg.engine == "ollama":
        return _embed_ollama(text, cfg.model_name)

    raise RuntimeError(f"Unsupported embedding engine: {cfg.engine}")
