#!/usr/bin/env python
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import argparse
import logging

from qdrant_client import QdrantClient
from sqlalchemy.orm import Session

from config.db import SessionLocal
from models.meta import MetaTable
from models.content import ContentTable

from vector.collection_manager import ensure_collection
from vector.realtime_vector import insert_vector
from services.text_normalizer import normalize_for_embedding


# =================================================
# 🔧 설정
# =================================================
QDRANT_HOST = "192.168.50.32"
QDRANT_PORT = 6333

BASE_COLLECTION = "documents"
MODEL_KEY = "gemma2_embed"

LOG_LEVEL = logging.INFO


# =================================================
# logging
# =================================================
logging.basicConfig(
    level=LOG_LEVEL,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("db_to_vector")


# =================================================
# main logic
# =================================================
def rebuild_vector(
    db: Session,
    qdrant: QdrantClient,
    doc_id: int | None = None
):
    collection_name = ensure_collection(
        client=qdrant,
        base_collection=BASE_COLLECTION,
        model_key=MODEL_KEY
    )

    meta_q = db.query(MetaTable)
    if doc_id:
        meta_q = meta_q.filter(MetaTable.seq_id == doc_id)

    metas = meta_q.all()

    if not metas:
        logger.warning("대상 문서 없음")
        return

    for meta in metas:
        logger.info(
            f"[DOC] doc_id={meta.seq_id} | title={meta.title}"
        )

        contents = (
            db.query(ContentTable)
            .filter(ContentTable.doc_id == meta.seq_id)
            .order_by(ContentTable.page_no, ContentTable.chunk_no)
            .all()
        )

        for content in contents:
            try:
                text = normalize_for_embedding(content.content)

                if not text.strip():
                    continue

                insert_vector(
                    collection_name=collection_name,
                    model_key=MODEL_KEY,
                    content_id=content.content_id,
                    doc_id=meta.seq_id,
                    page_no=content.page_no,
                    chunk_no=content.chunk_no,
                    text=text[:1500],
                    folder_name=meta.folder_name,
                    title=meta.title,
                    file_type=meta.file_type,
                    source=meta.source
                )

            except Exception as e:
                logger.error(
                    f"[VECTOR FAIL] "
                    f"doc_id={meta.seq_id} "
                    f"content_id={content.content_id} | {e}"
                )

    logger.info("✅ DB → Vector 재적재 완료")


# =================================================
# entry point
# =================================================
def main():
    parser = argparse.ArgumentParser(
        description="DB 데이터를 읽어 Qdrant Vector DB에 재적재"
    )
    parser.add_argument(
        "--doc-id",
        type=int,
        help="특정 문서만 처리 (미지정 시 전체)"
    )

    args = parser.parse_args()

    db = SessionLocal()

    qdrant = QdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
        timeout=30
    )

    try:
        rebuild_vector(
            db=db,
            qdrant=qdrant,
            doc_id=args.doc_id
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
