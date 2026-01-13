#!/usr/bin/env python
"""
DB 데이터를 읽어 Qdrant Vector DB에 재적재하는 스크립트

사용법:
    # CLI 실행
    python scripts/rebuild_vector_from_db.py --model-key openai_large
    python scripts/rebuild_vector_from_db.py --doc-id 123
    
    # API에서 호출
    from scripts.rebuild_vector_from_db import rebuild_vectors_async
    result = await rebuild_vectors_async(model_key="openai_large")
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import argparse
import logging
import asyncio
from typing import Optional, Callable
from dataclasses import dataclass

from dotenv import load_dotenv
load_dotenv()

from qdrant_client import QdrantClient
from sqlalchemy.orm import Session

from config.db import SessionLocal
from models.meta import MetaTable
from models.content import ContentTable

from vector.collection_manager import ensure_collection
from vector.realtime_vector import insert_vector, get_qdrant_client
from services.text_normalizer import normalize_for_embedding


# =================================================
# logging
# =================================================
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("rebuild_vector")


# =================================================
# Result dataclass
# =================================================
@dataclass
class RebuildResult:
    success: bool
    model_key: str
    collection_name: str
    total_documents: int
    total_chunks: int
    success_chunks: int
    failed_chunks: int
    error: Optional[str] = None


# =================================================
# Core rebuild function (sync)
# =================================================
def rebuild_vectors(
    model_key: str,
    base_collection: str = None,
    doc_id: int = None,
    progress_callback: Callable[[int, int, str], None] = None,
) -> RebuildResult:
    """
    DB의 content_table 데이터를 Qdrant에 재적재
    
    Args:
        model_key: 임베딩 모델 키 (openai_large, nomic 등)
        base_collection: 컬렉션 기본 이름 (기본: 환경변수 BASE_COLLECTION)
        doc_id: 특정 문서만 처리 (None이면 전체)
        progress_callback: 진행상황 콜백 (current, total, message)
        
    Returns:
        RebuildResult: 재적재 결과
    """
    base_collection = base_collection or os.getenv("BASE_COLLECTION", "documents")
    
    db = SessionLocal()
    client = get_qdrant_client()
    
    try:
        # 1. 컬렉션 확보
        collection_name = ensure_collection(
            client=client,
            base_collection=base_collection,
            model_key=model_key
        )
        
        logger.info(f"[REBUILD] Target collection: {collection_name}")
        
        # 2. 대상 문서 조회
        meta_q = db.query(MetaTable)
        if doc_id:
            meta_q = meta_q.filter(MetaTable.seq_id == doc_id)
        
        metas = meta_q.all()
        
        if not metas:
            logger.warning("[REBUILD] No documents found")
            return RebuildResult(
                success=True,
                model_key=model_key,
                collection_name=collection_name,
                total_documents=0,
                total_chunks=0,
                success_chunks=0,
                failed_chunks=0,
            )
        
        # 3. 전체 청크 수 계산
        total_chunks = 0
        for meta in metas:
            count = db.query(ContentTable).filter(ContentTable.doc_id == meta.seq_id).count()
            total_chunks += count
        
        logger.info(f"[REBUILD] Processing {len(metas)} documents, {total_chunks} chunks")
        
        # 4. 재적재 실행
        success_count = 0
        failed_count = 0
        current_chunk = 0
        
        for meta in metas:
            logger.info(f"[REBUILD] Document: doc_id={meta.seq_id}, title={meta.title}")
            
            contents = (
                db.query(ContentTable)
                .filter(ContentTable.doc_id == meta.seq_id)
                .order_by(ContentTable.page_no, ContentTable.chunk_no)
                .all()
            )
            
            for content in contents:
                current_chunk += 1
                
                try:
                    text = normalize_for_embedding(content.content)
                    
                    if not text.strip():
                        continue
                    
                    insert_vector(
                        collection_name=collection_name,
                        model_key=model_key,
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
                    
                    success_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(
                        f"[REBUILD FAIL] doc_id={meta.seq_id}, "
                        f"content_id={content.content_id}: {e}"
                    )
                
                # 진행상황 콜백
                if progress_callback and current_chunk % 10 == 0:
                    progress_callback(
                        current_chunk, 
                        total_chunks,
                        f"Processing doc_id={meta.seq_id}"
                    )
        
        logger.info(
            f"[REBUILD] Completed: {success_count} success, {failed_count} failed"
        )
        
        return RebuildResult(
            success=failed_count == 0,
            model_key=model_key,
            collection_name=collection_name,
            total_documents=len(metas),
            total_chunks=total_chunks,
            success_chunks=success_count,
            failed_chunks=failed_count,
        )
        
    except Exception as e:
        logger.error(f"[REBUILD] Error: {e}")
        return RebuildResult(
            success=False,
            model_key=model_key,
            collection_name="",
            total_documents=0,
            total_chunks=0,
            success_chunks=0,
            failed_chunks=0,
            error=str(e),
        )
        
    finally:
        db.close()


# =================================================
# Async wrapper for API
# =================================================
async def rebuild_vectors_async(
    model_key: str,
    base_collection: str = None,
    doc_id: int = None,
) -> RebuildResult:
    """
    비동기 래퍼 - FastAPI에서 호출용
    
    실제 작업은 스레드 풀에서 실행 (blocking I/O)
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: rebuild_vectors(model_key, base_collection, doc_id)
    )
    return result


# =================================================
# CLI entry point
# =================================================
def main():
    parser = argparse.ArgumentParser(
        description="DB 데이터를 읽어 Qdrant Vector DB에 재적재"
    )
    parser.add_argument(
        "--model-key",
        type=str,
        default=os.getenv("MODEL_KEY", "openai_large"),
        help="임베딩 모델 키 (기본: 환경변수 MODEL_KEY)"
    )
    parser.add_argument(
        "--base-collection",
        type=str,
        default=os.getenv("BASE_COLLECTION", "documents"),
        help="컬렉션 기본 이름"
    )
    parser.add_argument(
        "--doc-id",
        type=int,
        help="특정 문서만 처리 (미지정 시 전체)"
    )

    args = parser.parse_args()

    print(f"Starting rebuild with model_key={args.model_key}")
    
    result = rebuild_vectors(
        model_key=args.model_key,
        base_collection=args.base_collection,
        doc_id=args.doc_id,
    )
    
    print("\n=== Rebuild Result ===")
    print(f"Success: {result.success}")
    print(f"Model: {result.model_key}")
    print(f"Collection: {result.collection_name}")
    print(f"Documents: {result.total_documents}")
    print(f"Chunks: {result.success_chunks}/{result.total_chunks}")
    if result.error:
        print(f"Error: {result.error}")


if __name__ == "__main__":
    main()
