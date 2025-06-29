import logging
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from backend.db.models.ticker import Ticker
from backend.db.models.user_ticker import UserTicker

# Configure logging
logger = logging.getLogger(__name__)

class TickerRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_manual_picked_tickers(self, user_id: int):
        return (
            self.db.query(Ticker)
            .join(UserTicker, Ticker.id == UserTicker.ticker_id)
            .filter(UserTicker.user_id == user_id, UserTicker.manual_pick_yn == 1)
            .all()
        )

    def get_common_tickers(self, user_id: int, *exchanges):
        if not exchanges:
            return []
        
        # UserTicker에 등록된 제외대상 ticker_name 목록
        exclude_tgt = (
            select(UserTicker.ticker_name)
            .filter(UserTicker.user_id == user_id, UserTicker.manual_del_yn == 1)
        )
        
        # 거래소 공통 ticker_name 추출
        common_names_subq = (
            select(Ticker.name)
            .where(Ticker.exchange.in_(exchanges))
            .group_by(Ticker.name)
            .having(func.count_(func.distinct(Ticker.exchange)) == len(exchanges))
        )

        query = (
            self.db.query(Ticker.name)
            .filter(
                Ticker.exchange.in_(exchanges),
                Ticker.name.in_(common_names_subq),
                ~Ticker.name.in_(exclude_tgt)
            )
            .distinct()
        )
        return query.all()

    def exclude_ticker(self, user_id: int, ticker_name: str) -> bool:
        # UserTicker에 manual_del_yn=1로 등록(없으면 생성, 있으면 update)
        ticker = self.db.query(Ticker).filter(Ticker.name == ticker_name).first()
        if not ticker:
            return False

        user_ticker = (
            self.db.query(UserTicker)
            .filter(UserTicker.user_id == user_id, UserTicker.ticker_name == ticker.name)
            .first()
        )
        if user_ticker:
            setattr(user_ticker, "manual_del_yn", 1)
        else:
            user_ticker = UserTicker(
                user_id=user_id,
                ticker_name=ticker_name,
                manual_del_yn=1
            )
            self.db.add(user_ticker)
        self.db.commit()
        return True
