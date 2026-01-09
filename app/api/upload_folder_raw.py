import os
import shutil
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, Header, HTTPException

from pipeline import status_store

BASE_DIR = "watch_dir"
INCOMING_DIR = Path(BASE_DIR) / "incoming"

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload-folder-raw")
async def upload_folder_raw(
    files: List[UploadFile] = File(...),
    base_dir: str | None = Header(default=None, alias="X-Base-Dir"),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    INCOMING_DIR.mkdir(parents=True, exist_ok=True)

    saved_files = []

    for file in files:
        # ⭐ 핵심: filename에 상대경로가 포함되어 들어옴
        # 예: reports/2026/q1/a.pdf
        rel_path = Path(file.filename)

        # 보안: 경로 탈출 방지
        if ".." in rel_path.parts:
            raise HTTPException(status_code=400, detail="Invalid path")

        # 기준 폴더 강제 지정 (선택)
        if base_dir:
            rel_path = Path(base_dir) / rel_path

        dest_path = INCOMING_DIR / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(dest_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        finally:
            await file.close()

        # 상태 등록 (파일 단위)
        status_store.create(
            tracking_id=dest_path.as_posix(),
            filename=dest_path.name,
            path=str(dest_path),
        )

        saved_files.append(str(dest_path))

    return {
        "status": "uploaded",
        "files_count": len(saved_files),
        "files": saved_files,
    }
