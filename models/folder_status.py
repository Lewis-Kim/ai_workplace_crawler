from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from config.db import Base


class FolderStatus(Base):
    __tablename__ = "folder_status"

    id = Column(Integer, primary_key=True, autoincrement=True)

    folder_key = Column(String(500), nullable=False, unique=True)  # incoming 기준 상대경로
    folder_name = Column(String(255), nullable=False)              # 마지막 폴더명
    source = Column(String(50), default="watcher")

    status = Column(String(20), default="NEW")  # NEW / INGESTING / DONE / ERROR

    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    error_files = Column(Integer, default=0)

    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
