from abc import ABC
from typing import Any, List

class Exchange(ABC):
    name = None  # 또는 기본값을 문자열로 지정할 수 있습니다.
    server_url = None  # 또는 기본값을 문자열로 지정할 수 있습니다.

    @classmethod
    async def get_tickers(cls) -> List[Any]:
        """
        거래소 API로 티커 목록을 가져옵니다.

        Returns:
            list[dict]: 티커 목록 (각 티커의 정보가 포함된 딕셔너리 리스트)
        """
        return []
    
    async def get_orders(self, *args, **kwargs):
        return {}
    
    async def get_order(self, order_id: str) -> dict:
        return {}
    
    async def get_available_balance(self) -> float:
        return 0.0
    
    async def order(self, ticker: str, side: str, seed: float) -> dict:
        return {}
    
class KoreanExchange(Exchange):
    pass
class ForeignExchange(Exchange):
    async def get_position_info(self, ticker: str) -> dict:
        return {}

    async def get_lot_size(self, ticker: str) -> float | None:
        return None

    async def set_leverage(self, *args, **kwargs) -> dict:
        """
        레버리지 설정 결과를 반환합니다. 실제 구현에서는 거래소 API 결과를 result에 담아 반환하세요.
        """
        return { 'result': None }

    async def close_position(self, ticker: str) -> dict:
        """
        포지션을 청산합니다.
        """
        return {}