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


# ==========================
# 디렉터리 초기화
# ==========================

def ensure_directories():
    for d in [
        INCOMING_DIR,
        PROCESSED_DIR,
        DUPLICATED_DIR,
        ERROR_DIR,
    ]:
        os.makedirs(d, exist_ok=True)


# ==========================
# 메인 파이프라인
# ==========================

def main():
    print("🚀 Ingest Pipeline Starting...")

    # 1️⃣ 디렉터리 준비
    ensure_directories()

    # 2️⃣ 기존 파일 배치 ingest
    print("📂 Batch ingest existing files...")
    batch_ingest_folder(INCOMING_DIR)

    # 3️⃣ 워처 시작
    print("👀 Starting file watcher...")
    observer = Observer()
    handler = IngestHandler()

    observer.schedule(
        handler,
        INCOMING_DIR,
        recursive=False
    )
    observer.start()

    print("✅ Pipeline running")
    print(f"   - watching: {INCOMING_DIR}")
    print("   - press Ctrl+C to stop")

    try:
        while True:
            time.sleep(1000)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down pipeline...")
        observer.stop()

    observer.join()
    print("✅ Pipeline stopped cleanly")


# ==========================
# Entry Point
# ==========================

if __name__ == "__main__":
    main()
