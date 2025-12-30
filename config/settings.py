import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()  # .env 로드

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_CHARSET = os.getenv("DB_CHARSET", "utf8mb4")

password = quote_plus(DB_PASSWORD)

def validate_settings():
    missing = [
        k for k, v in {
            "DB_HOST": DB_HOST,
            "DB_NAME": DB_NAME,
            "DB_USER": DB_USER,
            "DB_PASSWORD": password,
        }.items() if not v
    ]
    if missing:
        raise RuntimeError(f"❌ 환경변수 누락: {', '.join(missing)}")
