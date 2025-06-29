from backend.db.repository.ticker import TickerRepository
from sqlalchemy.orm import Session

class TickerService:
    def __init__(self, ticker_repo: TickerRepository):
        self.ticker_repo = ticker_repo

    def get_manual_picked_tickers(self, user_id: int):
        return self.ticker_repo.get_manual_picked_tickers(user_id)

    def get_common_tickers(self, user_id: int):
        return self.ticker_repo.get_common_tickers(user_id, 'upbit', 'bybit')

    def exclude_ticker(self, user_id: int, ticker_name: str) -> bool:
        return self.ticker_repo.exclude_ticker(user_id, ticker_name)

