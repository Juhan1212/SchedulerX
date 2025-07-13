from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from backend.db.base import Base
from .exchange import Exchange # 임포트하지 않으면 관계 인식 안됨
from .user_ticker import UserTicker # 임포트하지 않으면 관계 인식 안됨

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    exchanges = relationship("Exchange", back_populates="user", cascade="all, delete-orphan")
    user_tickers = relationship("UserTicker", back_populates="user", cascade="all, delete-orphan")