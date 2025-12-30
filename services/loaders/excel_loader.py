import pandas as pd
from .base import BaseLoader

class ExcelLoader(BaseLoader):
    file_type = "excel"

    def load(self, file_path: str):
        """
        Excel → (sheet_row_no, text)
        sheet_row_no = sheet_index * 100000 + row_index
        """
        xls = pd.ExcelFile(file_path)
        unit_no = 1

        for sheet_idx, sheet_name in enumerate(xls.sheet_names, start=1):
            df = xls.parse(sheet_name)

            # 컬럼명 문자열화
            columns = [str(c) for c in df.columns]

            for row_idx, row in df.iterrows():
                values = [
                    f"{col}: {row[col]}"
                    for col in columns
                    if pd.notna(row[col])
                ]

                if not values:
                    continue

                text = f"[Sheet:{sheet_name}] " + " | ".join(values)

                yield unit_no, text
                unit_no += 1
