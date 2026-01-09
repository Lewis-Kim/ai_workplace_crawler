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
from services.text_normalizer import normalize_for_embedding

from vector.collection_manager import ensure_collection
from vector.realtime_vector import insert_vector, get_qdrant_client


# =================================================
# 🔧 Qdrant / Collection (Lazy Init + Safe)
# =================================================
_COLLECTION_NAME: str | None = None
BASE_COLLECTION: str = os.getenv("BASE_COLLECTION", "document")


def get_collection_name(
    *,
    base_collection: str,
    model_key: str,
) -> str:
    """
    Qdrant collection name을 안전하게 1회 생성/검증 후 재사용
    """
    global _COLLECTION_NAME

    if _COLLECTION_NAME is None:
        client = get_qdrant_client()
        _COLLECTION_NAME = ensure_collection(
            client=client,
            base_collection=base_collection,
            model_key=model_key,
        )
        logger.info(f"[INGEST] collection resolved: {_COLLECTION_NAME}")

    return _COLLECTION_NAME


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
def ingest_file(
    file_path: str,
    source: str,
    db: Session,
    folder_name: str | None = None,
    *,
    base_collection: str = BASE_COLLECTION,
    model_key: str | None = None,
) -> int:
    """
    단일 파일 ingest
    (meta → content → vector)
    """

    logger.info(f"[START] ingest_file | file={file_path}")

    # -------------------------------------------------
    # 0️⃣ model_key 확보
    # -------------------------------------------------
    if model_key is None:
        model_key = os.getenv("MODEL_KEY")

    if not model_key:
        raise RuntimeError("MODEL_KEY is not set (env or argument)")

    # -------------------------------------------------
    # 1️⃣ 파일 타입
    # -------------------------------------------------
    ext = os.path.splitext(file_path)[1].lower().lstrip(".")

    if ext not in LOADER_MAP:
        raise ValueError(f"지원하지 않는 파일 타입: {ext}")

    # -------------------------------------------------
    # 2️⃣ 해시
    # -------------------------------------------------
    file_hash = file_sha1(file_path)

    # -------------------------------------------------
    # 3️⃣ 중복 체크
    # -------------------------------------------------
    exists = db.query(MetaTable).filter(
        MetaTable.file_hash == file_hash
    ).first()

    if exists:
        logger.warning(
            f"[SKIP] duplicate | file={file_path}, doc_id={exists.seq_id}"
        )
        return exists.seq_id

    # -------------------------------------------------
    # 4️⃣ meta insert
    # -------------------------------------------------
    meta = MetaTable(
        title=os.path.basename(file_path),
        file_type=ext,
        source=source,
        file_hash=file_hash,
        file_path=file_path,
        folder_name=folder_name,
        create_dt=datetime.now(),
    )

    db.add(meta)
    db.commit()
    db.refresh(meta)

    logger.info(f"[META] inserted | doc_id={meta.seq_id}")

    # -------------------------------------------------
    # 5️⃣ 이미지 추출
    # -------------------------------------------------
    image_root = "images"
    image_dir = f"{image_root}/{meta.seq_id}"

    images = extract_images(
        file_path=file_path,
        output_dir=image_dir,
    )

    for idx, img in enumerate(images, start=1):
        image_name = img["image"]
        image_ext = os.path.splitext(image_name)[1].lstrip(".")

        db.add(
            ImageTable(
                doc_id=meta.seq_id,
                page_no=img.get("page"),
                image_no=idx,
                image_path=f"{image_dir}/{image_name}",
                image_name=image_name,
                image_ext=image_ext,
            )
        )

    db.commit()

    # -------------------------------------------------
    # 6️⃣ 텍스트 → chunk → DB + Vector
    # -------------------------------------------------
    loader = LOADER_MAP[ext]

    collection_name = get_collection_name(
        base_collection=base_collection,
        model_key=model_key,
    )

    chunk_count = 0

    for unit_no, text in loader.load(file_path):
        for idx, chunk in enumerate(chunk_text(text), start=1):
            clean = normalize_for_embedding(chunk)
            chunk_count += 1

            content = ContentTable(
                doc_id=meta.seq_id,
                page_no=unit_no,
                chunk_no=idx,
                content=clean,
            )
            db.add(content)
            db.flush()   # content_id 확보

            try:
                insert_vector(
                    collection_name=collection_name,
                    model_key=model_key,
                    content_id=content.content_id,
                    doc_id=meta.seq_id,
                    page_no=unit_no,
                    chunk_no=idx,
                    text=clean[:1500],
                    folder_name=folder_name,
                    title=meta.title,
                    file_type=ext,
                    source=source,
                )
            except Exception as ve:
                logger.error(
                    f"[VECTOR FAIL] content_id={content.content_id} | {ve}"
                )

    db.commit()

    # -------------------------------------------------
    # 7️⃣ 완료
    # -------------------------------------------------
    logger.info(
        f"[END] ingest completed | doc_id={meta.seq_id}, "
        f"images={len(images)}, chunks={chunk_count}"
    )

    return meta.seq_id
