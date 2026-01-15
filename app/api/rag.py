# app/api/rag.py

import os
import logging
import importlib
from typing import Any, Optional, cast

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


from vector.embedding import embed_text
from vector.realtime_vector import get_qdrant_client
from vector.collection_manager import resolve_collection_name
from config.runtime_settings import runtime_settings

logger = logging.getLogger("rag")

router = APIRouter(prefix="/rag", tags=["rag"])


# =================================================
# LLM Providers
# =================================================


def _call_openai(prompt: str, model: str = "gpt-4o-mini") -> str:
    """OpenAI API 호출"""
    from openai import OpenAI

    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "당신은 문서 기반 질의응답 AI 어시스턴트입니다. 주어진 문서 컨텍스트를 바탕으로 정확하고 친절하게 답변하세요. 컨텍스트에 없는 내용은 추측하지 마세요.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=2000,
    )
    content = response.choices[0].message.content
    return content or ""


def _call_ollama(prompt: str, model: str = "llama3.2") -> str:
    """Ollama 로컬 LLM 호출"""
    import ollama

    response = ollama.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "당신은 문서 기반 질의응답 AI 어시스턴트입니다. 주어진 문서 컨텍스트를 바탕으로 정확하고 친절하게 답변하세요. 컨텍스트에 없는 내용은 추측하지 마세요.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    return response["message"]["content"]


def _call_gemini(prompt: str, model: str = "gemini-1.5-flash") -> str:
    """Google Gemini API 호출"""
    genai = cast(Any, importlib.import_module("google.generativeai"))

    genai.configure()
    gen_model = genai.GenerativeModel(model)

    response = gen_model.generate_content(
        f"당신은 문서 기반 질의응답 AI 어시스턴트입니다. 주어진 문서 컨텍스트를 바탕으로 정확하고 친절하게 답변하세요.\n\n{prompt}"
    )
    return response.text


# =================================================
# Request / Response Models
# =================================================


class RAGRequest(BaseModel):
    question: str = Field(..., min_length=1, description="질문")
    top_k: int = Field(default=5, ge=1, le=20, description="검색할 문서 수")
    llm_provider: Optional[str] = Field(
        default=None, description="LLM 제공자 (openai, ollama, gemini)"
    )
    llm_model: Optional[str] = Field(default=None, description="LLM 모델명")


class SourceDocument(BaseModel):
    title: Optional[str]
    content: str
    page_no: int
    score: float
    file_type: Optional[str]
    folder_name: Optional[str]


class RAGResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceDocument]
    llm_provider: str
    llm_model: str


# =================================================
# RAG API
# =================================================


@router.post("/chat", response_model=RAGResponse)
async def rag_chat(req: RAGRequest):
    """
    RAG 기반 질의응답

    1. 질문을 벡터 검색하여 관련 문서 찾기
    2. 문서 컨텍스트와 질문을 LLM에 전달
    3. 답변 생성 및 소스 문서 반환
    """

    # -------------------------------------------------
    # 1️⃣ 설정 로드
    # -------------------------------------------------
    model_key = os.getenv("MODEL_KEY")
    base_collection = os.getenv("BASE_COLLECTION", "documents")

    # LLM 설정 (요청 > 런타임설정 > 환경변수 순서)
    llm_provider = req.llm_provider or runtime_settings.llm.provider
    llm_model = req.llm_model or runtime_settings.llm.model

    if not model_key:
        raise HTTPException(
            status_code=500, detail="MODEL_KEY 환경변수가 설정되지 않았습니다"
        )

    # -------------------------------------------------
    # 2️⃣ 벡터 검색
    # -------------------------------------------------
    try:
        query_vector = embed_text(req.question, model_key)
    except Exception as e:
        logger.error(f"[RAG] embedding failed: {e}")
        raise HTTPException(status_code=500, detail=f"임베딩 실패: {str(e)}")

    # Collection 결정: 수동 선택 > 자동 생성
    manual_collection = runtime_settings.collection.collection_name
    if manual_collection:
        collection_name = manual_collection
        logger.debug(f"[RAG] Using manually selected collection: {collection_name}")
    else:
        collection_name = resolve_collection_name(base_collection, model_key)
        logger.debug(f"[RAG] Using auto-generated collection: {collection_name}")

    client = cast(Any, get_qdrant_client())

    try:
        # qdrant-client 1.8+ uses query_points method
        search_response = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=req.top_k,
            with_payload=True,
        )
        search_result = search_response.points
    except Exception as e:
        logger.error(f"[RAG] search failed: {e}")
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}")

    # -------------------------------------------------
    # 3️⃣ 컨텍스트 구성
    # -------------------------------------------------
    sources = []
    context_parts = []

    for i, hit in enumerate(search_result, 1):
        payload = hit.payload or {}
        metadata = payload.get("metadata", {})
        content = payload.get("content", "")

        sources.append(
            SourceDocument(
                title=metadata.get("title"),
                content=content[:500],  # 소스에는 요약본
                page_no=metadata.get("page_no", 0),
                score=hit.score,
                file_type=metadata.get("file_type"),
                folder_name=metadata.get("folder_name"),
            )
        )

        # 컨텍스트용 전체 내용
        context_parts.append(
            f"[문서 {i}] {metadata.get('title', '문서')}, 페이지 {metadata.get('page_no', '?')}:\n{content}"
        )

    if not context_parts:
        return RAGResponse(
            question=req.question,
            answer="죄송합니다. 질문과 관련된 문서를 찾을 수 없습니다. 다른 질문을 시도해주세요.",
            sources=[],
            llm_provider=llm_provider,
            llm_model=llm_model,
        )

    context = "\n\n---\n\n".join(context_parts)

    # -------------------------------------------------
    # 4️⃣ LLM 호출
    # -------------------------------------------------
    prompt = f"""아래는 질문과 관련된 문서 내용입니다.

### 문서 컨텍스트:
{context}

### 질문:
{req.question}

### 답변:
위 문서 내용을 바탕으로 질문에 답변해주세요. 문서에 없는 내용은 "문서에서 관련 정보를 찾을 수 없습니다"라고 말씀해주세요.
내용이 없을 시 참고 문서는 표시하지 마세요 """

    try:
        if llm_provider == "openai":
            answer = _call_openai(prompt, llm_model)
        elif llm_provider == "ollama":
            answer = _call_ollama(prompt, llm_model)
        elif llm_provider == "gemini":
            answer = _call_gemini(prompt, llm_model)
        else:
            raise HTTPException(
                status_code=400, detail=f"지원하지 않는 LLM 제공자: {llm_provider}"
            )

    except Exception as e:
        logger.error(f"[RAG] LLM call failed: {e}")
        raise HTTPException(status_code=500, detail=f"LLM 호출 실패: {str(e)}")

    logger.info(
        f"[RAG] question='{req.question[:50]}...' sources={len(sources)} provider={llm_provider}"
    )

    return RAGResponse(
        question=req.question,
        answer=answer,
        sources=sources,
        llm_provider=llm_provider,
        llm_model=llm_model,
    )


@router.get("/config")
async def get_rag_config():
    """
    현재 RAG 설정 조회
    """
    # Collection 결정
    manual_collection = runtime_settings.collection.collection_name
    if manual_collection:
        collection_name = manual_collection
        collection_mode = "manual"
    else:
        model_key = os.getenv("MODEL_KEY", "openai_large")
        base_collection = os.getenv("BASE_COLLECTION", "documents")
        collection_name = resolve_collection_name(base_collection, model_key)
        collection_mode = "auto"

    return {
        "embedding_model": runtime_settings.embedding.model_key,
        "llm_provider": runtime_settings.llm.provider,
        "llm_model": runtime_settings.llm.model,
        "available_providers": list(runtime_settings.llm.available_models.keys()),
        "collection": {
            "name": collection_name,
            "mode": collection_mode,
        },
    }
