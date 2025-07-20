import asyncio
from backend.exchanges.bybit import BybitExchange
from backend.exchanges.upbit import UpbitExchange


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
    async def calc_exrate_batch(tickers: list[str], seed: float):
        """
        여러 티커에 대해 환율을 일괄 계산합니다.
        """
        # Upbit: batch 요청
        upbit_orderbooks = await UpbitExchange.get_ticker_orderbook(tickers)
        # Bybit: for문으로 개별 요청
        bybit_orderbooks = await asyncio.gather(
            *[BybitExchange.get_ticker_orderbook(ticker) for ticker in tickers]
        )
        results = []
        for upbit_ob, bybit_ob in zip(upbit_orderbooks, bybit_orderbooks):
            upbit_available_size = 0
            remaining_seed = seed
            
            for unit in upbit_ob["orderbook"]:
                ob_quote_volume = unit["ask_price"] * unit["ask_size"]
                if remaining_seed >= ob_quote_volume:
                    upbit_available_size += unit["ask_size"]
                    remaining_seed -= ob_quote_volume
                else:
                    upbit_available_size += remaining_seed / unit["ask_price"]
                    break
            
            remaining_size = upbit_available_size
            bybit_quote_volume = 0
            
            for unit in bybit_ob["orderbook"]:
                if remaining_size >= unit["bid_size"]:
                    bybit_quote_volume += unit["bid_price"] * unit["bid_size"]
                    remaining_size -= unit["bid_size"]
                else:
                    bybit_quote_volume += unit["bid_price"] * remaining_size
                    break
            
            if upbit_available_size == 0 or bybit_quote_volume == 0:
                continue
            
            exchange_rate = seed / bybit_quote_volume
            results.append({
                "name": upbit_ob["ticker"],
                "ex_rate": exchange_rate
            })
        return results


exMgr = ExchangeManager()
