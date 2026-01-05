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
PROCESSING_DIR = os.path.join(BASE_DIR, "processing")   # ✅ 추가 (핵심)
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
DUPLICATED_DIR = os.path.join(BASE_DIR, "duplicated")
ERROR_DIR = os.path.join(BASE_DIR, "error")

SUPPORTED_EXT = {
    ".pdf", ".txt", ".csv", ".docx",
    ".xlsx", ".xls",
    ".jpg", ".jpeg", ".png"
}


def ensure_dirs():
    for d in [INCOMING_DIR, PROCESSING_DIR, PROCESSED_DIR, DUPLICATED_DIR, ERROR_DIR]:
        os.makedirs(d, exist_ok=True)


# ==========================
# Watcher Handler
# ==========================

class IngestHandler(FileSystemEventHandler):
    """
    incoming 디렉터리를 감시하여
    파일 생성 시 자동 ingest 수행 (WinError32 방지 강화 버전)
    """

    def __init__(self):
        super().__init__()
        ensure_dirs()

    def on_created(self, event):
        if event.is_directory:
            return

        src_path = event.src_path
        _, ext = os.path.splitext(src_path)
        ext = ext.lower()

        if ext not in SUPPORTED_EXT:
            return

        print(f"[WATCH] detected: {src_path}")

        # 1️⃣ 파일 쓰기 완료 대기 (생성 직후/복사 중 방지)
        if not self._wait_until_ready(src_path):
            print(f"[SKIP] file not ready: {src_path}")
            return

        # 2️⃣ incoming → processing 으로 먼저 이동 (핵심: lock/충돌 최소화)
        try:
            move_file(src_path, PROCESSING_DIR)  # file_ops.py의 안정화+재시도 활용
        except Exception as e:
            print(f"[ERROR] move to processing failed: {src_path} -> {e}")
            # processing으로 못 옮기면 error로도 이동 시도
            try:
                move_file(src_path, ERROR_DIR)
            except Exception:
                pass
            return

        processing_path = os.path.join(PROCESSING_DIR, os.path.basename(src_path))
        db = SessionLocal()

        try:
            # 3️⃣ (processing 기준) 파일 해시 계산
            file_hash = file_sha1(processing_path)

            # 4️⃣ (processing 기준) 중복 파일 체크
            exists = db.query(MetaTable).filter(
                MetaTable.file_hash == file_hash
            ).first()

            if exists:
                # 중복이면 duplicated로 이동
                move_file(processing_path, DUPLICATED_DIR)
                print(f"[DUPLICATE] moved: {processing_path}")
                return

            # 5️⃣ ingest 실행 (processing 파일 대상으로)
            ingest_file(
                file_path=processing_path,
                source="watcher",
                db=db
            )

            # 6️⃣ 성공 → processed 이동
            move_file(processing_path, PROCESSED_DIR)
            print(f"[OK] processed: {processing_path}")

        except Exception as e:
            # ingest 실패 → rollback 후 error 이동
            try:
                db.rollback()
            except Exception:
                pass

            try:
                move_file(processing_path, ERROR_DIR)
            except Exception as me:
                print(f"[ERROR] move to error failed: {processing_path} -> {me}")

            print(f"[ERROR] {processing_path} -> {e}")

        finally:
            db.close()

    # --------------------------
    # 유틸: 파일 쓰기 완료 대기
    # --------------------------
    def _wait_until_ready(self, file_path: str, timeout: int = 20) -> bool:
        """
        파일 크기가 더 이상 변하지 않을 때까지 대기
        (복사 중 ingest 방지)
        """
        start = time.time()
        last_size = -1
        stable_count = 0

        while time.time() - start < timeout:
            try:
                size = os.path.getsize(file_path)
            except FileNotFoundError:
                return False
            except PermissionError:
                # 다른 프로세스가 잡고 있으면 잠깐 대기 후 재시도
                time.sleep(0.5)
                continue

            if size == last_size and size > 0:
                stable_count += 1
                # 2번 연속 동일하면 안정화로 판단 (엑셀/복사 지연 대비)
                if stable_count >= 2:
                    return True
            else:
                stable_count = 0

            last_size = size
            time.sleep(0.5)

        return False
