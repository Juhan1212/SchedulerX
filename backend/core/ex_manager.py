import asyncio
from backend.exchanges import *

class ExchangeManager:
    def __init__(self):
        self.exchanges = {}

    def register_exchange(self, name, exchange):
        self.exchanges[name] = exchange

    def get_common_tickers(self):
        all_tickers = [set(exchange.get_tickers()) for exchange in self.exchanges.values()]
        return set.intersection(*all_tickers)
    
    @staticmethod
    async def calc_exrate(ticker: str, seed: float):
        """
        upbit에서 seed(KRW)만큼의 특정 티커를 매수할 때, 매수가능수량을 계산하여
        해당 수량과 똑같은 수량을 bybit에서 매도할 때, upbit과 bybit의 환율을 계산합니다.
        """

        res = await asyncio.gather(
            UpbitExchange.get_ticker_orderbook([ticker]),
            BybitExchange.get_ticker_orderbook(ticker)
        )

        upbit_orderbook, bybit_orderbook = res

        # 업비트 주문가능수량 구하기
        remaining_seed = seed
        upbit_available_size = 0
        for unit in upbit_orderbook[0]["orderbook"]:
            ob_quote_volume = unit["ask_price"] * unit["ask_size"]
            if remaining_seed >= ob_quote_volume:
                upbit_available_size += unit["ask_size"]
                remaining_seed -= ob_quote_volume
            else:
                upbit_available_size += remaining_seed / unit["ask_price"]
                break

        # 바이비트에서 해당 주문가능수량만큼 매도할 때 필요한 금액 구하기
        remaining_size = upbit_available_size
        bybit_quote_volume = 0
        for unit in bybit_orderbook["orderbook"]:
            if remaining_size >= unit["bid_size"]:
                bybit_quote_volume += unit["bid_price"] * unit["bid_size"]
                remaining_size -= unit["bid_size"]
            else:
                bybit_quote_volume += unit["bid_price"] * remaining_size
                break
            
        # 방어 로직
        if upbit_available_size == 0 or bybit_quote_volume == 0:
            raise ValueError("Available size or quote volume is zero, cannot calculate exchange rate.")
        
        # 환율 계산
        exchange_rate = seed / bybit_quote_volume
        return {
            "ticker": ticker,
            "exchange_rate": exchange_rate
        }
        
    @staticmethod
    async def calc_exrate_batch(tickers: list[str], seed: float, exchange1: str, exchange2: str):
        """
        여러 티커에 대해 환율을 일괄 계산합니다.
        exchange1, exchange2: 거래소 이름(str, 예: 'upbit', 'bybit') 또는 클래스/인스턴스
        """
        def get_exchange_class(name):
            # 예: 'upbit' -> 'UpbitExchange', 'bybit' -> 'BybitExchange'
            class_name = name.lower().capitalize() + 'Exchange'
            return globals().get(class_name)

        ex1 = exchange1
        ex2 = exchange2
        if isinstance(exchange1, str):
            ex1_class = get_exchange_class(exchange1)
            if ex1_class is None:
                raise ValueError(f"Unknown exchange1: {exchange1}")
            ex1 = ex1_class
        if isinstance(exchange2, str):
            ex2_class = get_exchange_class(exchange2)
            if ex2_class is None:
                raise ValueError(f"Unknown exchange2: {exchange2}")
            ex2 = ex2_class

        # 클래스면 클래스 메서드 호출, 인스턴스면 인스턴스 메서드 호출
        get_orderbook1 = getattr(ex1, 'get_ticker_orderbook')
        get_orderbook2 = getattr(ex2, 'get_ticker_orderbook')
        
        exchange1_orderbooks = await get_orderbook1(tickers)
        exchange2_orderbooks = await asyncio.gather(
            *[get_orderbook2(ticker) for ticker in tickers]
        )
        results = []
        for ob1, ob2 in zip(exchange1_orderbooks, exchange2_orderbooks):
            available_size = 0
            remaining_seed = seed
            for unit in ob1["orderbook"]:
                ob_quote_volume = unit["ask_price"] * unit["ask_size"]
                if remaining_seed >= ob_quote_volume:
                    available_size += unit["ask_size"]
                    remaining_seed -= ob_quote_volume
                else:
                    available_size += remaining_seed / unit["ask_price"]
                    break
            remaining_size = available_size
            quote_volume = 0
            for unit in ob2["orderbook"]:
                if remaining_size >= unit["bid_size"]:
                    quote_volume += unit["bid_price"] * unit["bid_size"]
                    remaining_size -= unit["bid_size"]
                else:
                    quote_volume += unit["bid_price"] * remaining_size
                    break
            if available_size == 0 or quote_volume == 0:
                continue
            exchange_rate = seed / quote_volume
            results.append({
                "name": ob1["ticker"],
                "ex_rate": exchange_rate
            })
        return results


exMgr = ExchangeManager()
