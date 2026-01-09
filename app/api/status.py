from fastapi import APIRouter, HTTPException
from pipeline import status_store

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/status/{tracking_id}")
def file_status(tracking_id: str):
    data = status_store.get(tracking_id)
    if not data:
        raise HTTPException(status_code=404, detail="Tracking ID not found")

    return data
