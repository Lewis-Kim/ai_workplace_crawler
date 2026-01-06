# vector/embedding.py

import json
import http.client
import google.generativeai as genai
from openai import OpenAI

from vector.embedding_models import (
    EMBEDDING_MODELS,
    ENGINE_OPENAI,
    ENGINE_OLLAMA,
    ENGINE_GEMINI,
)

# -----------------------------
# OpenAI
# -----------------------------
_openai_client = OpenAI()

def _embed_openai(text: str, model: str) -> list[float]:
    resp = _openai_client.embeddings.create(
        model=model,
        input=text
    )
    return resp.data[0].embedding


# -----------------------------
# Ollama
# -----------------------------
OLLAMA_HOST = "localhost"
OLLAMA_PORT = 11434

def _embed_ollama(text: str, model: str) -> list[float]:
    conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=60)
    payload = json.dumps({"model": model, "prompt": text})
    headers = {"Content-Type": "application/json"}

    conn.request("POST", "/api/embeddings", payload, headers)
    res = conn.getresponse()
    body = res.read().decode("utf-8")

    if res.status != 200:
        raise RuntimeError(f"Ollama error {res.status}: {body}")

    return json.loads(body)["embedding"]


# -----------------------------
# Gemini
# -----------------------------
genai.configure()  # GOOGLE_API_KEY 환경변수 사용

def _embed_gemini(text: str, model: str) -> list[float]:
    result = genai.embed_content(
        model=model,
        content=text,
        task_type="retrieval_document",
    )
    return result["embedding"]


# -----------------------------
# Unified API
# -----------------------------
def embed_text(text: str, model_key: str) -> list[float]:
    if model_key not in EMBEDDING_MODELS:
        raise ValueError(f"Unknown model_key: {model_key}")

    cfg = EMBEDDING_MODELS[model_key]

    if cfg.engine == ENGINE_OPENAI:
        return _embed_openai(text, cfg.model_name)

    if cfg.engine == ENGINE_OLLAMA:
        return _embed_ollama(text, cfg.model_name)

    if cfg.engine == ENGINE_GEMINI:
        return _embed_gemini(text, cfg.model_name)

    raise RuntimeError(f"Unsupported embedding engine: {cfg.engine}")
