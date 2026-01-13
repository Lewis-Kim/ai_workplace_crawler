# app/api/search.py

import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from qdrant_client.models import Filter, FieldCondition, MatchValue

from vector.embedding import embed_text
from vector.realtime_vector import get_qdrant_client
from vector.collection_manager import resolve_collection_name

logger = logging.getLogger("search")

router = APIRouter(prefix="/search", tags=["search"])

# =================================================
# Request / Response Models
# =================================================

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="검색 쿼리")
    top_k: int = Field(default=5, ge=1, le=100, description="반환할 결과 수")
    folder_name: Optional[str] = Field(default=None, description="폴더명 필터")
    file_type: Optional[str] = Field(default=None, description="파일타입 필터 (pdf, docx 등)")
    score_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="최소 유사도 점수")


class SearchResult(BaseModel):
    content_id: int
    doc_id: int
    page_no: int
    chunk_no: int
    content: str
    score: float
    title: Optional[str] = None
    folder_name: Optional[str] = None
    file_type: Optional[str] = None
    source: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list[SearchResult]


# =================================================
# Search API
# =================================================

@router.post("", response_model=SearchResponse)
async def search_documents(req: SearchRequest):
    """
    벡터 유사도 검색
    
    - query: 검색할 텍스트
    - top_k: 반환할 결과 수 (기본 5)
    - folder_name: 특정 폴더 내 검색 (선택)
    - file_type: 특정 파일타입 필터 (선택)
    - score_threshold: 최소 유사도 점수 (선택)
    """
    
    # -------------------------------------------------
    # 1️⃣ 환경 변수에서 설정 로드
    # -------------------------------------------------
    model_key = os.getenv("MODEL_KEY")
    base_collection = os.getenv("BASE_COLLECTION", "documents")
    
    if not model_key:
        raise HTTPException(status_code=500, detail="MODEL_KEY 환경변수가 설정되지 않았습니다")
    
    # -------------------------------------------------
    # 2️⃣ 쿼리 임베딩
    # -------------------------------------------------
    try:
        query_vector = embed_text(req.query, model_key)
    except Exception as e:
        logger.error(f"[SEARCH] embedding failed: {e}")
        raise HTTPException(status_code=500, detail=f"임베딩 실패: {str(e)}")
    
    # -------------------------------------------------
    # 3️⃣ Qdrant 검색
    # -------------------------------------------------
    collection_name = resolve_collection_name(base_collection, model_key)
    client = get_qdrant_client()
    
    # 필터 구성 (qdrant-client 1.16+ API)
    query_filter = None
    must_conditions = []
    
    if req.folder_name:
        must_conditions.append(
            FieldCondition(
                key="metadata.folder_name",
                match=MatchValue(value=req.folder_name)
            )
        )
    
    if req.file_type:
        must_conditions.append(
            FieldCondition(
                key="metadata.file_type", 
                match=MatchValue(value=req.file_type)
            )
        )
    
    if must_conditions:
        query_filter = Filter(must=must_conditions)
    
    try:
        # qdrant-client 1.16+ uses query_points instead of search
        search_result = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=req.top_k,
            query_filter=query_filter,
            score_threshold=req.score_threshold,
            with_payload=True,
        )
        # query_points returns QueryResponse with .points attribute
        points = search_result.points
    except Exception as e:
        logger.error(f"[SEARCH] qdrant search failed: {e}")
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}")
    
    # -------------------------------------------------
    # 4️⃣ 결과 변환
    # -------------------------------------------------
    results = []
    for hit in points:
        payload = hit.payload or {}
        metadata = payload.get("metadata", {})
        
        results.append(SearchResult(
            content_id=metadata.get("content_id", hit.id),
            doc_id=metadata.get("doc_id", 0),
            page_no=metadata.get("page_no", 0),
            chunk_no=metadata.get("chunk_no", 0),
            content=payload.get("content", ""),
            score=hit.score,
            title=metadata.get("title"),
            folder_name=metadata.get("folder_name"),
            file_type=metadata.get("file_type"),
            source=metadata.get("source"),
        ))
    
    logger.info(f"[SEARCH] query='{req.query[:50]}...' results={len(results)}")
    
    return SearchResponse(
        query=req.query,
        total=len(results),
        results=results,
    )


@router.get("/collections")
async def list_collections():
    """
    현재 사용 가능한 Qdrant 컬렉션 목록 조회
    """
    try:
        client = get_qdrant_client()
        collections = client.get_collections()
        return {
            "collections": [c.name for c in collections.collections]
        }
    except Exception as e:
        logger.error(f"[SEARCH] list collections failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collection/{collection_name}/info")
async def get_collection_info(collection_name: str):
    """
    특정 컬렉션의 상세 정보 조회
    """
    try:
        client = get_qdrant_client()
        info = client.get_collection(collection_name)
        
        # qdrant-client 1.16+ API compatibility
        vectors_config = info.config.params.vectors
        return {
            "name": collection_name,
            "vectors_count": info.indexed_vectors_count,
            "points_count": info.points_count,
            "status": str(info.status),
            "vector_size": vectors_config.size,
            "distance": str(vectors_config.distance),
        }
    except Exception as e:
        logger.error(f"[SEARCH] get collection info failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
