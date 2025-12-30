from .base import BaseLoader

class TXTLoader(BaseLoader):
    file_type = "txt"

    def load(self, file_path: str):
        """
        TXT를 '문단 단위'로 yield
        - 빈 줄 기준
        - 마지막 문단 보장
        """
        buffer = []
        unit_no = 1

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()

                if line:
                    buffer.append(line)
                else:
                    if buffer:
                        yield unit_no, " ".join(buffer)
                        buffer = []
                        unit_no += 1

            # 🔥 파일 끝났는데 buffer 남아있으면 반드시 yield
            if buffer:
                yield unit_no, " ".join(buffer)
