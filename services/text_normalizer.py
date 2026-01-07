# services/text_normalizer.py

import re
import unicodedata


def normalize_for_embedding(text: str) -> str:
    if not text:
        return ""

    # 1️⃣ Unicode 정규화 (한글/호환문자 안정화)
    text = unicodedata.normalize("NFKC", text)

    # 2️⃣ 줄바꿈/탭 → 공백
    text = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")

    # 3️⃣ 제어문자 제거
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)

    # 4️⃣ Zero-width 문자 제거
    text = re.sub(r"[\u200b\u200c\u200d\uFEFF]", "", text)

    # 5️⃣ 구분선/반복 특수문자 제거
    text = re.sub(r"[-_=]{3,}", " ", text)

    # 6️⃣ 공백 압축
    text = re.sub(r"\s+", " ", text)

    return text.strip()
