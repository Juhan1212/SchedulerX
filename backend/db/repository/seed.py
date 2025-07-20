
from sqlalchemy.orm import Session
from backend.db.models.seed import Seed

class SeedRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_seed_by_user_id(self, user_id: int):
        return self.db.query(Seed).filter(Seed.user_id == user_id).first()

    def upsert_seed(self, user_id: int, amt: int):
        seed = self.db.query(Seed).filter(Seed.user_id == user_id).first()
        if seed:
            seed.amt = amt  # type: ignore
        else:
            seed = Seed(user_id=user_id, amt=amt)
            self.db.add(seed)
        self.db.commit()
        self.db.refresh(seed)
        return seed
