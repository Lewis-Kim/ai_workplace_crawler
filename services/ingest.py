import os
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from models.meta import MetaTable
from models.content import ContentTable
from models.ImageTable import ImageTable

from services.loaders.pdf_loader import PDFLoader
from services.loaders.txt_loader import TXTLoader
from services.loaders.excel_loader import ExcelLoader
from services.loaders.csv_loader import CSVLoader
from services.loaders.docx_loader import DOCXLoader
from services.loaders.image_ocr_loader import ImageOCRLoader

from services.chunking import chunk_text
from services.utils.file_hash import file_sha1
from services.images.image_extractor import extract_images

from qdrant_client import QdrantClient
from vector.collection_manager import ensure_collection
from vector.realtime_vector import insert_vector


# =================================================
# 🔧 Qdrant / Embedding 설정 (🔥 핵심)
# =================================================
QDRANT_HOST = "192.168.50.32"
QDRANT_PORT = 6333

BASE_COLLECTION = "documents"
MODEL_KEY = "nomic"   # ⭐ 모델 변경은 여기만

qdrant_client = QdrantClient(
    host=QDRANT_HOST,
    port=QDRANT_PORT,
    timeout=30
)

# 🚀 앱 시작 시 1회만 실행
COLLECTION_NAME = ensure_collection(
    client=qdrant_client,
    base_collection=BASE_COLLECTION,
    model_key=MODEL_KEY
)


# =================================================
# logging 설정
# =================================================
logger = logging.getLogger("ingest")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


# =================================================
# loader map
# =================================================
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


# =================================================
# ingest main
# =================================================
def ingest_file(file_path: str, source: str, db: Session):

    logger.info(f"[START] ingest_file | file={file_path}")

    # -------------------------------------------------
    # 1️⃣ 파일 타입 확인
    # -------------------------------------------------
    ext = os.path.splitext(file_path)[1].lower().lstrip(".")

    if ext not in LOADER_MAP:
        logger.error(f"[STOP] unsupported file type: {ext}")
        raise ValueError(f"지원하지 않는 파일 타입: {ext}")

    logger.info(f"[STEP 1] file type detected: {ext}")

    # -------------------------------------------------
    # 2️⃣ 파일 해시 계산
    # -------------------------------------------------
    file_hash = file_sha1(file_path)
    logger.info(f"[STEP 2] file hash calculated: {file_hash}")

    # -------------------------------------------------
    # 3️⃣ 중복 파일 체크
    # -------------------------------------------------
    exists = db.query(MetaTable).filter(
        MetaTable.file_hash == file_hash
    ).first()

    if exists:
        logger.warning(
            f"[SKIP] duplicate file | file={file_path}, doc_id={exists.seq_id}"
        )
        return exists.seq_id

    # -------------------------------------------------
    # 4️⃣ meta_table INSERT
    # -------------------------------------------------
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

    logger.info(f"[STEP 3] meta inserted | doc_id={meta.seq_id}")

    # -------------------------------------------------
    # 5️⃣ 이미지 추출 + images INSERT
    # -------------------------------------------------
    image_root = "images"    
    image_dir = f"{image_root}/{meta.seq_id}"

    logger.info(f"[STEP 4] image extraction start")

    images = extract_images(
        file_path=file_path,
        output_dir=image_dir   # ✅ 반드시 doc_id 경로
    )

    for idx, img in enumerate(images, start=1):
        image_name = img["image"]
        image_ext = os.path.splitext(image_name)[1].lstrip(".")

        db.add(ImageTable(
            doc_id=meta.seq_id,
            page_no=img.get("page"),
            image_no=idx,
            image_path=f"{image_dir}/{image_name}",
            image_name=image_name,
            image_ext=image_ext
        ))

    db.commit()

    logger.info(
        f"[STEP 4 DONE] images inserted | count={len(images)}"
    )

    # -------------------------------------------------
    # 6️⃣ 텍스트 로드 → chunk → DB + 🔥 Vector Insert
    # -------------------------------------------------
    loader = LOADER_MAP[ext]

    unit_count = 0
    chunk_count = 0

    logger.info("[STEP 5] text loading & chunking start")

    for unit_no, text in loader.load(file_path):
        unit_count += 1

        chunks = chunk_text(text)

        for idx, chunk in enumerate(chunks, start=1):
            chunk_count += 1

            content = ContentTable(
                doc_id=meta.seq_id,
                page_no=unit_no,
                chunk_no=idx,
                content=chunk
            )
            db.add(content)
            db.commit()
            db.refresh(content)

            # 🔥 Qdrant Vector Insert (컬렉션/모델 명시)
            try:
                insert_vector(
                    collection_name=COLLECTION_NAME,
                    model_key=MODEL_KEY,
                    content_id=content.content_id,
                    doc_id=meta.seq_id,
                    page_no=unit_no,
                    chunk_no=idx,
                    text=chunk[:1500],  # 🔒 안전 길이 제한
                )
            except Exception as ve:
                logger.error(
                    f"[VECTOR FAIL] content_id={content.content_id} | {ve}"
                )

    logger.info(
        f"[STEP 5 DONE] text stored | units={unit_count}, chunks={chunk_count}"
    )

    # -------------------------------------------------
    # 7️⃣ 완료
    # -------------------------------------------------
    logger.info(
        f"[END] ingest completed | doc_id={meta.seq_id}, "
        f"images={len(images)}, chunks={chunk_count}"
    )

    return meta.seq_id
