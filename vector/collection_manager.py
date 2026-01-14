# vector/collection_manager.py

import logging
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams

from vector.embedding_models import get_embedding_config


# =================================================
# logging
# =================================================
logger = logging.getLogger("collection_manager")
logger.setLevel(logging.INFO)


# =================================================
# Collection name resolver
# =================================================
def resolve_collection_name(base_collection: str, model_key: str) -> str:
    """
    base_collection + model_key + version 조합으로
    실제 Qdrant 컬렉션명 생성

    예)
    base_collection = "docs"
    model_key       = "openai_large"

    -> docs_openai_large_v2
    """
    cfg = get_embedding_config(model_key)
    return f"{base_collection}_{model_key}_v{cfg.version}"


# =================================================
# Ensure collection (create or validate)
# =================================================
def ensure_collection(
    *,
    client: QdrantClient,
    base_collection: str,
    model_key: str,
) -> str:
    """
    Qdrant 컬렉션 존재 보장 + 차원(dimension) 안전 검증

    - 컬렉션이 없으면 생성
    - 이미 있으면 vector_size 불일치 시 즉시 에러

    Returns:
        실제 사용해야 할 collection_name
    """

    cfg = get_embedding_config(model_key)
    collection_name = resolve_collection_name(base_collection, model_key)

# -------------------------------------------------
    # 컬렉션이 이미 존재하는 경우
    # -------------------------------------------------
    if client.collection_exists(collection_name):
        info = client.get_collection(collection_name)

        existing_dim = info.config.params.vectors.size
        expected_dim = cfg.vector_size

        if existing_dim != expected_dim:
            raise RuntimeError(
                "[QDRANT COLLECTION DIMENSION MISMATCH]\n"
                f"collection   : {collection_name}\n"
                f"existing_dim : {existing_dim}\n"
                f"expected_dim : {expected_dim}\n"
                f"model_key    : {model_key}"
            )

        logger.debug(
            f"[QDRANT] collection exists: {collection_name} "
            f"(dim={existing_dim})"
        )
        return collection_name

    # -------------------------------------------------
    # 컬렉션 신규 생성
    # -------------------------------------------------
    logger.info(
        f"[QDRANT] creating collection: {collection_name} "
        f"(dim={cfg.vector_size}, distance={cfg.distance})"
    )

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=cfg.vector_size,
            distance=cfg.distance,
        ),
    )

    return collection_name


# =================================================
# Vector dimension assertion (double safety)
# =================================================
def assert_vector_dimension(
    *,
    expected_dim: int,
    vector: list[float],
    content_id: int | None = None,
):
    """
    insert / upsert 직전 vector 차원 검증 (이중 안전장치)

    Args:
        expected_dim : 컬렉션에 정의된 vector dimension
        vector       : 실제 임베딩 벡터
        content_id   : (선택) 로그 식별용
    """
    if len(vector) != expected_dim:
        msg = (
            f"[VECTOR DIMENSION ERROR] "
            f"expected={expected_dim}, got={len(vector)}"
        )
        if content_id is not None:
            msg += f" | content_id={content_id}"
        raise ValueError(msg)
