import os
import logging
import aiohttp
import dotenv
from .base import Exchange

dotenv.load_dotenv()

logger = logging.getLogger(__name__)

class GateioExchange(Exchange):
    """
    Gate.io 거래소 API와 상호작용하기 위한 클래스.
    주요 시장 데이터 및 거래 서비스 메서드 제공
    """
    name = "gateio"
    server_url = "https://api.gateio.ws/api/v4"

    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key

    @classmethod
    def from_env(cls):
        api_key = os.getenv("GATEIO_API_KEY")
        secret_key = os.getenv("GATEIO_SECRET_KEY")
        if not api_key or not secret_key:
            raise ValueError("GATEIO_API_KEY and GATEIO_SECRET_KEY must be set in environment variables.")
        return cls(api_key, secret_key)
    
    @classmethod
    async def get_ticker(cls, ticker: str):
        """
        Gate.io에서 USDT 마켓 티커 목록을 가져옵니다.
        Returns:
            list[str]: 티커 목록
        """
        try:
            url = f"{cls.server_url}/futures/usdt/contracts/{ticker}_USDT"
            headers = {"accept": "application/json"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as res:
                    if res.status != 200:
                        raise Exception(f"Gate.io API Error: {res.status} - {await res.text()}")
                    ticker_data = await res.json()
                    return ticker_data
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching tickers: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while fetching tickers: {e}")
            raise

    @classmethod
    async def get_tickers(cls):
        """
        Gate.io에서 KRW 마켓 티커 목록을 가져옵니다 (예시: USDT 마켓).
        Returns:
            list[str]: 티커 목록
        """
        try:
            url = f"{cls.server_url}/futures/usdt/contracts"
            headers = {"accept": "application/json"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as res:
                    if res.status != 200:
                        raise Exception(f"Gate.io API Error: {res.status} - {await res.text()}")
                    tickers = await res.json()
                    # 예시: USDT 마켓만 필터링
                    usdt_tickers = filter(lambda x: x['name'].endswith('_USDT'), tickers)
                    processed_tickers = map(lambda x: x['name'].replace('_USDT', ''), usdt_tickers)
                    return list(processed_tickers)
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching tickers: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while fetching tickers: {e}")
            raise

    @classmethod
    async def get_ticker_orderbook(cls, ticker: str):
        """
        Gate.io에서 특정 티커의 주문서 조회
        Returns:
            dict: 표준화된 주문서 정보
        """
        try:
            url = f"{cls.server_url}/spot/order_book?currency_pair={ticker}_USDT"
            headers = {"accept": "application/json"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as res:
                    if res.status != 200:
                        raise Exception(f"Gate.io API Error: {res.status} - {await res.text()}")
                    orderbook_data = await res.json()
                    standardized_orderbook = {
                        "ticker": ticker,
                        "timestamp": orderbook_data.get("update_time", None),
                        "orderbook": [
                            {
                                "ask_price": float(orderbook_data["asks"][0][0]) if orderbook_data["asks"] else None,
                                "bid_price": float(orderbook_data["bids"][0][0]) if orderbook_data["bids"] else None,
                                "ask_size": float(orderbook_data["asks"][0][1]) if orderbook_data["asks"] else None,
                                "bid_size": float(orderbook_data["bids"][0][1]) if orderbook_data["bids"] else None,
                            }
                        ]
                    }
                    return standardized_orderbook
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching orderbook for {ticker}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while fetching orderbook for {ticker}: {e}")
            raise

    @classmethod
    async def get_ticker_ob_price(cls, ticker: str):
        """
        Gate.io에서 현재 티커의 매수 기준 최저호가 가격 조회
        Returns:
            dict: {"ticker": ticker, "price": ...}
        """
        try:
            orderbook = await cls.get_ticker_orderbook(ticker)
            if orderbook and orderbook["orderbook"]:
                return {"ticker": ticker, "price": orderbook["orderbook"][0]["ask_price"]}
            return {"ticker": ticker, "price": None}
        except Exception as e:
            logger.error(f"Error fetching ticker price for {ticker}: {e}")
            raise

    @classmethod
    async def get_ticker_candles(cls, ticker: str, interval: str = "1m", to: int = 0, limit: int = 200):
        """
        Gate.io에서 특정 티커의 캔들 데이터 조회
        interval (str): 캔들 간격 (지원: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 8h, 1d, 1w)
        Returns:
            list[dict]: 캔들 데이터 리스트
        """
        try:
            allowed_intervals = ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "8h", "1d", "1w"]
            if interval not in allowed_intervals:
                raise ValueError(f"Unsupported interval: {interval}")
            url = f"{cls.server_url}/futures/usdt/candlesticks?contract={ticker}_USDT&interval={interval}&limit={limit}"
            if to != 0:
                url += f"&to={to}"
            headers = {"accept": "application/json"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as res:
                    if res.status != 200:
                        raise Exception(f"Gate.io API Error: {res.status} - {await res.text()}")
                    candles = await res.json()
                    return [
                        {
                            "timestamp": int(candle['t']),
                            "open": float(candle['o']),
                            "close": float(candle['c']),
                            "high": float(candle['h']),
                            "low": float(candle['l']),
                            "volume": float(candle['v'])
                        }
                        for candle in candles
                    ]
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching candles for {ticker}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while fetching candles for {ticker}: {e}")
            raise
