from sqlalchemy import Column, Integer, ForeignKey
from backend.db.base import Base

class Seed(Base):
    __tablename__ = "seed"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    amt = Column(Integer, default=0)
