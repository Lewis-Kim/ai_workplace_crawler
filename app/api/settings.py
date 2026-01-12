# app/api/settings.py

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from config.runtime_settings import runtime_settings

logger = logging.getLogger("settings")

router = APIRouter(prefix="/settings", tags=["settings"])


# =================================================
# Request / Response Models
# =================================================

class LLMSettingsUpdate(BaseModel):
    provider: str = Field(..., description="LLM 제공자 (openai, ollama, gemini)")
    model: str = Field(..., description="모델명")


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
