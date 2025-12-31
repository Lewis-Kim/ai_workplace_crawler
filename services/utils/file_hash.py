import hashlib

def file_sha1(path: str) -> str:
    """
    파일 내용을 기반으로 SHA1 해시 생성
    (파일명 변경에도 중복 감지 가능)
    """
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
