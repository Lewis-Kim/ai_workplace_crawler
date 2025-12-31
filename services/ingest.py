import os
from datetime import datetime
from sqlalchemy.orm import Session

from models.meta import MetaTable
from models.content import ContentTable

from services.loaders.pdf_loader import PDFLoader
from services.loaders.txt_loader import TXTLoader
from services.chunking import chunk_text  # ✅ 추가
from services.loaders.excel_loader import ExcelLoader  # 🔥 추가
from services.loaders.csv_loader import CSVLoader
from services.loaders.docx_loader import DOCXLoader
from services.loaders.image_ocr_loader import ImageOCRLoader
from services.utils import file_sha1

LOADER_MAP = {
    "pdf": PDFLoader(),
    "txt": TXTLoader(),
    "xlsx": ExcelLoader(),
    "xls": ExcelLoader(),
    "csv": CSVLoader(),
    "docx": DOCXLoader(),
    "jpg": ImageOCRLoader(),
    "jpeg": ImageOCRLoader(),
    "png": ImageOCRLoader(),
}

def ingest_file(file_path: str, source: str, db: Session):
    
    ext = os.path.splitext(file_path)[1].lower().lstrip(".")

    if ext not in LOADER_MAP:
        raise ValueError(f"지원하지 않는 파일 타입: {ext}")
    
    # 0️⃣ 파일 해시 계산
    file_hash = file_sha1(file_path)

    # 1️⃣ 이미 처리된 파일인지 확인
    exists = db.query(MetaTable).filter(
        MetaTable.file_hash == file_hash
    ).first()

    if exists:
        print(f"[SKIP] duplicate file: {file_path}")
        return exists.seq_id

    loader = LOADER_MAP[ext]

    # 1️⃣ meta 저장
    meta = MetaTable(
        title=os.path.basename(file_path),
        file_type=ext,
        sorce=source,
        create_dt=datetime.now(),
        file_hash=file_hash
    )
    db.add(meta)
    db.commit()
    db.refresh(meta)

    # 🔍 디버그용 카운터
    unit_count = 0
    chunk_count = 0

    # 2️⃣ content 저장
    for unit_no, text in loader.load(file_path):
        unit_count += 1
        #print(f"[DEBUG] unit_no={unit_no}, len(text)={len(text)}")

        chunks = chunk_text(text)

        for idx, chunk in enumerate(chunks, start=1):
            chunk_count += 1
            #print(f"[DEBUG] doc_id={meta.seq_id},page_no={unit_no},chunk_no={idx},chunk={chunk}")
            db.add(ContentTable(
                doc_id=meta.seq_id,
                page_no=unit_no,
                chunk_no=idx,
                content=chunk
            ))

    db.commit()

    #print(f"[DEBUG] units={unit_count}, chunks={chunk_count}")

    return meta.seq_id

