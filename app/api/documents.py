# app/api/documents.py

import os
import shutil
import logging
from typing import Optional, cast

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config.db import SessionLocal
from models.meta import MetaTable
from models.content import ContentTable
from models.ImageTable import ImageTable
from vector.realtime_vector import get_qdrant_client
from vector.collection_manager import resolve_collection_name
from qdrant_client.models import PointIdsList

logger = logging.getLogger("documents")

router = APIRouter(prefix="/documents", tags=["documents"])


# =================================================
# Dependency
# =================================================


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =================================================
# Response Models
# =================================================


class DocumentInfo(BaseModel):
    seq_id: int
    title: Optional[str]
    file_type: Optional[str]
    source: Optional[str]
    folder_name: Optional[str]
    file_hash: Optional[str]
    chunk_count: int
    image_count: int


class DeleteResponse(BaseModel):
    success: bool
    doc_id: int
    deleted_chunks: int
    deleted_images: int
    deleted_vectors: int
    message: str


class BatchDeleteResponse(BaseModel):
    success: bool
    total_requested: int
    total_deleted: int
    failed: list[int]
    details: list[DeleteResponse]


# =================================================
# GET - 문서 목록 / 상세
# =================================================


@router.get("", response_model=list[DocumentInfo])
async def list_documents(
    folder_name: Optional[str] = None,
    file_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    문서 목록 조회
    """
    query = db.query(MetaTable)

    if folder_name:
        query = query.filter(MetaTable.folder_name == folder_name)
    if file_type:
        query = query.filter(MetaTable.file_type == file_type)

    docs = query.order_by(MetaTable.seq_id.desc()).offset(offset).limit(limit).all()

    results = []
    for doc in docs:
        chunk_count = (
            db.query(ContentTable).filter(ContentTable.doc_id == doc.seq_id).count()
        )
        image_count = (
            db.query(ImageTable).filter(ImageTable.doc_id == doc.seq_id).count()
        )

        seq_id = cast(int, doc.seq_id)
        title = cast(Optional[str], doc.title)
        file_type_value = cast(Optional[str], doc.file_type)
        source = cast(Optional[str], doc.source)
        folder_name_value = cast(Optional[str], doc.folder_name)
        file_hash = cast(Optional[str], doc.file_hash)

        results.append(
            DocumentInfo(
                seq_id=seq_id,
                title=title,
                file_type=file_type_value,
                source=source,
                folder_name=folder_name_value,
                file_hash=file_hash,
                chunk_count=chunk_count,
                image_count=image_count,
            )
        )

    return results


@router.get("/{doc_id}", response_model=DocumentInfo)
async def get_document(doc_id: int, db: Session = Depends(get_db)):
    """
    단일 문서 상세 조회
    """
    doc = db.query(MetaTable).filter(MetaTable.seq_id == doc_id).first()

    if not doc:
        raise HTTPException(
            status_code=404, detail=f"문서를 찾을 수 없습니다: {doc_id}"
        )

    chunk_count = db.query(ContentTable).filter(ContentTable.doc_id == doc_id).count()
    image_count = db.query(ImageTable).filter(ImageTable.doc_id == doc_id).count()

    seq_id = cast(int, doc.seq_id)
    title = cast(Optional[str], doc.title)
    file_type_value = cast(Optional[str], doc.file_type)
    source = cast(Optional[str], doc.source)
    folder_name_value = cast(Optional[str], doc.folder_name)
    file_hash = cast(Optional[str], doc.file_hash)

    return DocumentInfo(
        seq_id=seq_id,
        title=title,
        file_type=file_type_value,
        source=source,
        folder_name=folder_name_value,
        file_hash=file_hash,
        chunk_count=chunk_count,
        image_count=image_count,
    )


# =================================================
# DELETE - 문서 삭제
# =================================================


def _delete_document_internal(doc_id: int, db: Session) -> DeleteResponse:
    """
    내부 삭제 로직 (트랜잭션 내에서 호출)

    삭제 순서:
    1. Qdrant 벡터 삭제 (content_id 기반)
    2. 이미지 파일 삭제 (파일시스템)
    3. DB 삭제 (CASCADE로 content, images 자동 삭제)
    """

    # 0️⃣ 문서 존재 확인
    doc = db.query(MetaTable).filter(MetaTable.seq_id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=404, detail=f"문서를 찾을 수 없습니다: {doc_id}"
        )

    # 1️⃣ content_id 목록 조회 (Qdrant 삭제용)
    contents = (
        db.query(ContentTable.content_id).filter(ContentTable.doc_id == doc_id).all()
    )
    content_ids = [c.content_id for c in contents]
    deleted_chunks = len(content_ids)

    # 2️⃣ 이미지 정보 조회
    images = db.query(ImageTable).filter(ImageTable.doc_id == doc_id).all()
    deleted_images = len(images)

    # 3️⃣ Qdrant 벡터 삭제
    deleted_vectors = 0
    if content_ids:
        try:
            model_key = os.getenv("MODEL_KEY")
            base_collection = os.getenv("BASE_COLLECTION", "documents")

            if model_key:
                collection_name = resolve_collection_name(base_collection, model_key)
                client = get_qdrant_client()

                # 포인트 ID로 삭제 (content_id가 point id)
                # qdrant-client 1.16+ uses PointIdsList model
                client.delete(
                    collection_name=collection_name,
                    points_selector=PointIdsList(points=content_ids),
                )
                deleted_vectors = len(content_ids)
                logger.info(
                    f"[DELETE] Qdrant vectors deleted: {deleted_vectors} from {collection_name}"
                )
        except Exception as e:
            logger.warning(f"[DELETE] Qdrant deletion failed (continuing): {e}")

    # 4️⃣ 이미지 파일 삭제 (파일시스템)
    image_dir = f"images/{doc_id}"
    if os.path.exists(image_dir):
        try:
            shutil.rmtree(image_dir)
            logger.info(f"[DELETE] Image directory removed: {image_dir}")
        except Exception as e:
            logger.warning(f"[DELETE] Image directory removal failed: {e}")

    # 5️⃣ DB 삭제 (meta 삭제 → content, images CASCADE 삭제)
    db.delete(doc)
    db.commit()

    logger.info(
        f"[DELETE] Document deleted: doc_id={doc_id}, chunks={deleted_chunks}, images={deleted_images}, vectors={deleted_vectors}"
    )

    return DeleteResponse(
        success=True,
        doc_id=doc_id,
        deleted_chunks=deleted_chunks,
        deleted_images=deleted_images,
        deleted_vectors=deleted_vectors,
        message=f"문서 {doc_id} 삭제 완료",
    )


@router.delete("/{doc_id}", response_model=DeleteResponse)
async def delete_document(doc_id: int, db: Session = Depends(get_db)):
    """
    단일 문서 삭제

    삭제 항목:
    - DB: meta_table, content_table, images (CASCADE)
    - Qdrant: 해당 문서의 모든 벡터
    - 파일시스템: images/{doc_id}/ 디렉토리
    """
    return _delete_document_internal(doc_id, db)


class BatchDeleteRequest(BaseModel):
    doc_ids: list[int] = Field(
        ..., min_length=1, max_length=100, description="삭제할 문서 ID 목록"
    )


@router.post("/batch-delete", response_model=BatchDeleteResponse)
async def batch_delete_documents(
    req: BatchDeleteRequest, db: Session = Depends(get_db)
):
    """
    여러 문서 일괄 삭제

    - 최대 100개까지 한번에 삭제 가능
    - 일부 실패해도 나머지는 계속 처리
    """
    results = []
    failed = []

    for doc_id in req.doc_ids:
        try:
            result = _delete_document_internal(doc_id, db)
            results.append(result)
        except HTTPException as e:
            failed.append(doc_id)
            results.append(
                DeleteResponse(
                    success=False,
                    doc_id=doc_id,
                    deleted_chunks=0,
                    deleted_images=0,
                    deleted_vectors=0,
                    message=str(e.detail),
                )
            )
        except Exception as e:
            failed.append(doc_id)
            results.append(
                DeleteResponse(
                    success=False,
                    doc_id=doc_id,
                    deleted_chunks=0,
                    deleted_images=0,
                    deleted_vectors=0,
                    message=str(e),
                )
            )

    return BatchDeleteResponse(
        success=len(failed) == 0,
        total_requested=len(req.doc_ids),
        total_deleted=len(req.doc_ids) - len(failed),
        failed=failed,
        details=results,
    )


# =================================================
# DELETE by folder
# =================================================


@router.delete("/folder/{folder_name}", response_model=BatchDeleteResponse)
async def delete_by_folder(folder_name: str, db: Session = Depends(get_db)):
    """
    특정 폴더의 모든 문서 삭제
    """
    docs = db.query(MetaTable.seq_id).filter(MetaTable.folder_name == folder_name).all()
    doc_ids = [d.seq_id for d in docs]

    if not doc_ids:
        raise HTTPException(
            status_code=404, detail=f"해당 폴더에 문서가 없습니다: {folder_name}"
        )

    # batch delete 재사용
    req = BatchDeleteRequest(doc_ids=doc_ids)
    return await batch_delete_documents(req, db)
