from backend.db.schemas.user import UserCreate
from backend.db.models.user import User
from backend.db.repository.user import UserRepository

class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def create_user(self, data: UserCreate) -> User:
        user = User(email=data.email, password_hash=data.password_hash)
        return self.user_repo.create(user)

    def get_user_by_email(self, email: str) -> User | None:
        return self.user_repo.get_by_email(email)
