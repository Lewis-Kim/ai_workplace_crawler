import os
import logging
from datetime import datetime

from batch.folder_batch import batch_ingest_folder
from watcher.file_watcher import IngestHandler
from pipeline import state
from watchdog.observers import Observer   # ✅
from config.paths import INCOMING_DIR, PROCESSED_DIR, DUPLICATED_DIR, ERROR_DIR, PROCESSING_DIR

logger = logging.getLogger("pipeline")





def ensure_directories():
    for d in (
        INCOMING_DIR,
        PROCESSING_DIR,
        PROCESSED_DIR,
        DUPLICATED_DIR,
        ERROR_DIR,
    ):
        os.makedirs(d, exist_ok=True)


def start_pipeline():
    if state.observer:
        logger.warning("Pipeline already running")
        return

    logger.info("🚀 Ingest Pipeline Starting...")

    ensure_directories()

    logger.info("📂 Batch ingest existing files/folders...")
    batch_ingest_folder(INCOMING_DIR)

    logger.info("👀 Starting file watcher...")
    observer = Observer()
    handler = IngestHandler()

    observer.schedule(handler, INCOMING_DIR, recursive=True)
    observer.start()

    state.observer = observer
    state.started_at = datetime.now()

    logger.info("✅ Pipeline running")
    logger.info(f"   - watching: {INCOMING_DIR}")


def stop_pipeline():
    if not state.observer:
        return

    logger.info("🛑 Shutting down pipeline...")
    state.observer.stop()
    state.observer.join()

    state.observer = None
    state.started_at = None

    logger.info("✅ Pipeline stopped cleanly")

def restart_pipeline():
    logger.info("🔁 Restarting pipeline...")
    stop_pipeline()
    start_pipeline()
    logger.info("✅ Pipeline restarted")

