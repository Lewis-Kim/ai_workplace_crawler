import fitz
from .base import BaseLoader

class PDFLoader(BaseLoader):
    file_type = "pdf"

    def load(self, file_path: str):
        doc = fitz.open(file_path)

        for page_no, page in enumerate(doc, start=1):
            text = (
                page.get_text("text")
                .replace("\xa0", " ")
                .strip()
            )
            if text:
                yield page_no, text
