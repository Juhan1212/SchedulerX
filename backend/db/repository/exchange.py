import logging
from sqlalchemy.orm import Session
from backend.db.models.exchange import Exchange
from backend.db.schemas.exchange import RegisterExchange

logger = logging.getLogger(__name__)

class ExchangeRepository:
    def __init__(self, db: Session):
        self.db = db

    def register_exchange(self, register_exchange: RegisterExchange):
        """
        register_exchange: RegisterExchange 스키마 (uid, api_key, secret_key)
        """
        exchange = Exchange(
            user_id=register_exchange.user_id,
            uid=register_exchange.uid,
            api_key=register_exchange.api_key,
            secret_key=register_exchange.secret_key
        )
        self.db.add(exchange)
        self.db.commit()
        self.db.refresh(exchange)
        return exchange

    def get_all_registered_exchanges(self, user_id: int):
        return self.db.query(Exchange).filter(Exchange.user_id == user_id).all()

    def get_one_registered_exchange(self, user_id: int):
        return self.db.query(Exchange).filter(Exchange.user_id == user_id).first()
