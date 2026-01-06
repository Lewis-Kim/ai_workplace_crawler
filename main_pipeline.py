import os
import time
from watchdog.observers import Observer

from batch.folder_batch import batch_ingest_folder
from watcher.file_watcher import IngestHandler


# ==========================
# 설정
# ==========================
BASE_DIR = "watch_dir"

INCOMING_DIR = os.path.join(BASE_DIR, "incoming")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
DUPLICATED_DIR = os.path.join(BASE_DIR, "duplicated")
ERROR_DIR = os.path.join(BASE_DIR, "error")


def ensure_directories():
    for d in [
        INCOMING_DIR,
        PROCESSED_DIR,
        DUPLICATED_DIR,
        ERROR_DIR,
    ]:
        os.makedirs(d, exist_ok=True)


def main():
    print("🚀 Ingest Pipeline Starting...")

    # 1️⃣ 디렉터리 준비
    ensure_directories()

    # 2️⃣ 서버 시작 시 기존 데이터 처리
    print("📂 Batch ingest existing files/folders...")
    batch_ingest_folder(INCOMING_DIR)

    # 3️⃣ watcher 시작
    print("👀 Starting file watcher...")
    observer = Observer()
    handler = IngestHandler()

    observer.schedule(
        handler,
        INCOMING_DIR,
        recursive=True      # ✅ 폴더 대응
    )
    observer.start()

    print("✅ Pipeline running")
    print(f"   - watching: {INCOMING_DIR}")
    print("   - press Ctrl+C to stop")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down pipeline...")
        observer.stop()

    observer.join()
    print("✅ Pipeline stopped cleanly")


if __name__ == "__main__":
    main()
