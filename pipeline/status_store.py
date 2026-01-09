from datetime import datetime
from typing import Dict

# status values
UPLOADED = "uploaded"
PROCESSING = "processing"
COMPLETED = "completed"
FAILED = "failed"

_status: Dict[str, dict] = {}


def create(tracking_id: str, filename: str, path: str):
    _status[tracking_id] = {
        "tracking_id": tracking_id,
        "filename": filename,
        "path": path,
        "status": UPLOADED,
        "created_at": datetime.now(),
        "updated_at": None,
        "error": None,
    }


def update(tracking_id: str, status: str, error: str | None = None):
    if tracking_id not in _status:
        return

    _status[tracking_id]["status"] = status
    _status[tracking_id]["updated_at"] = datetime.now()
    _status[tracking_id]["error"] = error


def get(tracking_id: str):
    return _status.get(tracking_id)
