# vector/realtime_vector.py

import logging
from typing import Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from vector.embedding import embed_text
from vector.embedding_models import EMBEDDING_MODELS


# =================================================
# logging
# =================================================
logger = logging.getLogger("vector")
logger.setLevel(logging.INFO)


# =================================================
# Qdrant client (단일 인스턴스)
# =================================================
QDRANT_HOST = "192.168.50.32"
QDRANT_PORT = 6333

_qdrant_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            host=QDRANT_HOST,
            port=QDRANT_PORT,
            timeout=30
        )
        logger.info("[QDRANT] client initialized")
    return _qdrant_client


# =================================================
# vector insert (🔥 최종 안전 API)
# =================================================
def insert_vector(
    *,
    collection_name: str,
    model_key: str,
    content_id: int,
    doc_id: int,
    page_no: int,
    chunk_no: int,
    text: str,
    extra_payload: Dict[str, Any] | None = None,
):
    """
    실시간 임베딩 → Qdrant upsert (안전 버전)

    - collection_name: ensure_collection()에서 받은 값
    - model_key: embedding_models.py 키
    - content_id: DB content PK (vector id로 사용)
    """

    if not text or not text.strip():
        logger.warning(
            f"[VECTOR SKIP] empty text | content_id={content_id}"
        )
        return

    if model_key not in EMBEDDING_MODELS:
        raise ValueError(f"Unknown model_key: {model_key}")

    cfg = EMBEDDING_MODELS[model_key]

    # -------------------------------------------------
    # 1️⃣ Embedding
    # -------------------------------------------------
    try:
        vector = embed_text(text, model_key)
    except Exception as e:
        logger.error(
            f"[EMBED FAIL] content_id={content_id} | {e}"
        )
        raise

    # 안전 검증 (차원 불일치 방지)
    if len(vector) != cfg.vector_size:
        raise RuntimeError(
            f"Embedding size mismatch "
            f"(got={len(vector)}, expected={cfg.vector_size})"
        )

    # -------------------------------------------------
    # 2️⃣ Payload 구성
    # -------------------------------------------------
    payload = {
        "content_id": content_id,
        "doc_id": doc_id,
        "page_no": page_no,
        "chunk_no": chunk_no,
        "model_key": model_key,
        "text": text,
    }

    if extra_payload:
        payload.update(extra_payload)

    # -------------------------------------------------
    # 3️⃣ Qdrant upsert
    # -------------------------------------------------
    client = get_qdrant_client()

    try:
        client.upsert(
            collection_name=collection_name,
            points=[
                PointStruct(
                    id=content_id,   # 🔥 PK 기반 (중복 방지)
                    vector=vector,
                    payload=payload
                )
            ]
        )
    except Exception as e:
        logger.error(
            f"[QDRANT UPSERT FAIL] "
            f"collection={collection_name} "
            f"content_id={content_id} | {e}"
        )
        raise

    logger.debug(
        f"[VECTOR OK] collection={collection_name} "
        f"content_id={content_id}"
    )
