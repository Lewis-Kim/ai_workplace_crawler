import os
import time
from datetime import datetime
from pathlib import Path
from watchdog.events import FileSystemEventHandler, FileMovedEvent

from config.db import SessionLocal
from services.ingest import ingest_file
from services.utils.file_hash import file_sha1
from services.utils.file_ops import move_file
from models.meta import MetaTable
from models.folder_status import FolderStatus
from pipeline import status_store



# ==========================
# 설정
# ==========================

from config.paths import (
    INCOMING_DIR,
    PROCESSING_DIR,
    PROCESSED_DIR,
    DUPLICATED_DIR,
    ERROR_DIR,
)

SUPPORTED_EXT = {
    ".pdf", ".txt", ".csv", ".docx",
    ".xlsx", ".xls",
    ".jpg", ".jpeg", ".png"
}


def ensure_dirs():
    for d in [INCOMING_DIR, PROCESSING_DIR, PROCESSED_DIR, DUPLICATED_DIR, ERROR_DIR]:
        os.makedirs(d, exist_ok=True)


class IngestHandler(FileSystemEventHandler):
    """
    ✅ 파일 + 폴더 모두 처리
    ✅ 폴더 단위 상태 관리: NEW -> INGESTING -> DONE/ERROR
    ✅ 문서 메타에는 folder_name 포함
    """

    def __init__(self):
        super().__init__()
        ensure_dirs()

    # --------------------------
    # 이벤트
    # --------------------------
    def on_created(self, event):
        if event.is_directory:
            self._handle_directory(event.src_path)
        else:
            self._handle_file(event.src_path)

    def on_moved(self, event: FileMovedEvent):
        path = event.dest_path
        if event.is_directory:
            self._handle_directory(path)
        else:
            self._handle_file(path)

    # --------------------------
    # 폴더 처리 + 폴더 상태 관리 (핵심)
    # --------------------------
    def _handle_directory(self, dir_path: str):
        print(f"[WATCH] directory detected: {dir_path}")

        if not self._wait_dir_until_ready(dir_path):
            print(f"[SKIP] directory not ready: {dir_path}")
            return

        folder_key, folder_name = self._get_folder_key_name(dir_path)

        # 1) 폴더 상태: NEW/INGESTING upsert
        db = SessionLocal()
        try:
            fs = db.query(FolderStatus).filter(FolderStatus.folder_key == folder_key).first()
            if not fs:
                fs = FolderStatus(
                    folder_key=folder_key,
                    folder_name=folder_name,
                    source="watcher",
                    status="NEW",
                    total_files=0,
                    processed_files=0,
                    error_files=0,
                    started_at=None,
                    finished_at=None
                )
                db.add(fs)
                db.commit()
                db.refresh(fs)

            # 이미 DONE 인데 또 들어오는 경우는 정책 선택:
            # - 재처리 허용: 아래처럼 INGESTING으로 다시 전환
            # - 재처리 금지: return
            fs.status = "INGESTING"
            fs.started_at = datetime.utcnow()
            fs.finished_at = None
            fs.processed_files = 0
            fs.error_files = 0

            files = list(self._iter_supported_files(dir_path))
            fs.total_files = len(files)
            db.commit()

        finally:
            db.close()

        # 2) 폴더 내 파일들 처리 (파일 단위 기존 로직 재사용)
        processed_ok = 0
        processed_err = 0

        for p in files:
            try:
                self._handle_file(str(p))
                processed_ok += 1
            except Exception:
                # _handle_file 내부에서 예외를 안 던지도록 해도 되지만,
                # 여기서는 "폴더 상태 ERROR 카운트"를 위해 안전하게 처리
                processed_err += 1

        # 3) 폴더 상태 DONE/ERROR 마감
        db = SessionLocal()
        try:
            fs = db.query(FolderStatus).filter(FolderStatus.folder_key == folder_key).first()
            if fs:
                fs.processed_files = processed_ok
                fs.error_files = processed_err
                fs.finished_at = datetime.utcnow()
                fs.status = "DONE" if processed_err == 0 else "ERROR"
                db.commit()

            print(f"[FOLDER] {folder_key} status={fs.status} total={fs.total_files} ok={fs.processed_files} err={fs.error_files}")
        finally:
            db.close()

    def _iter_supported_files(self, dir_path: str):
        for p in Path(dir_path).rglob("*"):
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXT:
                yield p

    def _get_folder_key_name(self, dir_path: str) -> tuple[str, str]:
        """
        folder_key: incoming 기준 상대경로 (다단 폴더 지원)
        folder_name: 마지막 폴더명
        """
        abs_in = os.path.abspath(INCOMING_DIR)
        abs_dir = os.path.abspath(dir_path)

        # incoming 밖이면 그냥 basename 기준으로 fallback
        if not abs_dir.startswith(abs_in):
            folder_name = os.path.basename(abs_dir)
            return folder_name, folder_name

        rel = os.path.relpath(abs_dir, abs_in)      # 예: "2025/보고서"
        folder_name = os.path.basename(abs_dir)     # 예: "보고서"
        return rel.replace("\\", "/"), folder_name

    # --------------------------
    # 파일 처리 (문서에 folder_name 포함)
    # --------------------------
    def _handle_file(self, src_path: str):
        if not os.path.exists(src_path):
            return

        _, ext = os.path.splitext(src_path)
        if ext.lower() not in SUPPORTED_EXT:
            return

        # ✅ 문서가 포함된 폴더명 (마지막 폴더명)
        folder_name = os.path.basename(os.path.dirname(src_path))

        print(f"[WATCH] file detected: {src_path} (folder={folder_name})")

        if not self._wait_until_ready(src_path):
            print(f"[SKIP] file not ready: {src_path}")
            return

        # incoming -> processing
        try:
            move_file(src_path, PROCESSING_DIR)
        except Exception as e:
            print(f"[ERROR] move to processing failed: {src_path} -> {e}")
            raise

        processing_path = os.path.join(PROCESSING_DIR, os.path.basename(src_path))

        db = SessionLocal()
        try:
            file_hash = file_sha1(processing_path)

            exists = db.query(MetaTable).filter(MetaTable.file_hash == file_hash).first()
            if exists:
                move_file(processing_path, DUPLICATED_DIR)
                print(f"[DUPLICATE] {processing_path}")
                return

            ingest_file(
                file_path=processing_path,
                source="watcher",
                db=db,
                folder_name=folder_name
            )

            move_file(processing_path, PROCESSED_DIR)
            print(f"[OK] processed: {processing_path}")

        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass

            try:
                move_file(processing_path, ERROR_DIR)
            except Exception:
                pass

            print(f"[ERROR] {processing_path} -> {e}")
            raise

        finally:
            db.close()

    # --------------------------
    # 파일 안정화
    # --------------------------
    def _wait_until_ready(self, file_path: str, timeout: int = 20) -> bool:
        start = time.time()
        last_size = -1
        stable = 0

        while time.time() - start < timeout:
            try:
                size = os.path.getsize(file_path)
            except (FileNotFoundError, PermissionError):
                time.sleep(0.5)
                continue

            if size == last_size and size > 0:
                stable += 1
                if stable >= 2:
                    return True
            else:
                stable = 0

            last_size = size
            time.sleep(0.5)

        return False

    # --------------------------
    # 폴더 안정화
    # --------------------------
    def _wait_dir_until_ready(self, dir_path: str, timeout: int = 60) -> bool:
        start = time.time()
        last_sig = None
        stable = 0

        while time.time() - start < timeout:
            sig = self._dir_signature(dir_path)
            if sig is None:
                time.sleep(0.5)
                continue

            if sig == last_sig:
                stable += 1
                if stable >= 2:
                    return True
            else:
                stable = 0

            last_sig = sig
            time.sleep(0.8)

        return False

    def _dir_signature(self, dir_path: str):
        try:
            total = 0
            count = 0
            for p in Path(dir_path).rglob("*"):
                if p.is_file():
                    stat = p.stat()
                    total += stat.st_size
                    count += 1
            return (count, total)
        except Exception:
            return None
        
        
    def _handle(self, file_path: str):
        filename = os.path.basename(file_path)
        tracking_id, _ = os.path.splitext(filename)

        # 처리 시작
        status_store.update(tracking_id, status_store.PROCESSING)

        try:
            ingest_file(file_path)
            status_store.update(tracking_id, status_store.COMPLETED)

        except Exception as e:
            status_store.update(
                tracking_id,
                status_store.FAILED,
                error=str(e),
            )
            raise

