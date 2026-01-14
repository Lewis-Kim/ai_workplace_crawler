# app/api/settings.py

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

from config.runtime_settings import runtime_settings
from vector.realtime_vector import get_qdrant_client

logger = logging.getLogger("settings")

router = APIRouter(prefix="/settings", tags=["settings"])


# =================================================
# Request / Response Models
# =================================================

class LLMSettingsUpdate(BaseModel):
    provider: str = Field(..., description="LLM 제공자 (openai, ollama, gemini)")
    model: str = Field(..., description="모델명")


class EmbeddingSettingsUpdate(BaseModel):
    model_key: str = Field(..., description="임베딩 모델 키 (openai_large, nomic, bge_m3 등)")


class CollectionSettingsUpdate(BaseModel):
    collection_name: str = Field(..., description="Qdrant collection 이름")


class SettingsResponse(BaseModel):
    llm: dict
    embedding: dict


# =================================================
# GET - 현재 설정 조회
# =================================================

@router.get("", response_model=SettingsResponse)
async def get_settings():
    """
    현재 런타임 설정 조회
    """
    return runtime_settings.to_dict()


@router.get("/llm")
async def get_llm_settings():
    """
    LLM 설정만 조회
    """
    return runtime_settings.get_llm_config()


@router.get("/embedding")
async def get_embedding_settings():
    """
    임베딩 설정 조회
    """
    return runtime_settings.get_embedding_config()


# =================================================
# PUT - 설정 변경
# =================================================

@router.put("/llm")
async def update_llm_settings(req: LLMSettingsUpdate):
    """
    LLM 설정 변경
    
    - provider: openai, ollama, gemini
    - model: provider별 모델명
    """
    available_providers = list(runtime_settings.llm.available_models.keys())
    
    if req.provider not in available_providers:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 provider: {req.provider}. 사용 가능: {available_providers}"
        )
    
    success = runtime_settings.set_llm(req.provider, req.model)
    
    if not success:
        raise HTTPException(status_code=400, detail="설정 변경 실패")
    
    logger.info(f"[SETTINGS] LLM changed: provider={req.provider}, model={req.model}")
    
    return {
        "success": True,
        "message": f"LLM 설정 변경 완료: {req.provider}/{req.model}",
        "current": runtime_settings.get_llm_config(),
    }


# =================================================
# PUT - Embedding 설정 변경
# =================================================

@router.put("/embedding")
async def update_embedding_settings(req: EmbeddingSettingsUpdate):
    """
    Embedding 모델 변경
    
    ⚠️ 주의: 모델 변경 시 기존 문서 검색을 위해 재인덱싱 필요
    
    - model_key: openai_large, nomic, bge_m3, gemini_embed, gemma2_embed
    """
    available_models = list(runtime_settings.embedding.available_models.keys())
    
    if req.model_key not in available_models:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 model_key: {req.model_key}. 사용 가능: {available_models}"
        )
    
    result = runtime_settings.set_embedding(req.model_key)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "설정 변경 실패"))
    
    logger.info(f"[SETTINGS] Embedding changed: {result['old_model']} -> {result['new_model']}")
    
    return {
        "success": True,
        "message": f"Embedding 모델 변경 완료: {req.model_key}",
        "old_model": result["old_model"],
        "new_model": result["new_model"],
        "old_dimension": result["old_dimension"],
        "new_dimension": result["new_dimension"],
        "requires_reindex": result["requires_reindex"],
        "warning": result.get("warning"),
        "current": runtime_settings.get_embedding_config(),
    }


# =================================================
# POST - Embedding 재인덱싱
# =================================================

@router.post("/embedding/reindex")
async def reindex_embeddings(doc_id: Optional[int] = None):
    """
    Embedding 재인덱싱 실행
    
    현재 설정된 임베딩 모델로 모든 문서를 재인덱싱합니다.
    
    - doc_id: 특정 문서만 재인덱싱 (미지정 시 전체)
    
    ⚠️ 주의: 문서 수에 따라 시간이 오래 걸릴 수 있습니다.
    """
    from scripts.rebuild_vector_from_db import rebuild_vectors_async
    
    model_key = runtime_settings.embedding.model_key
    
    logger.info(f"[SETTINGS] Starting reindex with model_key={model_key}, doc_id={doc_id}")
    
    try:
        result = await rebuild_vectors_async(
            model_key=model_key,
            doc_id=doc_id,
        )
        
        return {
            "success": result.success,
            "model_key": result.model_key,
            "collection_name": result.collection_name,
            "total_documents": result.total_documents,
            "total_chunks": result.total_chunks,
            "success_chunks": result.success_chunks,
            "failed_chunks": result.failed_chunks,
            "error": result.error,
            "message": f"재인덱싱 완료: {result.success_chunks}/{result.total_chunks} chunks" if result.success else f"재인덱싱 실패: {result.error}",
        }
        
    except Exception as e:
        logger.error(f"[SETTINGS] Reindex failed: {e}")
        raise HTTPException(status_code=500, detail=f"재인덱싱 실패: {str(e)}")


# =================================================
# POST - 초기화
# =================================================

@router.post("/reset")
async def reset_settings():
    """
    설정을 환경변수(.env) 기본값으로 초기화
    """
    runtime_settings.reset_to_env()
    
    logger.info("[SETTINGS] Reset to environment defaults")
    
    return {
        "success": True,
        "message": "설정이 환경변수 기본값으로 초기화되었습니다.",
        "current": runtime_settings.to_dict(),
    }


# =================================================
# Qdrant Collection 관리
# =================================================

@router.get("/collections")
async def get_collections():
    """
    Qdrant에 존재하는 모든 collection 목록 조회
    """
    try:
        client = get_qdrant_client()
        collections = client.get_collections()
        
        collection_list = []
        for col in collections.collections:
            try:
                info = client.get_collection(col.name)
                collection_list.append({
                    "name": col.name,
                    "vectors_count": info.vectors_count,
                    "points_count": info.points_count,
                    "vector_size": info.config.params.vectors.size if info.config.params.vectors else None,
                })
            except Exception:
                collection_list.append({
                    "name": col.name,
                    "vectors_count": None,
                    "points_count": None,
                    "vector_size": None,
                })
        
        # 현재 선택된 collection
        current_collection = runtime_settings.get_collection_config()
        
        return {
            "collections": collection_list,
            "current": current_collection.get("collection_name"),
            "total": len(collection_list),
        }
        
    except Exception as e:
        logger.error(f"[SETTINGS] Failed to get collections: {e}")
        raise HTTPException(status_code=500, detail=f"Collection 목록 조회 실패: {str(e)}")


@router.put("/collections")
async def update_collection(req: CollectionSettingsUpdate):
    """
    사용할 Qdrant collection 변경
    
    - collection_name: Qdrant에 존재하는 collection 이름
    """
    try:
        client = get_qdrant_client()
        
        # collection 존재 확인
        if not client.collection_exists(req.collection_name):
            raise HTTPException(
                status_code=400,
                detail=f"Collection이 존재하지 않습니다: {req.collection_name}"
            )
        
        # 설정 저장
        result = runtime_settings.set_collection(req.collection_name)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "설정 변경 실패"))
        
        logger.info(f"[SETTINGS] Collection changed: {result['old_collection']} -> {result['new_collection']}")
        
        return {
            "success": True,
            "message": f"Collection 변경 완료: {req.collection_name}",
            "old_collection": result["old_collection"],
            "new_collection": result["new_collection"],
            "current": runtime_settings.get_collection_config(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SETTINGS] Failed to update collection: {e}")
        raise HTTPException(status_code=500, detail=f"Collection 변경 실패: {str(e)}")


# =================================================
# GET - 설정 적용 검증
# =================================================

@router.get("/verify")
async def verify_settings():
    """
    설정이 시스템 전체에 올바르게 적용되었는지 검증
    
    확인 항목:
    - Runtime Settings (메모리)
    - Database Storage (영구 저장)
    - RAG API (실제 사용되는 설정)
    """
    from config.db import SessionLocal
    from models.settings import SystemSettings
    
    import os
    
    # 1. Runtime settings (메모리)
    runtime_provider = runtime_settings.llm.provider
    runtime_model = runtime_settings.llm.model
    runtime_embedding = runtime_settings.embedding.model_key
    
    # 2. Database 확인
    db_provider = None
    db_model = None
    db_embedding = None
    db_updated_at = None
    db_synced = False
    
    try:
        db = SessionLocal()
        provider_row = db.query(SystemSettings).filter(
            SystemSettings.setting_key == "llm_provider"
        ).first()
        model_row = db.query(SystemSettings).filter(
            SystemSettings.setting_key == "llm_model"
        ).first()
        embed_row = db.query(SystemSettings).filter(
            SystemSettings.setting_key == "embedding_model_key"
        ).first()
        
        if provider_row:
            db_provider = provider_row.setting_value
            db_updated_at = str(provider_row.updated_at) if provider_row.updated_at else None
        if model_row:
            db_model = model_row.setting_value
        if embed_row:
            db_embedding = embed_row.setting_value
            
        db_synced = (
            db_provider == runtime_provider and 
            db_model == runtime_model and
            db_embedding == runtime_embedding
        )
        db.close()
    except Exception as e:
        logger.warning(f"[SETTINGS] DB verification failed: {e}")
    
    # 3. RAG API에서 사용하는 설정
    rag_provider = runtime_settings.llm.provider
    rag_model = runtime_settings.llm.model
    
    # 4. 환경변수 MODEL_KEY 확인
    env_embedding = os.getenv("MODEL_KEY")
    
    # 전체 동기화 상태
    all_synced = (
        runtime_provider == db_provider == rag_provider and
        runtime_model == db_model == rag_model and
        (db_embedding is None or db_embedding == runtime_embedding)
    )
    
    return {
        "runtime": {
            "provider": runtime_provider,
            "model": runtime_model,
            "embedding": runtime_embedding,
        },
        "database": {
            "provider": db_provider,
            "model": db_model,
            "embedding": db_embedding,
            "synced": db_synced,
            "updated_at": db_updated_at,
        },
        "rag_api": {
            "provider": rag_provider,
            "model": rag_model,
        },
        "embedding": {
            "current": runtime_embedding,
            "env_value": env_embedding,
            "synced": runtime_embedding == env_embedding or db_embedding == runtime_embedding,
        },
        "all_synced": all_synced,
        "message": "All settings are synchronized" if all_synced else "Settings may be out of sync",
    }
