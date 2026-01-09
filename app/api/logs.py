# api/logs.py
from fastapi import APIRouter
from pathlib import Path

router = APIRouter()
LOG_FILE = Path("../../logs/system.log")

print("🔥 LOGS ROUTER LOADED")

@router.get("/logs")
def read_logs(limit: int = 200):
    if not LOG_FILE.exists():
        return {"logs": []}

    lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
    return {
        "logs": lines[-limit:]
    }
