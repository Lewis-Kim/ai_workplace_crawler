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
