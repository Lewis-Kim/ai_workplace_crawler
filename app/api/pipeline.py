from fastapi import APIRouter
from datetime import datetime

from pipeline import state
from pipeline.runner import (
    start_pipeline,
    stop_pipeline,
    restart_pipeline,
)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


# -------------------------
# 상태 확인
# -------------------------
@router.get("/status")
def pipeline_status():
    running = state.observer is not None
    alive = bool(state.observer and state.observer.is_alive())

    uptime = None
    if state.started_at:
        uptime = (datetime.now() - state.started_at).total_seconds()

    return {
        "running": running,
        "observer_alive": alive,
        "started_at": state.started_at,
        "uptime_seconds": uptime,
    }


# -------------------------
# 시작
# -------------------------
@router.post("/start")
def pipeline_start():
    if state.observer:
        return {
            "status": "already_running",
            "timestamp": datetime.now(),
        }

    start_pipeline()
    return {
        "status": "started",
        "timestamp": datetime.now(),
    }


# -------------------------
# 중지
# -------------------------
@router.post("/stop")
def pipeline_stop():
    if not state.observer:
        return {
            "status": "already_stopped",
            "timestamp": datetime.now(),
        }

    stop_pipeline()
    return {
        "status": "stopped",
        "timestamp": datetime.now(),
    }


# -------------------------
# 재시작
# -------------------------
@router.post("/restart")
def pipeline_restart():
    restart_pipeline()
    return {
        "status": "restarted",
        "timestamp": datetime.now(),
    }
