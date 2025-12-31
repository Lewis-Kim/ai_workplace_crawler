import os
import time
from watchdog.events import FileSystemEventHandler

from config.db import SessionLocal
from services.ingest import ingest_file
from services.utils.file_hash import file_sha1
from services.utils.file_ops import move_file
from models.meta import MetaTable


# ==========================
# 설정
# ==========================

BASE_DIR = "watch_dir"

INCOMING_DIR = os.path.join(BASE_DIR, "incoming")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
DUPLICATED_DIR = os.path.join(BASE_DIR, "duplicated")
ERROR_DIR = os.path.join(BASE_DIR, "error")

SUPPORTED_EXT = {
    ".pdf", ".txt", ".csv", ".docx",
    ".xlsx", ".xls",
    ".jpg", ".jpeg", ".png"
}


# ==========================
# Watcher Handler
# ==========================

class IngestHandler(FileSystemEventHandler):
    """
    incoming 디렉터리를 감시하여
    파일 생성 시 자동 ingest 수행
    """

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        if ext not in SUPPORTED_EXT:
            return

        print(f"[WATCH] detected: {file_path}")

        # 1️⃣ 파일 쓰기 완료 대기
        if not self._wait_until_ready(file_path):
            print(f"[SKIP] file not ready: {file_path}")
            return

        db = SessionLocal()

        try:
            # 2️⃣ 파일 해시 계산
            file_hash = file_sha1(file_path)

            # 3️⃣ 중복 파일 체크
            exists = db.query(MetaTable).filter(
                MetaTable.file_hash == file_hash
            ).first()

            if exists:
                move_file(file_path, DUPLICATED_DIR)
                print(f"[DUPLICATE] moved: {file_path}")
                return

            # 4️⃣ ingest 실행
            ingest_file(
                file_path=file_path,
                source="watcher",
                db=db
            )

            # 5️⃣ 정상 처리 → processed 이동
            move_file(file_path, PROCESSED_DIR)
            print(f"[OK] processed: {file_path}")

        except Exception as e:
            # 6️⃣ 에러 발생 → error 이동
            move_file(file_path, ERROR_DIR)
            print(f"[ERROR] {file_path} -> {e}")

        finally:
            db.close()

    # --------------------------
    # 유틸: 파일 쓰기 완료 대기
    # --------------------------

    def _wait_until_ready(self, file_path: str, timeout: int = 15) -> bool:
        """
        파일 크기가 더 이상 변하지 않을 때까지 대기
        (복사 중 ingest 방지)
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
