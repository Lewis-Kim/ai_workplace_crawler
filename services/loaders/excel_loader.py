import pandas as pd
from .base import BaseLoader


class ExcelLoader(BaseLoader):
    file_type = "excel"

    def load(self, file_path: str):
        """
        Excel Loader (Streaming-safe)
        - Sheet 단위
        - Row 단위
        - 값 정규화
        """
        xls = pd.ExcelFile(file_path)
        unit_no = 1

        for sheet_name in xls.sheet_names:
            # 🔹 dtype=str → 모든 값 문자열화 (노이즈 최소화)
            df = xls.parse(
                sheet_name,
                dtype=str
            )

            if df.empty:
                continue

            columns = [str(c).strip() for c in df.columns]

            # 🔹 itertuples(): iterrows()보다 훨씬 빠름
            for row in df.itertuples(index=False):
                values = []

                for col, val in zip(columns, row):
                    if val is None:
                        continue

                    val = str(val).strip()
                    if not val or val.lower() in ("nan", "nat"):
                        continue

                    values.append(f"{col}: {val}")

                if not values:
                    continue

                text = f"[Sheet:{sheet_name}] " + " | ".join(values)

                yield unit_no, text
                unit_no += 1
