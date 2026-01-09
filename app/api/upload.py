import os
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from services.utils.file_ops import resolve_duplicate_filename

from pipeline import status_store

BASE_DIR = "watch_dir"
INCOMING_DIR = os.path.join(BASE_DIR, "incoming")

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename")

    os.makedirs(INCOMING_DIR, exist_ok=True)

    tracking_id = uuid.uuid4().hex

    safe_filename = resolve_duplicate_filename(
        INCOMING_DIR,
        file.filename
    )

    dest_path = os.path.join(INCOMING_DIR, safe_filename)

    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        await file.close()

    status_store.create(
        tracking_id=tracking_id,
        filename=safe_filename,
        path=dest_path,
    )

    return {
        "tracking_id": tracking_id,
        "filename": safe_filename,
        "status": "uploaded",
    }
