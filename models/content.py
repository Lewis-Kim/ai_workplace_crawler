from sqlalchemy import (
    Column, Integer, Text, DateTime, ForeignKey
)
from datetime import datetime
from config.db import Base

class ContentTable(Base):
    __tablename__ = "content_table"

    content_id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(
        Integer,
        ForeignKey("meta_table.seq_id", ondelete="CASCADE"),
        nullable=False
    )
    page_no = Column(Integer, comment="페이지 번호")
    chunk_no = Column(Integer, comment="청크 번호")
    content = Column(Text, comment="텍스트 내용")
    created_at = Column(DateTime, default=datetime.now)
