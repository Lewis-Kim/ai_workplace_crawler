import pytesseract
from PIL import Image
from .base import BaseLoader

class ImageOCRLoader(BaseLoader):
    file_type = "image"

    def load(self, file_path: str):
        image = Image.open(file_path)

        text = pytesseract.image_to_string(
            image,
            lang="kor+eng"
        )

        unit_no = 1
        for line in text.splitlines():
            line = line.strip()
            if line:
                yield unit_no, line
                unit_no += 1
