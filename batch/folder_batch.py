from pathlib import Path
import os

from watcher.file_watcher import IngestHandler, SUPPORTED_EXT


def batch_ingest_folder(root_dir: str):
    """
    서버 시작 시 incoming 디렉터리 초기 스캔
    - 폴더 → IngestHandler._handle_directory
    - 파일 → IngestHandler._handle_file
    ⚠ ingest 로직은 절대 여기서 구현하지 않는다
    """

    print(f"[BATCH] scanning existing contents: {root_dir}")

    handler = IngestHandler()
    root = Path(root_dir)

    if not root.exists():
        print(f"[BATCH] directory not found: {root_dir}")
        return

    # 1️⃣ 최상위 폴더 먼저 처리
    for entry in sorted(root.iterdir()):
        if entry.is_dir():
            print(f"[BATCH] found directory: {entry}")
            handler._handle_directory(str(entry))

    # 2️⃣ incoming 루트에 바로 있는 파일 처리
    for entry in sorted(root.iterdir()):
        if entry.is_file() and entry.suffix.lower() in SUPPORTED_EXT:
            print(f"[BATCH] found file: {entry}")
            handler._handle_file(str(entry))

    print("[BATCH] initial scan completed")
