import time
from watchdog.observers import Observer
from watcher.file_watcher import IngestHandler

WATCH_DIR = "./watch_dir"  # 감시할 폴더

def main():
    observer = Observer()
    handler = IngestHandler(WATCH_DIR)

    observer.schedule(handler, WATCH_DIR, recursive=False)
    observer.start()

    print(f"👀 Watching directory: {WATCH_DIR}")

    try:
        while True:
            time.sleep(1000)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()

if __name__ == "__main__":
    main()
