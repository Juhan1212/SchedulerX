from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship
from backend.db.base import Base

class UserTicker(Base):
    __tablename__ = "user_ticker"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticker_id = Column(Integer, ForeignKey("tickers.id"), nullable=False)
    ticker_name = Column(String, index=True)
    manual_del_yn = Column(Integer, default=0)
    manual_pick_yn = Column(Integer, default=0)
    user = relationship("User", back_populates="user_tickers")
    ticker = relationship("Ticker", back_populates="user_tickers")
