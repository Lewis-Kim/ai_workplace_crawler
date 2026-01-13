# api/logs.py
import os
import asyncio
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

# 프로젝트 루트 기준 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_FILE = BASE_DIR / "logs" / "system.log"

# 로그 디렉토리 생성
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


@router.get("/logs")
def read_logs(limit: int = 200):
    """기존 로그 조회 API (polling용)"""
    if not LOG_FILE.exists():
        return {"logs": []}

    lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
    return {
        "logs": lines[-limit:]
    }


@router.get("/logs/stream")
async def stream_logs():
    """
    SSE(Server-Sent Events) 기반 실시간 로그 스트리밍
    
    - 파일 변경 감지하여 새 로그만 전송
    - 클라이언트 연결 유지
    """
    async def log_generator():
        last_position = 0
        last_size = 0
        
        # 파일이 없으면 생성될 때까지 대기
        while not LOG_FILE.exists():
            yield f"data: [SYSTEM] Waiting for log file...\n\n"
            await asyncio.sleep(2)
        
        # 초기 위치를 파일 끝으로 설정 (기존 로그는 건너뛰기)
        try:
            last_size = LOG_FILE.stat().st_size
            last_position = last_size
        except:
            pass
        
        yield f"data: [SYSTEM] Log streaming started\n\n"
        
        while True:
            try:
                current_size = LOG_FILE.stat().st_size
                
                # 파일이 truncate 되었거나 새로 생성된 경우
                if current_size < last_position:
                    last_position = 0
                
                # 새 내용이 있으면 읽기
                if current_size > last_position:
                    with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                        f.seek(last_position)
                        new_content = f.read()
                        last_position = f.tell()
                    
                    # 새 라인들을 SSE 형식으로 전송
                    for line in new_content.strip().split("\n"):
                        if line.strip():
                            # SSE 형식: data: <content>\n\n
                            yield f"data: {line}\n\n"
                
            except FileNotFoundError:
                yield f"data: [SYSTEM] Log file not found, waiting...\n\n"
            except Exception as e:
                yield f"data: [ERROR] {str(e)}\n\n"
            
            # 100ms 간격으로 폴링 (실시간에 가까운 반응)
            await asyncio.sleep(0.1)
    
    return StreamingResponse(
        log_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx 버퍼링 비활성화
        }
    )
