from config.db import engine, SessionLocal, Base
from services.ingest import ingest_file

def init_db():
    Base.metadata.create_all(bind=engine)

def main():
    init_db()

    db = SessionLocal()
    try:
        doc_id = ingest_file(
            file_path="C:\\Users\\nee56\\Downloads\\소비 환경 변화에 따른 소호 업종 점검 및 분석.txt",   # sample.pdf 도 가능
            source="manual_upload",
            db=db
        )
        print(f"✅ 저장 완료 (doc_id={doc_id})")
    finally:
        db.close()

if __name__ == "__main__":
    main()
