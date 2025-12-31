import os
import time

from config.db import SessionLocal
from services.ingest import ingest_file
from services.utils.file_hash import file_sha1
from services.utils.file_ops import move_file
from models.meta import MetaTable


SUPPORTED_EXT = {
    ".pdf", ".txt", ".csv", ".docx",
    ".xlsx", ".xls",
    ".jpg", ".jpeg", ".png"
}

BASE_DIR = "watch_dir"
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
DUPLICATED_DIR = os.path.join(BASE_DIR, "duplicated")
ERROR_DIR = os.path.join(BASE_DIR, "error")


def batch_ingest_folder(folder_path: str):
    """
    폴더 내 기존 파일 전체 ingest (운영용)
    - 중복 파일 분리
    - 성공/실패 파일 이동
    """
    print(f"[BATCH] scanning folder: {folder_path}")

    files = sorted(
        f for f in os.listdir(folder_path)
        if os.path.splitext(f)[1].lower() in SUPPORTED_EXT
    )

    for filename in files:
        file_path = os.path.join(folder_path, filename)

        # 🔹 파일 준비 대기 (복사 중 방지)
        if not _wait_until_ready(file_path):
            print(f"[BATCH SKIP] not ready: {filename}")
            continue

        db = SessionLocal()
        try:
            # 🔹 중복 체크
            file_hash = file_sha1(file_path)
            exists = db.query(MetaTable).filter(
                MetaTable.file_hash == file_hash
            ).first()

            if exists:
                move_file(file_path, DUPLICATED_DIR)
                print(f"[BATCH DUPLICATE] {filename}")
                continue

            # 🔹 ingest
            ingest_file(
                file_path=file_path,
                source="batch",
                db=db
            )

            # 🔹 정상 처리
            move_file(file_path, PROCESSED_DIR)
            print(f"[BATCH OK] {filename}")

        except Exception as e:
            move_file(file_path, ERROR_DIR)
            print(f"[BATCH FAIL] {filename} -> {e}")

        finally:
            db.close()


def _wait_until_ready(file_path: str, timeout: int = 15) -> bool:
    """
    파일 크기 변경이 멈출 때까지 대기
    """
    start = time.time()
    last_size = -1

    while time.time() - start < timeout:
        try:
            size = os.path.getsize(file_path)
        except FileNotFoundError:
            return False

        if size == last_size:
            return True

        last_size = size
        time.sleep(0.5)

    return False
