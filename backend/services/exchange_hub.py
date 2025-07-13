from decimal import Decimal
import logging
import asyncio
from backend.db.repository.exchange import ExchangeRepository
from backend.exchanges.bybit import BybitExchange
from backend.exchanges.gateio import GateioExchange
from backend.exchanges.upbit import UpbitExchange

logger = logging.getLogger(__name__)

EXCHANGE_CLASS_MAP = {
    "bybit": BybitExchange,
    "upbit": UpbitExchange,
    "gateio": GateioExchange
    # 확장 시 여기에 추가
}

class ExchangeHub:
    def __init__(self, user_id: int, exchange_repository: ExchangeRepository):
        self.user_id = user_id
        self.exchange_repository = exchange_repository
        self.exchange_objs = self._load_user_exchanges()

    def _load_user_exchanges(self):
        exchanges = self.exchange_repository.get_all_registered_exchanges(self.user_id)
        exchange_objs = []
        for ex in exchanges:
            ex_class = EXCHANGE_CLASS_MAP.get(ex.name.lower())
            if ex_class:
                # 각 거래소 클래스의 생성자에 맞게 인스턴스 생성
                exchange_objs.append(ex_class(api_key=ex.api_key, secret_key=ex.secret_key))
        return exchange_objs

    async def call_method_on_all(self, method_name: str, exchanges: list, *args, **kwargs):
        """
        등록된 거래소 객체 리스트(exchanges)가 주어지면 해당 리스트 기준으로,
        아니면 self.exchange_objs 기준으로 method_name에 해당하는 async 메서드를 병렬로 호출
        """
        logger.info(f"Calling method {method_name} on exchanges: {exchanges}")
        logger.info(f"args: {args}, kwargs: {kwargs}")
        
        targets = exchanges if exchanges else self.exchange_objs
        tasks = []
        results = {}
        for ex_obj in targets:
            ex_class = EXCHANGE_CLASS_MAP.get(ex_obj.lower())
            method = getattr(ex_class, method_name, None)
            if callable(method):
                tasks.append((ex_obj, method(*args, **kwargs)))
        if not tasks:
            return results
        names, coros = zip(*tasks)
        gathered = await asyncio.gather(*coros, return_exceptions=True)
        for name, result in zip(names, gathered):
            results[name] = result
        return results

    def get_exchange_obj(self, name: str):
        for ex_obj in self.exchange_objs:
            if ex_obj.name.lower() == name.lower():
                return ex_obj
        return None

    def merge_kline_data(self, kline_data1, kline_data2):
        # timestamp 기준으로 dict로 변환
        dict1 = {item["timestamp"]: item for item in kline_data1}
        dict2 = {item["timestamp"]: item for item in kline_data2}
        merged = []

        for ts in dict1:
            if ts in dict2:
                u = dict1[ts]
                g = dict2[ts]
                merged.append({
                    "timestamp": ts,
                    "open": round((u["open"] / g["open"]), 2),
                    "high": round((u["high"] / g["high"]), 2),
                    "low": round((u["low"] / g["low"]), 2),
                    "close": round((u["close"] / g["close"]), 2),
                    "volume": Decimal(str(u["volume"])) + Decimal(str(g["volume"]))
                })
        return merged

# 사용 예시:
# hub = ExchangeHub(user_id, exchange_repository)
# tickers = await hub.call_method_on_all('get_tickers')
# bybit_obj = hub.get_exchange_obj('bybit')
# candles = await bybit_obj.get_ticker_candles('BTC', interval='1')
