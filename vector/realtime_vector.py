# vector/realtime_vector.py

import os
import logging
from typing import Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from vector.embedding import embed_text
from vector.embedding_models import get_embedding_config
from vector.collection_manager import assert_vector_dimension
from vector.embedding_models import get_embedding_config

# =================================================
# logging
# =================================================
logger = logging.getLogger("vector")
logger.setLevel(logging.INFO)


# =================================================
# Qdrant client (singleton)
# =================================================
QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

_qdrant_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    """
    Qdrant client 단일 인스턴스 반환
    """
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            host=QDRANT_HOST,
            port=QDRANT_PORT,
            timeout=30,
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
    folder_name: str,
    title: str,
    file_type: str,
    source: str,
    extra_payload: Dict[str, Any] | None = None,
):
    """
    실시간 임베딩 → Qdrant upsert (운영 안전 버전)

    - collection_name : ensure_collection() 결과
    - model_key       : embedding_models.py 키
    - content_id      : DB content PK (Qdrant point id)
    """

    # -------------------------------------------------
    # 0️⃣ 입력 방어
    # -------------------------------------------------
    if not text or not text.strip():
        logger.warning(
            f"[VECTOR SKIP] empty text | content_id={content_id}"
        )
        return

    cfg = get_embedding_config(model_key)

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

    # -------------------------------------------------
    # 2️⃣ Vector dimension 안전 검증 (이중 장치)
    # -------------------------------------------------
    assert_vector_dimension(
        expected_dim=cfg.vector_size,
        vector=vector,
        content_id=content_id,
    )

    # -------------------------------------------------
    # 3️⃣ Payload 구성 (검색/필터 최적화: flatten) - 차후 확장 가능
    #    - 현재는 content 기반 검색만 사용
    # -------------------------------------------------
    metadata = {
        "content_id": content_id,
        "doc_id": doc_id,
        "page_no": page_no,
        "chunk_no": chunk_no,
        "model_key": model_key,
        "folder_name": folder_name,
        "title": title,
        "file_type": file_type,
        "source": source,
    }
    payload = {
        "content": text,
        "metadata": metadata,
    }

    if extra_payload:
        payload.update(extra_payload)

    # -------------------------------------------------
    # 4️⃣ Qdrant upsert
    # -------------------------------------------------
    client = get_qdrant_client()

    try:
        client.upsert(
            collection_name=collection_name,
            points=[
                PointStruct(
                    id=content_id,   # 🔥 PK 기반 (중복/재처리 안전)
                    vector=vector,
                    payload=payload,
                )
            ],
        )
    except Exception as e:
        logger.error(
            f"[QDRANT UPSERT FAIL] "
            f"collection={collection_name} "
            f"content_id={content_id} | {e}"
        )
        raise

    logger.info(
        f"[VECTOR OK] collection={collection_name} "
        f"content_id={content_id}"
    )
