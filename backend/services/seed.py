from sqlalchemy.orm import Session
from backend.db.repository.seed import SeedRepository

class SeedService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SeedRepository(db)

    def get_seed(self, user_id: int):
        return self.repo.get_seed_by_user_id(user_id)

    def update_seed(self, user_id: int, amt: int):
        return self.repo.upsert_seed(user_id, amt)
