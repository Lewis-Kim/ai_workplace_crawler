def chunk_text(
    text: str,
    size: int = 500,
    overlap: int = 100,
    max_chunks: int = 200
):
    """
    안전한 청크 분할
    - 무한 루프 방지
    - 대용량 텍스트 보호
    """
    if not text:
        return []

    n = len(text)

    # 짧은 텍스트는 그대로 하나로
    if n <= size:
        return [text.strip()]

    # 방어 로직
    overlap = min(overlap, size // 2)

    chunks = []
    start = 0
    step = size - overlap
    count = 0

    while start < n:
        end = min(start + size, n)
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)
            count += 1

        if count >= max_chunks:
            break  # 🔥 무한 방지

        start += step  # ✅ 반드시 증가

    return chunks
