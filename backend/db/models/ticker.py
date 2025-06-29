from sqlalchemy import Column, Integer, String, TIMESTAMP
from backend.db.base import Base

class Ticker(Base):
    __tablename__ = "tickers"
    id = Column(Integer, primary_key=True, index=True)
    exchange = Column(String, nullable=False)
    name = Column(String, nullable=False)
    dw_pos_yn = Column(Integer, default=0)
    created_at = Column(TIMESTAMP)
