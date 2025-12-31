import os
from config.db import SessionLocal
from services.ingest import ingest_file

SUPPORTED_EXT = {
    ".pdf", ".txt", ".csv", ".docx",
    ".xlsx", ".xls",
    ".jpg", ".jpeg", ".png"
}

def batch_ingest_folder(folder_path: str):
    """
    폴더 내 기존 파일 전체 ingest
    """
    print(f"[BATCH] scanning folder: {folder_path}")

    files = sorted(
        f for f in os.listdir(folder_path)
        if os.path.splitext(f)[1].lower() in SUPPORTED_EXT
    )

    for filename in files:
        file_path = os.path.join(folder_path, filename)

        db = SessionLocal()
        try:
            ingest_file(
                file_path=file_path,
                source="batch",
                db=db
            )
            print(f"[BATCH OK] {filename}")
        except Exception as e:
            print(f"[BATCH FAIL] {filename} -> {e}")
        finally:
            db.close()
