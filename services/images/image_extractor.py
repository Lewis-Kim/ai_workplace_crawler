import os
import zipfile
import shutil
from pathlib import Path
from typing import List, Dict

import fitz  # pymupdf

ZIP_MEDIA_PATHS = {
    ".docx": "word/media/",
    ".pptx": "ppt/media/",
    ".xlsx": "xl/media/",
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


# -------------------------------------------------
# PDF
# -------------------------------------------------
def extract_images_from_pdf(file_path: Path, out_dir: Path) -> List[Dict]:
    meta = []
    doc = fitz.open(file_path)

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        for img_idx, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base = doc.extract_image(xref)

            fpath = out_dir / fname

            with open(fpath, "wb") as f:
                f.write(base["image"])

            meta.append({
                "page": page_idx + 1,
                "image": fname
            })

    return meta


# -------------------------------------------------
# DOCX / PPTX / XLSX
# -------------------------------------------------
def extract_images_from_zip(file_path: Path, out_dir: Path) -> List[Dict]:
    meta = []
    prefix = ZIP_MEDIA_PATHS.get(file_path.suffix.lower())
    if not prefix:
        return meta

    with zipfile.ZipFile(file_path) as z:
        for name in z.namelist():
            if name.startswith(prefix):
                fname = os.path.basename(name)
                if not fname:
                    continue

                with open(out_dir / fname, "wb") as f:
                    f.write(z.read(name))

                meta.append({"image": fname})

    return meta


# -------------------------------------------------
# Image file
# -------------------------------------------------
def extract_single_image(file_path: Path, out_dir: Path) -> List[Dict]:
    fname = file_path.name
    shutil.copy(file_path, out_dir / fname)
    return [{"image": fname}]


# -------------------------------------------------
# Dispatcher (🔥 핵심 수정)
# -------------------------------------------------
def extract_images(file_path: str, output_dir: str) -> List[Dict]:
    """
    output_dir = images/{meta.seq_id}
    """
    file_path = Path(file_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ext = file_path.suffix.lower()

    if ext == ".pdf":
        return extract_images_from_pdf(file_path, out_dir)

    if ext in ZIP_MEDIA_PATHS:
        return extract_images_from_zip(file_path, out_dir)

    if ext in IMAGE_EXTS:
        return extract_single_image(file_path, out_dir)

    return []
