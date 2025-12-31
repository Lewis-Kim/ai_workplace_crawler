from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from config.db import Base


class ImageTable(Base):
    __tablename__ = "images"

    seq_id = Column(Integer, primary_key=True, autoincrement=True)

    # FK → meta_table.seq_id
    doc_id = Column(Integer, ForeignKey("meta_table.seq_id"), nullable=False)

    page_no = Column(Integer, nullable=True)
    image_no = Column(Integer, nullable=True)

    image_path = Column(String(512), nullable=False)
    image_name = Column(String(255), nullable=False)
    image_ext = Column(String(10), nullable=False)

    ocr_text = Column(String, nullable=True)
    caption = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
