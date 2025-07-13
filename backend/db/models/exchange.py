from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, text
from sqlalchemy.orm import relationship
from backend.db.base import Base

class Exchange(Base):
    __tablename__ = "exchanges"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    uid = Column(String, nullable=True)
    api_key = Column(String, nullable=True)
    secret_key = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), onupdate=text("now()"))
    user = relationship("User", back_populates="exchanges")
