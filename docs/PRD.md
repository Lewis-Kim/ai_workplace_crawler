# DataWave - RAG 문서 관리 시스템 PRD

## 1. 개요 (Overview)
### 1.1 제품 비전
DataWave는 조직 내 분산된 다양한 형태의 문서(PDF, Word, Excel 등)를 자동으로 수집, 분석하여 지식 자산화하고, 이를 AI 기술(RAG)을 통해 효율적으로 활용할 수 있게 돕는 통합 문서 관리 솔루션입니다.

### 1.2 목표 사용자
- 대량의 사내 문서를 관리하고 정보를 빠르게 찾아야 하는 기업 실무자
- 기술 문서, 보고서 등에서 특정 지식을 추출하여 답변을 얻고자 하는 연구원/엔지니어
- 자동화된 문서 파이프라인 구축이 필요한 시스템 관리자

### 1.3 핵심 가치 제안
- **자동 지식화**: 폴더 감시를 통한 실시간 문서 수집 및 벡터화 자동화
- **멀티모달 대응**: 텍스트뿐만 아니라 문서 내 이미지 및 OCR 처리 지원
- **유연한 AI 선택**: OpenAI, Google Gemini, Ollama(로컬) 등 다양한 LLM 연동
- **신속한 정보 접근**: 단순 키워드 검색을 넘어선 의미론적(Semantic) 검색 및 질의응답

## 2. 기능 요구사항 (Functional Requirements)

### 2.1 문서 업로드 및 처리
- **다양한 포맷 지원**: PDF, DOCX, XLSX, CSV, TXT, 이미지(JPG, PNG) 지원
- **자동 수집(Watcher)**: 지정된 폴더(`watch_dir/incoming`)에 파일 생성 시 자동 처리 시작
- **중복 방지**: SHA1 해시 기반의 파일 중복 체크 및 별도 관리(`duplicated` 폴더)
- **추출 및 파싱**:
    - 문서 내 텍스트 추출 및 Chunking 처리
    - 문서 내 포함된 이미지 자동 분리 및 저장
    - 이미지에 대한 OCR 처리 및 캡셔닝 생성 지원

### 2.2 벡터 검색
- **의미론적 검색**: Qdrant 벡터 DB를 활용한 유사도 기반 검색
- **필터링**: 폴더명, 파일 타입별 검색 결과 필터링 기능
- **스코어링**: 검색 결과에 대한 유사도 점수 제공 및 임계값(Threshold) 설정 가능

### 2.3 RAG 질의응답
- **컨텍스트 기반 답변**: 검색된 문서 조각을 LLM에 전달하여 근거 기반 답변 생성
- **멀티 LLM 지원**:
    - OpenAI (GPT-4o mini 등)
    - Google Gemini (Gemini 1.5 Flash 등)
    - Ollama (Llama 3.2 등 로컬 모델)
- **출처 제공**: 답변 생성에 사용된 참고 문서 목록 및 페이지 번호 표시

### 2.4 대시보드
- **통계 요약**: 총 문서 수, 처리 성공, 중복, 에러 상태 시각화
- **시스템 상태 모니터링**: Ingest Service, Vector DB 연결 상태 및 사용 중인 임베딩 모델 정보 표시
- **실시간 로그**: 백엔드에서 발생하는 처리 로그를 실시간으로 스트리밍하여 표시

### 2.5 문서 관리
- **목록 조회**: 업로드된 전체 문서 리스트 및 상세 정보 조회
- **삭제 및 관리**: 
    - 개별 문서 삭제 (DB, 벡터 DB, 파일시스템 연동 삭제)
    - 폴더 단위 일괄 삭제 기능
    - 처리 실패 파일 재처리 대기 관리

## 3. 비기능 요구사항 (Non-Functional Requirements)

### 3.1 성능
- **비동기 처리**: 대용량 파일 처리를 위한 비동기 파이프라인 구조
- **확장성**: 문서 로더 및 벡터 DB 클라이언트의 플러그인 인터페이스 구조

### 3.2 보안
- **환경 변수 관리**: API 키 및 DB 자격 증명을 `.env` 파일을 통해 격리 관리
- **파일 경로 보호**: `Path.resolve` 등을 통한 디렉토리 트래버설 방지

### 3.3 확장성
- 새로운 문서 타입 추가를 위한 Loader 클래스 확장 구조
- 새로운 벡터 DB 지원을 위한 Collection Manager 모듈화

## 4. 시스템 아키텍처

### 4.1 전체 구조도
```text
[사용자 UI (FastAPI Templates)]
       │
[API 레이어 (FastAPI)] ◄──── [폴더 감시 (Watchdog)]
       │                           │
[서비스 레이어 (Ingest/RAG)] ──────┘
       │
       ├─ [문서 파서 (PyMuPDF/Docx/Pandas)]
       ├─ [이미지 처리 (OCR/Pillow)]
       ├─ [임베딩 (OpenAI/Ollama)]
       │
[데이터 레이어]
       ├─ MySQL (Metadata, Chunks, Image Meta)
       ├─ Qdrant (Vector Data)
       └─ Local File System (Raw Files, Extracted Images)
```

### 4.2 데이터 흐름
1. 파일 업로드/유입 -> 2. SHA1 해시 계산 -> 3. 메타데이터 DB 저장 -> 4. 이미지 추출/저장 -> 5. 텍스트 추출/Chunking -> 6. 벡터 임베딩 생성 -> 7. Qdrant 저장

## 5. 데이터 모델

### 5.1 DB 스키마 (MySQL)
- `meta_table`: 문서 기본 메타정보 (ID, 제목, 해시, 타입 등)
- `content_table`: 텍스트 조각 및 페이지 정보
- `images`: 추출된 이미지 경로 및 OCR 결과
- `folder_status`: 일괄 처리 상태 추적

### 5.2 벡터 DB 구조 (Qdrant)
- `Collection`: `{base_name}_{model_key}` 형식
- `Payload`: `content`, `metadata` (doc_id, page_no, folder_name 등)
- `Vector`: 임베딩 모델 설정에 따른 차원(Dimension) 데이터

## 6. API 명세 요약
- `POST /files/upload`: 개별 파일 업로드
- `POST /search`: 벡터 유사도 검색
- `POST /rag/chat`: RAG 기반 질의응답
- `GET /api/dashboard/summary`: 시스템 통계 조회
- `GET /documents`: 문서 목록 및 상세 조회
- `DELETE /documents/{id}`: 문서 및 관련 데이터 영구 삭제

## 7. 기술 스택
- **Language**: Python 3.14+
- **Framework**: FastAPI
- **Database**: MySQL 8.0+, Qdrant
- **ORM**: SQLAlchemy
- **Parsing**: PyMuPDF, python-docx, Pandas, Pytesseract
- **LLM/AI**: OpenAI API, Google Generative AI, Ollama
- **Frontend**: Vanilla JS, HTML5, CSS3

## 8. 향후 로드맵
- **멀티모달 검색**: 텍스트를 넘어선 이미지 유사도 검색 지원
- **권한 관리**: 사용자별/그룹별 문서 접근 제어 기능
- **리포트 자동 생성**: 수집된 지식을 바탕으로 일일/주간 요약 리포트 자동 생성
- **Web Crawler 연동**: 특정 웹사이트 콘텐츠 자동 수집 기능 확장
