import csv
from .base import BaseLoader

class CSVLoader(BaseLoader):
    file_type = "csv"

    def load(self, file_path: str):
        unit_no = 1

        # 인코딩 자동 대응
        for encoding in ("utf-8", "cp949"):
            try:
                f = open(file_path, newline="", encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            f = open(file_path, newline="", encoding="utf-8", errors="ignore")

        with f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []

            for row in reader:
                values = [
                    f"{h}: {row[h]}"
                    for h in headers
                    if row.get(h)
                ]
                if not values:
                    continue

                text = " | ".join(values)
                yield unit_no, text
                unit_no += 1
