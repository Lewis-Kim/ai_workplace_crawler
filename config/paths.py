import os

BASE_DIR = "watch_dir"

INCOMING_DIR = os.path.join(BASE_DIR, "incoming")
PROCESSING_DIR = os.path.join(BASE_DIR, "processing")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
DUPLICATED_DIR = os.path.join(BASE_DIR, "duplicated")
ERROR_DIR = os.path.join(BASE_DIR, "error")
