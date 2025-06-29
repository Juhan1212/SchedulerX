from sqlalchemy import Column, Integer, ForeignKey, String
from backend.db.base import Base

class UserTicker(Base):
    __tablename__ = "user_ticker"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticker_name = Column(String, unique=True, index=True)
    manual_del_yn = Column(Integer, default=0)
    manual_pick_yn = Column(Integer, default=0)
    # ...existing code...
