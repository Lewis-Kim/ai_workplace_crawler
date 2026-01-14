# vector/embedding.py

import os
import json
import http.client
from dotenv import load_dotenv

load_dotenv()  # 환경변수 로드

import google.generativeai as genai
from openai import OpenAI

from vector.embedding_models import (
    EMBEDDING_MODELS,
    ENGINE_OPENAI,
    ENGINE_OLLAMA,
    ENGINE_GEMINI,
)

# -----------------------------
# OpenAI (Lazy initialization)
# -----------------------------
_openai_client: OpenAI | None = None


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI()
    return _openai_client


def _embed_openai(text: str, model: str) -> list[float]:
    client = _get_openai_client()
    resp = client.embeddings.create(
        model=model,
        input=text
    )
    return resp.data[0].embedding


# -----------------------------
# Ollama
# -----------------------------
_ollama_host_env = os.getenv("OLLAMA_HOST", "localhost")
# 0.0.0.0은 서버 바인딩용이므로 클라이언트 연결 시 localhost로 변환
OLLAMA_HOST = "localhost" if _ollama_host_env == "0.0.0.0" else _ollama_host_env
OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))


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
# Gemini (Lazy initialization)
# -----------------------------
_gemini_configured = False


def _ensure_gemini_configured():
    global _gemini_configured
    if not _gemini_configured:
        genai.configure()  # GOOGLE_API_KEY 환경변수 사용
        _gemini_configured = True


def _embed_gemini(text: str, model: str) -> list[float]:
    _ensure_gemini_configured()
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
