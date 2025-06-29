from fastapi import Depends
from backend.db.base import SessionLocal
from backend.db.repository.user import UserRepository
from backend.services.user import UserService

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_repository(db=Depends(get_db)):
    return UserRepository(db)

def get_user_service(repo=Depends(get_user_repository)):
    return UserService(repo)
