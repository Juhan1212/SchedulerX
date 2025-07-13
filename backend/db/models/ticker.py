from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.orm import relationship
from backend.db.base import Base

class Ticker(Base):
    __tablename__ = "tickers"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    exchange = Column(String, nullable=False)
    name = Column(String, nullable=False)
    dw_pos_yn = Column(Integer, default=0)
    created_at = Column(TIMESTAMP)
    user_tickers = relationship("UserTicker", back_populates="ticker", cascade="all, delete-orphan")
