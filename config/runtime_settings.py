# config/runtime_settings.py
"""
런타임 설정 관리 모듈

설정 우선순위: DB > 환경변수(.env) > 기본값
서버 시작 시 DB에서 설정을 로드하고, 변경 시 DB에 저장합니다.
"""

import os
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger("settings")


@dataclass
class LLMSettings:
    """LLM 관련 설정"""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    
    # Provider별 사용 가능한 모델 목록
    available_models: dict = field(default_factory=lambda: {
        "openai": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
        ],
        "ollama": [
            "llama3.2",
            "llama3.1",
            "llama3",
            "mistral",
            "codellama",
            "gemma2",
            "qwen2.5",
        ],
        "gemini": [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-pro",
        ],
    })


@dataclass  
class EmbeddingSettings:
    """임베딩 관련 설정"""
    model_key: str = "openai_large"
    
    # 사용 가능한 임베딩 모델 (model_key -> 설명)
    available_models: dict = field(default_factory=lambda: {
        "openai_large": {
            "name": "OpenAI text-embedding-3-large",
            "dimension": 3072,
            "engine": "openai",
            "description": "OpenAI 최고 성능 모델 (API 키 필요)"
        },
        "nomic": {
            "name": "Ollama nomic-embed-text",
            "dimension": 768,
            "engine": "ollama",
            "description": "Ollama 로컬 모델 (무료)"
        },
        "bge_m3": {
            "name": "Ollama bge-m3",
            "dimension": 1024,
            "engine": "ollama",
            "description": "다국어 지원 로컬 모델"
        },
        "gemini_embed": {
            "name": "Google embedding-001",
            "dimension": 768,
            "engine": "gemini",
            "description": "Google Gemini 임베딩 (API 키 필요)"
        },
        "gemma2_embed": {
            "name": "Ollama gemma2 embedding",
            "dimension": 768,
            "engine": "ollama",
            "description": "Gemma2 기반 로컬 모델"
        },
    })


class RuntimeSettings:
    """
    런타임 설정 싱글톤 (DB 영구 저장)
    
    사용법:
        from config.runtime_settings import runtime_settings
        
        # 조회
        provider = runtime_settings.llm.provider
        model = runtime_settings.llm.model
        
        # 변경 (자동 DB 저장)
        runtime_settings.set_llm("ollama", "llama3.2")
    """
    
    _instance: Optional["RuntimeSettings"] = None
    
    # 설정 키 상수
    KEY_LLM_PROVIDER = "llm_provider"
    KEY_LLM_MODEL = "llm_model"
    KEY_EMBEDDING_MODEL = "embedding_model_key"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 기본값으로 초기화
        self.llm = LLMSettings(
            provider=os.getenv("LLM_PROVIDER", "openai"),
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        )
        
        self.embedding = EmbeddingSettings(
            model_key=os.getenv("MODEL_KEY", "openai_large"),
        )
        
        self._initialized = True
        
        # DB에서 설정 로드 시도
        self._load_from_db()
    
    def _get_db_session(self):
        """DB 세션 가져오기"""
        try:
            from config.db import SessionLocal
            return SessionLocal()
        except Exception as e:
            logger.warning(f"[SETTINGS] DB session failed: {e}")
            return None
    
    def _load_from_db(self):
        """DB에서 설정 로드"""
        session = self._get_db_session()
        if not session:
            return
            
        try:
            from models.settings import SystemSettings
            
            # LLM Provider
            provider_row = session.query(SystemSettings).filter(
                SystemSettings.setting_key == self.KEY_LLM_PROVIDER
            ).first()
            if provider_row:
                self.llm.provider = provider_row.setting_value
            
            # LLM Model
            model_row = session.query(SystemSettings).filter(
                SystemSettings.setting_key == self.KEY_LLM_MODEL
            ).first()
            if model_row:
                self.llm.model = model_row.setting_value
            
            # Embedding Model
            embed_row = session.query(SystemSettings).filter(
                SystemSettings.setting_key == self.KEY_EMBEDDING_MODEL
            ).first()
            if embed_row:
                self.embedding.model_key = embed_row.setting_value
            
            logger.info(f"[SETTINGS] Loaded from DB: LLM={self.llm.provider}/{self.llm.model}, Embedding={self.embedding.model_key}")
            
        except Exception as e:
            logger.warning(f"[SETTINGS] DB load failed (using defaults): {e}")
        finally:
            session.close()
    
    def _save_to_db(self, key: str, value: str, description: str = None):
        """DB에 설정 저장 (upsert)"""
        session = self._get_db_session()
        if not session:
            return False
            
        try:
            from models.settings import SystemSettings
            
            # 기존 레코드 찾기
            existing = session.query(SystemSettings).filter(
                SystemSettings.setting_key == key
            ).first()
            
            if existing:
                existing.setting_value = value
                if description:
                    existing.description = description
            else:
                new_setting = SystemSettings(
                    setting_key=key,
                    setting_value=value,
                    description=description
                )
                session.add(new_setting)
            
            session.commit()
            logger.info(f"[SETTINGS] Saved to DB: {key}={value}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"[SETTINGS] DB save failed: {e}")
            return False
        finally:
            session.close()
    
    def set_llm(self, provider: str, model: str) -> bool:
        """
        LLM 설정 변경 (메모리 + DB 저장)
        
        Args:
            provider: openai, ollama, gemini
            model: provider별 모델명
            
        Returns:
            성공 여부
        """
        if provider not in self.llm.available_models:
            return False
        
        # 메모리 업데이트
        self.llm.provider = provider
        self.llm.model = model
        
        # DB 저장
        self._save_to_db(self.KEY_LLM_PROVIDER, provider, "LLM 제공자")
        self._save_to_db(self.KEY_LLM_MODEL, model, "LLM 모델명")
        
        return True
    
    def set_embedding(self, model_key: str) -> dict:
        """
        Embedding 모델 변경 (메모리 + DB 저장)
        
        ⚠️ 주의: 모델 변경 시 재인덱싱 필요
        
        Args:
            model_key: 임베딩 모델 키 (openai_large, nomic 등)
            
        Returns:
            변경 결과 및 경고 메시지
        """
        if model_key not in self.embedding.available_models:
            return {
                "success": False,
                "error": f"Unknown model_key: {model_key}",
            }
        
        old_model = self.embedding.model_key
        
        # 메모리 업데이트
        self.embedding.model_key = model_key
        
        # DB 저장
        self._save_to_db(
            self.KEY_EMBEDDING_MODEL, 
            model_key, 
            "임베딩 모델 키"
        )
        
        # 환경변수도 업데이트 (현재 프로세스 내에서만)
        os.environ["MODEL_KEY"] = model_key
        
        new_config = self.embedding.available_models[model_key]
        old_config = self.embedding.available_models.get(old_model, {})
        
        return {
            "success": True,
            "old_model": old_model,
            "new_model": model_key,
            "old_dimension": old_config.get("dimension"),
            "new_dimension": new_config.get("dimension"),
            "requires_reindex": old_model != model_key,
            "warning": "모델이 변경되었습니다. 기존 문서를 검색하려면 재인덱싱이 필요합니다." if old_model != model_key else None,
        }
    
    def get_llm_config(self) -> dict:
        """현재 LLM 설정 반환"""
        return {
            "provider": self.llm.provider,
            "model": self.llm.model,
            "available_providers": list(self.llm.available_models.keys()),
            "available_models": self.llm.available_models,
        }
    
    def get_embedding_config(self) -> dict:
        """현재 임베딩 설정 반환"""
        current_model = self.embedding.available_models.get(self.embedding.model_key, {})
        return {
            "model_key": self.embedding.model_key,
            "model_info": current_model,
            "available_models": self.embedding.available_models,
        }
    
    def to_dict(self) -> dict:
        """전체 설정을 dict로 반환"""
        return {
            "llm": self.get_llm_config(),
            "embedding": self.get_embedding_config(),
            "storage": "database",  # 저장 방식 표시
        }
    
    def reset_to_env(self):
        """환경변수 값으로 초기화 (DB도 업데이트)"""
        env_provider = os.getenv("LLM_PROVIDER", "openai")
        env_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        env_embedding = os.getenv("MODEL_KEY", "openai_large")
        
        self.llm.provider = env_provider
        self.llm.model = env_model
        self.embedding.model_key = env_embedding
        
        # DB도 업데이트
        self._save_to_db(self.KEY_LLM_PROVIDER, env_provider, "LLM 제공자")
        self._save_to_db(self.KEY_LLM_MODEL, env_model, "LLM 모델명")
        self._save_to_db(self.KEY_EMBEDDING_MODEL, env_embedding, "임베딩 모델 키")
        
        logger.info(f"[SETTINGS] Reset to environment defaults: LLM={env_provider}/{env_model}, Embedding={env_embedding}")
    
    def reload_from_db(self):
        """DB에서 설정 다시 로드"""
        self._load_from_db()


# 싱글톤 인스턴스
runtime_settings = RuntimeSettings()
