# services/utils/file_ops.py

import os
import time
import shutil
import logging

logger = logging.getLogger("file_ops")
logger.setLevel(logging.INFO)


def wait_for_file_stable(
    file_path: str,
    wait_sec: float = 1.0,
    max_retry: int = 10,
) -> bool:
    """
    파일 크기가 더 이상 변하지 않을 때까지 대기
    (Windows WinError 32 방지 핵심)
    """
    last_size = -1

    for i in range(max_retry):
        try:
            current_size = os.path.getsize(file_path)
        except FileNotFoundError:
            time.sleep(wait_sec)
            continue

        if current_size == last_size:
            logger.debug(f"[STABLE] file stabilized: {file_path}")
            return True

        last_size = current_size
        time.sleep(wait_sec)

    logger.warning(f"[STABLE FAIL] file not stabilized: {file_path}")
    return False


def move_file(
    src: str,
    dest_dir: str,
    retry: int = 5,
    wait_sec: float = 1.0,
):
    """
    Windows 안전 move (WinError 32 대응)
    """
    if not os.path.exists(src):
        logger.warning(f"[MOVE SKIP] source not found: {src}")
        return

    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(src))

    # 1️⃣ 파일 안정화 대기
    if not wait_for_file_stable(src):
        raise RuntimeError(f"File not stabilized: {src}")

    # 2️⃣ move 재시도
    for i in range(retry):
        try:
            shutil.move(src, dest)
            logger.info(f"[MOVE OK] {src} -> {dest}")
            return
        except PermissionError as e:
            logger.warning(
                f"[MOVE RETRY {i+1}/{retry}] {src} | {e}"
            )
            time.sleep(wait_sec)

    raise PermissionError(f"Failed to move file after retries: {src}")
