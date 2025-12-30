from docx import Document
from .base import BaseLoader

class DOCXLoader(BaseLoader):
    file_type = "docx"

    def load(self, file_path: str):
        doc = Document(file_path)
        unit_no = 1

        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                yield unit_no, text
                unit_no += 1
