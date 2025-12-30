from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from config.db import Base

class MetaTable(Base):
    __tablename__ = "meta_table"

    seq_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), comment="제목")
    file_type = Column(String(45), comment="파일타입")
    sorce = Column(String(45), comment="출처")
    create_dt = Column(DateTime, default=datetime.now, comment="등록일자")
