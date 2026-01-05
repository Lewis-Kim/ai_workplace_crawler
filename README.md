# 🧠 AI_WORKPLACE_CRAWLER

문서(PDF, DOCX, XLSX, CSV, TXT, 이미지)를 자동 수집·분석하여  
**텍스트와 이미지를 분리 저장**하고,  
AI/RAG 처리를 위한 **표준화된 데이터 구조로 적재**하는 파이프라인입니다.

---

## 1. 주요 기능

- 📂 **폴더 감시 기반 자동 수집 (Watch Directory)**
- 🔁 **파일 중복 방지 (SHA1 해시)**
- 📄 **문서 텍스트 추출 + Chunking**
- 🖼 **문서 내 이미지 자동 분리 저장**
- 🗄 **MySQL (SQLAlchemy ORM) 기반 메타/콘텐츠 관리**
- 🧠 **OCR / Vision / VectorDB 확장 가능 구조**

---

## 2. 전체 아키텍처 개요
```
파일 업로드
↓
파일 해시 계산 (중복 방지)
↓
meta_table (문서 메타 저장)
↓
이미지 추출
├─ 파일 시스템 저장 (images/{doc_id}/)
└─ images 테이블 INSERT
↓
텍스트 로딩
↓
chunking
↓
content_table INSERT
```

---

## 3. 디렉터리 구조

```text
AI_WORKPLACE_CRAWLER/
├─ batch/
│  └─ folder_batch.py
│
├─ config/
│  ├─ db.py                 # SQLAlchemy DB 설정
│  └─ settings.py           # 환경 설정
│
├─ images/
│  └─ {doc_id}/
│     └─ (문서별 이미지 저장 디렉토리)
│
├─ models/
│  ├─ meta.py               # meta_table ORM
│  ├─ content.py            # content_table ORM
│  └─ ImageTable.py         # images 테이블 ORM
│
├─ services/
│  ├─ ingest.py             # 핵심 ingest 로직 (텍스트 + 이미지)
│  ├─ chunking.py           # 텍스트 chunking
│  │
│  ├─ loaders/              # 문서 타입별 로더
│  │  ├─ pdf_loader.py
│  │  ├─ docx_loader.py
│  │  ├─ excel_loader.py
│  │  ├─ csv_loader.py
│  │  ├─ txt_loader.py
│  │  └─ image_ocr_loader.py
│  │
│  ├─ images/               # 이미지 처리 전용 모듈
│  │  └─ image_extractor.py
│  └─ utils/
│     └─ file_hash.py       # SHA1 해시 계산
│
├─ watch_dir/
│  ├─ incoming/             # 신규 유입 파일
│  ├─ processed/            # 처리 완료 파일
│  ├─ duplicated/           # 중복 파일
│  └─ error/                # 처리 실패 파일
│
├─ watcher/
│  └─ file_watcher.py       # 디렉토리 감시 로직
|
├─ .env                     # 환경 변수
├─ LICENSE
├─ main.py                  # 단일 실행 진입점
├─ main_pipeline.py         # 배치/파이프라인 실행
├─ main_watch.py            # watch_dir 감시 실행
├─ README.md
└─ requirements.txt
```
## 4. DB 테이블 구조

### 4.1 meta_table (문서 메타)

```sql
-- project3.meta_table definition

CREATE TABLE `meta_table` (
  `seq_id` int NOT NULL AUTO_INCREMENT COMMENT '문서 ID',
  `title` varchar(100) DEFAULT NULL COMMENT '제목',
  `file_type` varchar(45) DEFAULT NULL COMMENT '파일타입',
  `sorce` varchar(45) DEFAULT NULL COMMENT '출처',
  `create_dt` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
  `file_hash` char(40) DEFAULT NULL,
  `embeding_yn` char(1) DEFAULT NULL,
  PRIMARY KEY (`seq_id`),
  UNIQUE KEY `ux_file_hash` (`file_hash`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

```
### 4.2 content_table (텍스트 chunk)
```sql
-- project3.content_table definition

CREATE TABLE `content_table` (
  `content_id` int NOT NULL AUTO_INCREMENT COMMENT '문서아이디',
  `doc_id` int NOT NULL COMMENT 'meta_table.seq_id',
  `page_no` int DEFAULT NULL COMMENT '페이지 번호',
  `chunk_no` int DEFAULT NULL COMMENT '청크 번호',
  `content` text COMMENT '텍스트 내용',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`content_id`),
  KEY `idx_doc` (`doc_id`),
  FULLTEXT KEY `ft_content` (`content`),
  CONSTRAINT `fk_doc` FOREIGN KEY (`doc_id`) REFERENCES `meta_table` (`seq_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1317 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

```
### 4.3 images (이미지 메타)
```sql
-- project3.images definition

CREATE TABLE `images` (
  `seq_id` int NOT NULL AUTO_INCREMENT COMMENT '이미지 ID',
  `doc_id` int NOT NULL COMMENT '문서 ID (meta_table.seq_id)',
  `page_no` int DEFAULT NULL COMMENT '페이지 번호',
  `image_no` int DEFAULT NULL COMMENT '페이지 내 이미지 순번',
  `image_path` varchar(512) NOT NULL COMMENT '이미지 파일 경로',
  `image_name` varchar(255) NOT NULL COMMENT '이미지 파일명',
  `image_ext` varchar(10) NOT NULL COMMENT '확장자',
  `ocr_text` longtext COMMENT 'OCR 결과',
  `caption` longtext COMMENT '이미지 설명',
  `embedding_id` varchar(128) DEFAULT NULL COMMENT '벡터 DB ID',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
  PRIMARY KEY (`seq_id`),
  KEY `idx_images_doc_id` (`doc_id`),
  CONSTRAINT `fk_images_meta` FOREIGN KEY (`doc_id`) REFERENCES `meta_table` (`seq_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=72 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```
## 5. 설치 방법
### 5.1 Python 가상환경 생성

```bash
python -m venv venv
source venv/bin/activate     # Linux / Mac
venv\Scripts\activate        # Windows
```
### 5.2 패키지 설치
```bash
pip install -r requirements.txt
```
### 5.3 환경 변수 설정
.env 파일 생성:

```env
DB_HOST=localhost
DB_PORT=3306
<<<<<<< HEAD
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_CHARSET=utf8mb4

OPENAI_API_KEY=

를 복사해서 디비 정보를 넣고 저장
