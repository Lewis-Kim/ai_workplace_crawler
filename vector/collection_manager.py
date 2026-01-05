# vector/collection_manager.py

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams

from vector.embedding_models import EMBEDDING_MODELS


def build_collection_name(base: str, model_key: str) -> str:
    cfg = EMBEDDING_MODELS[model_key]
    return f"{base}_{cfg.key}_v{cfg.version}"


def ensure_collection(
    client: QdrantClient,
    base_collection: str,
    model_key: str,
) -> str:

    cfg = EMBEDDING_MODELS[model_key]
    collection_name = build_collection_name(base_collection, model_key)

    collections = client.get_collections().collections
    names = [c.name for c in collections]

    if collection_name not in names:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=cfg.vector_size,
                distance=cfg.distance
            )
        )
        print(f"✅ Created collection: {collection_name}")
        return collection_name

    info = client.get_collection(collection_name)
    vectors = info.config.params.vectors

    if vectors.size != cfg.vector_size:
        raise RuntimeError("VECTOR_SIZE mismatch")

    if vectors.distance != cfg.distance:
        raise RuntimeError("DISTANCE mismatch")

    print(f"✅ Collection validated: {collection_name}")
    return collection_name
