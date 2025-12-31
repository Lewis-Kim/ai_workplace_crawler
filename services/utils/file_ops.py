import os
import shutil

def move_file(src: str, dest_dir: str):
    os.makedirs(dest_dir, exist_ok=True)

    filename = os.path.basename(src)
    dest = os.path.join(dest_dir, filename)

    # 파일명 충돌 방지
    if os.path.exists(dest):
        base, ext = os.path.splitext(filename)
        i = 1
        while True:
            new_name = f"{base}_{i}{ext}"
            dest = os.path.join(dest_dir, new_name)
            if not os.path.exists(dest):
                break
            i += 1

    shutil.move(src, dest)
    return dest
