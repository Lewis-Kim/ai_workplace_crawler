# DataWave Project Tasks

Based on `PRD.md`, the following tasks are planned.

## Phase 1: Environment & Infrastructure Setup
- [x] Initialize Project Structure (FastAPI, directories)
- [x] Database Setup (MySQL, Qdrant)
- [x] Environment Variables Configuration (.env)
- [x] Logging & Monitoring Setup

## Phase 2: Core Service - Ingestion Pipeline (Ingest Service)
- [x] Implement File Watcher (Watchdog) for `watch_dir/incoming`
- [x] File Parser Implementation (PDF, DOCX, XLSX, TXT)
- [x] Image Extraction & OCR Integration
- [x] Text Chunking Logic
- [x] Duplicate File Detection (SHA1 Hash)
- [x] Database Schema Implementation (MySQL tables)

## Phase 3: RAG & Vector Engine
- [x] Qdrant Collection Management
- [x] Embedding Model Integration (OpenAI/Ollama)
- [x] Vector Storage & Indexing
- [x] Semantic Search Logic Implementation
- [x] Filtering & Scoring Logic

## Phase 4: Chat & Search API
- [x] RAG Generation Logic (Context + LLM)
- [x] LLM Integration (OpenAI, Gemini, Ollama)
- [x] API Endpoints Implementation:
    - [x] POST /files/upload
    - [x] POST /search
    - [x] POST /rag/chat
    - [x] GET /documents
    - [x] DELETE /documents/{id}

## Phase 5: Dashboard & Management UI
- [x] Dashboard Backend (Stats, Status)
- [x] Frontend Implementation (Vanilla JS + HTML/CSS)
    - [x] Dashboard View
    - [x] File Upload/List View
    - [x] Chat Interface
- [x] Real-time Log Streaming

## Phase 6: Testing & Optimization
- [x] Unit & Integration Tests
- [x] Performance Tuning (Async processing)
- [x] Security Review (Path traversal, API Keys)

## Phase 7: Document Management UI
- [x] meta_table 조회/관리 UI 구현
    - [x] 문서 목록 조회 (테이블 형식)
    - [x] 문서 상세 정보 표시 (chunk 수, image 수)
    - [x] 단일 문서 삭제 (MySQL + Qdrant 동시 삭제)
    - [x] 다중 문서 선택 삭제
    - [x] 폴더별 필터링
    - [x] 파일 타입별 필터링

## Phase 8: Pipeline Control UI
- [x] 대시보드에 파이프라인 제어 섹션 추가
    - [x] 파이프라인 상태 표시 (실행/중지, Observer 활성화)
    - [x] 시작 시간 및 Uptime 표시
    - [x] 시작/중지/재시작 버튼 구현
    - [x] 5초 간격 자동 상태 갱신
    - [x] Ingest Service 상태 연동

## Phase 9: Settings UI (LLM 모델 선택)
- [x] 런타임 설정 관리 모듈 구현 (config/runtime_settings.py)
- [x] 설정 API 구현 (app/api/settings.py)
    - [x] GET /settings - 현재 설정 조회
    - [x] PUT /settings/llm - LLM 설정 변경
    - [x] POST /settings/reset - 기본값 초기화
- [x] 환경설정 UI 구현 (templates/settings.html)
    - [x] LLM Provider 선택 (OpenAI, Ollama, Gemini)
    - [x] LLM Model 선택 (provider별 모델 목록)
    - [x] Embedding Model 표시 (읽기 전용)
    - [x] 설정 저장 기능
- [x] 사이드바에 환경설정 메뉴 추가
- [x] RAG API에서 런타임 설정 사용하도록 연동
- [x] DB 영구 저장 기능 추가
    - [x] system_settings 테이블 ORM 모델 (models/settings.py)
    - [x] 서버 시작 시 DB에서 설정 로드
    - [x] 설정 변경 시 DB에 자동 저장

## Phase 10: Qdrant Collection 선택 기능
- [x] Qdrant Collection 관리 API 구현
    - [x] GET /settings/collections - Qdrant에 존재하는 모든 collection 목록 조회
    - [x] PUT /settings/collections - 사용할 collection 선택/변경
- [x] RuntimeSettings에 Collection 설정 추가
    - [x] CollectionSettings 데이터클래스 추가
    - [x] set_collection() - collection 설정 변경 (DB 저장)
    - [x] get_collection_config() - 현재 collection 설정 조회
    - [x] DB 키: qdrant_collection_name
- [x] 설정 UI에 Collection 선택 섹션 추가
    - [x] Qdrant Collection Settings 카드 추가
    - [x] 드롭다운에서 collection 선택
    - [x] 선택한 collection의 vectors/points/dimension 정보 표시
    - [x] Save/Refresh 버튼
- [x] RAG API에서 선택된 Collection 사용
    - [x] 수동 선택된 collection 우선 사용
    - [x] 미선택 시 기존 자동 생성 방식 유지 (base_collection_model_key_version)

## Phase 11: UI/UX 개선
- [x] iframe 스크롤바 개선
    - [x] 콘텐츠가 화면보다 클 때 스크롤바 표시
    - [x] 모달 스타일 커스텀 스크롤바 적용
        - [x] 파란색 그라데이션 (#3b82f6 → #2563eb)
        - [x] Hover 시 밝은 파란색 (#60a5fa → #3b82f6)
        - [x] 반투명 어두운 트랙 배경
        - [x] Firefox 지원 (scrollbar-width, scrollbar-color)
    - [x] index.html - scrolling="no" 제거, 동적 스크롤 활성화 로직
    - [x] iframe_base.html - 리사이즈 메시지 개선
    - [x] main.css - 모달 스타일 스크롤바 CSS 추가
    - [x] iframe.css - iframe 내부 스크롤바 스타일 통일
