from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from config.db import Base


class MetaTable(Base):
    __tablename__ = "meta_table"

    seq_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255))
    file_type = Column(String(20))
    sorce = Column(String(50))
    file_hash = Column(String(40), unique=True)
    create_dt = Column(DateTime, default=datetime.now)  # ✅ 콤마 없음
