# app/api/dashboard.py

import os
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from config.db import SessionLocal
from models.meta import MetaTable
from models.content import ContentTable
from models.ImageTable import ImageTable
from models.folder_status import FolderStatus
from vector.realtime_vector import get_qdrant_client
from vector.collection_manager import resolve_collection_name

logger = logging.getLogger("dashboard")

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


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

class DashboardSummary(BaseModel):
    total: int
    success: int
    duplicated: int
    error: int


class SystemStatus(BaseModel):
    ingest_service: str
    vector_db: str
    vector_db_collection: str | None
    vector_count: int
    embedding_model: str | None


class DashboardDetail(BaseModel):
    summary: DashboardSummary
    system: SystemStatus
    recent_documents: list[dict]


# =================================================
# API Endpoints
# =================================================

@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    대시보드 요약 통계
    
    - total: 총 문서 수
    - success: 정상 처리된 문서 수
    - duplicated: 중복 파일 수 (duplicated 폴더 내 파일 수)
    - error: 에러 파일 수 (error 폴더 내 파일 수)
    """
    
    # 총 문서 수
    total = db.query(func.count(MetaTable.seq_id)).scalar() or 0
    
    # 정상 처리 = 총 문서 수 (meta_table에 있으면 정상 처리된 것)
    success = total
    
    # 중복 파일 수 (duplicated 폴더)
    duplicated_dir = "watch_dir/duplicated"
    duplicated = 0
    if os.path.exists(duplicated_dir):
        duplicated = len([f for f in os.listdir(duplicated_dir) if os.path.isfile(os.path.join(duplicated_dir, f))])
    
    # 에러 파일 수 (error 폴더)
    error_dir = "watch_dir/error"
    error = 0
    if os.path.exists(error_dir):
        error = len([f for f in os.listdir(error_dir) if os.path.isfile(os.path.join(error_dir, f))])
    
    return DashboardSummary(
        total=total,
        success=success,
        duplicated=duplicated,
        error=error,
    )


@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """
    시스템 상태 조회
    """
    
    # Ingest Service 상태
    ingest_status = "RUNNING"  # 서버가 응답하면 실행 중
    
    # Vector DB 상태
    vector_status = "DISCONNECTED"
    vector_count = 0
    collection_name = None
    
    try:
        client = get_qdrant_client()
        # 연결 테스트
        collections = client.get_collections()
        vector_status = "CONNECTED"
        
        # 현재 컬렉션 정보
        model_key = os.getenv("MODEL_KEY")
        base_collection = os.getenv("BASE_COLLECTION", "documents")
        
        if model_key:
            collection_name = resolve_collection_name(base_collection, model_key)
            try:
                info = client.get_collection(collection_name)
                vector_count = info.points_count or 0
            except Exception:
                pass
                
    except Exception as e:
        logger.warning(f"[DASHBOARD] Qdrant connection failed: {e}")
        vector_status = "DISCONNECTED"
    
    # 임베딩 모델
    model_key = os.getenv("MODEL_KEY")
    
    return SystemStatus(
        ingest_service=ingest_status,
        vector_db=vector_status,
        vector_db_collection=collection_name,
        vector_count=vector_count,
        embedding_model=model_key,
    )


@router.get("/detail", response_model=DashboardDetail)
async def get_dashboard_detail(db: Session = Depends(get_db)):
    """
    대시보드 상세 정보 (요약 + 시스템 상태 + 최근 문서)
    """
    
    # 요약
    summary = await get_dashboard_summary(db)
    
    # 시스템 상태
    system = await get_system_status()
    
    # 최근 문서 10개
    recent_docs = db.query(MetaTable).order_by(MetaTable.seq_id.desc()).limit(10).all()
    
    recent_documents = []
    for doc in recent_docs:
        chunk_count = db.query(func.count(ContentTable.content_id)).filter(
            ContentTable.doc_id == doc.seq_id
        ).scalar() or 0
        
        recent_documents.append({
            "seq_id": doc.seq_id,
            "title": doc.title,
            "file_type": doc.file_type,
            "folder_name": doc.folder_name,
            "chunk_count": chunk_count,
            "created_at": doc.create_dt.isoformat() if doc.create_dt else None,
        })
    
    return DashboardDetail(
        summary=summary,
        system=system,
        recent_documents=recent_documents,
    )


@router.get("/folders")
async def get_folder_status(db: Session = Depends(get_db)):
    """
    폴더별 처리 상태 조회
    """
    
    folders = db.query(FolderStatus).order_by(FolderStatus.id.desc()).limit(20).all()
    
    return {
        "folders": [
            {
                "id": f.id,
                "folder_key": f.folder_key,
                "folder_name": f.folder_name,
                "status": f.status,
                "total_files": f.total_files,
                "processed_files": f.processed_files,
                "error_files": f.error_files,
                "started_at": f.started_at.isoformat() if f.started_at else None,
                "finished_at": f.finished_at.isoformat() if f.finished_at else None,
            }
            for f in folders
        ]
    }
