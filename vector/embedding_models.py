# vector/embedding_models.py

from dataclasses import dataclass
from qdrant_client.models import Distance


ENGINE_OPENAI = "openai"
ENGINE_OLLAMA = "ollama"
ENGINE_GEMINI = "gemini"   # ⭐ 추가


@dataclass(frozen=True)
class EmbeddingModelConfig:
    key: str
    model_name: str
    vector_size: int
    distance: Distance
    version: int
    engine: str          # ⭐ 추가: openai | ollama


EMBEDDING_MODELS = {
    "openai_large": EmbeddingModelConfig(
        key="openai_large",
        model_name="text-embedding-3-large",
        vector_size=3072,
        distance=Distance.COSINE,
        version=2,
        engine=ENGINE_OPENAI
    ),

    "nomic": EmbeddingModelConfig(
        key="nomic",
        model_name="nomic-embed-text",
        vector_size=768,
        distance=Distance.COSINE,
        version=2,
        engine=ENGINE_OLLAMA
    ),

    "bge_m3": EmbeddingModelConfig(
        key="bge_m3",
        model_name="bge-m3",
        vector_size=1024,
        distance=Distance.COSINE,
        version=1,
        engine=ENGINE_OLLAMA
    ),

    # -----------------------------
    # Gemini (Google)
    # -----------------------------
    "gemini_embed": EmbeddingModelConfig(
        key="gemini_embed",
        model_name="models/embedding-001",
        vector_size=768,
        distance=Distance.COSINE,
        version=1,
        engine=ENGINE_GEMINI
    ),
    
     # ⭐ NEW: Gemma 2 Embedding
    "gemma2_embed": EmbeddingModelConfig(
        key="gemma2_embed",
        model_name="embeddinggemma",
        vector_size=768,
        distance=Distance.COSINE,
        version=1,
        engine=ENGINE_OLLAMA
    ),   
    
}

def get_embedding_config(model_key: str) -> EmbeddingModelConfig:
    if model_key not in EMBEDDING_MODELS:
        raise ValueError(f"Unknown embedding model_key: {model_key}")
    return EMBEDDING_MODELS[model_key]
