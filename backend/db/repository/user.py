from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List
from sqlalchemy.orm import Session
from backend.db.models.user import User

T = TypeVar("T")  # 모델 타입

class AbstractUserRepository(ABC, Generic[T]):
    @abstractmethod
    def get_by_id(self, id: int) -> T:
        pass

    @abstractmethod
    def get_all(self) -> List[T]:
        pass

    @abstractmethod
    def create(self, user: T) -> T:
        pass

class UserRepository(AbstractUserRepository[User]):
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, id: int) -> User:
        return self.db.query(User).filter(User.id == id).first()

    def get_all(self) -> list[User]:
        return self.db.query(User).all()

    def get_by_email(self, email: str) -> User:
        return self.db.query(User).filter(User.email == email).first()

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user