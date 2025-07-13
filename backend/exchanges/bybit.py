import logging
import os
import aiohttp
from .base import Exchange

logger = logging.getLogger(__name__)

class BybitExchange(Exchange):
    """
    Bybit 거래소 API와 상호작용하기 위한 클래스.

    이 클래스는 시장 데이터를 가져오고 Bybit의 거래 서비스를 이용하기 위한 메서드를 제공합니다.

    속성:
        client (HTTP): Bybit 통합 거래 HTTP 클라이언트 인스턴스.
    """
    name = "bybit"
    server_url = "https://api.bybit.com"

    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key

    @classmethod
    def from_env(cls):
        """
        환경 변수에서 API 키와 시크릿 키를 로드하여 BybitExchange 인스턴스를 생성합니다.

        Returns:
            BybitExchange: BybitExchange 인스턴스
        """
        api_key = os.getenv("BYBIT_API_KEY")
        secret_key = os.getenv("BYBIT_SECRET_KEY")
        if not api_key or not secret_key:
            raise ValueError("BYBIT_API_KEY and BYBIT_SECRET_KEY must be set in environment variables.")
        return cls(api_key, secret_key)

    @classmethod
    async def get_tickers(cls) -> list[str]:
        """
        Bybit에서 USDT 티커 목록을 가져옵니다.

        Returns:
            list[str]: USDT 티커 목록 (USDT 접미사가 제거된 티커 이름 리스트)

        Raises:
            Exception: API 호출 실패 시 발생하는 예외
        """
        try:
            url = f"{cls.server_url}/v5/market/tickers?category=linear&baseCoin=USDT"
            headers = {"accept": "application/json"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as res:
                    if res.status != 200:
                        raise Exception(f"Bybit API Error: {res.status} - {await res.text()}")

                    response = await res.json()
                    if response.get("retCode") == 0:  # 성공 코드 확인
                        usdt_tickers = filter(
                            lambda x: x['symbol'].endswith('USDT'),
                            response.get("result", {}).get("list", [])
                        )
                        processed_tickers = map(
                            lambda x: x['symbol'].replace('USDT', ''),
                            usdt_tickers
                        )
                        return list(processed_tickers)
                    raise Exception(f"Bybit API Error: {response.get('retMsg')}")
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching tickers: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while fetching tickers: {e}")
            raise
        
    @classmethod
    async def get_ticker_orderbook(cls, ticker: str):
        """
        Bybit에서 특정 티커의 주문서를 가져옵니다.

        Args:
            ticker (str): 티커 이름 (예: 'BTC')

        Returns:
            dict: 표준화된 주문서 정보

        Raises:
            Exception: API 호출 실패 시 발생하는 예외
        """
        try:
            url = f"{cls.server_url}/v5/market/orderbook?category=linear&symbol={ticker}USDT"
            headers = {"accept": "application/json"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as res:
                    if res.status != 200:
                        raise Exception(f"Bybit API Error: {res.status} - {await res.text()}")

                    response = await res.json()
                    if response.get("retCode") == 0:
                        orderbook_data = response["result"]
                        standardized_orderbook = {
                            "ticker": ticker,
                            "timestamp": orderbook_data["ts"],
                            "orderbook": [
                                {
                                    "ask_price": float(ask[0]),
                                    "bid_price": float(bid[0]),
                                    "ask_size": float(ask[1]),
                                    "bid_size": float(bid[1])
                                }
                                for ask, bid in zip(orderbook_data["a"], orderbook_data["b"])
                            ]
                        }
                        return standardized_orderbook
                    raise Exception(f"Bybit API Error: {response.get('retMsg')}")
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching orderbook for {ticker}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while fetching orderbook for {ticker}: {e}")
            raise
        
    @classmethod
    async def get_ticker_candles(cls, ticker: str, interval: str = "1", count: int = 200):
        """
        Bybit에서 특정 티커의 캔들 데이터를 가져옵니다.

        Args:
            ticker (str): 티커 이름 (예: 'BTC')
            interval (str): 캔들 간격 (예: 1,3,5,15,30,60,120,240,360,720,D,W,M)
            count (int): 가져올 캔들의 개수

        Returns:
            list[dict]: 표준화된 캔들 데이터 리스트

        Raises:
            Exception: API 호출 실패 시 발생하는 예외
        """
        try:
            url = f"{cls.server_url}/v5/market/candles?category=linear&symbol={ticker}USDT&interval={interval}&limit={count}"
            headers = {"accept": "application/json"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as res:
                    if res.status != 200:
                        raise Exception(f"Bybit API Error: {res.status} - {await res.text()}")

                    response = await res.json()
                    if response.get("retCode") == 0:
                        candles = response["result"]
                        standardized_candles = [
                            {
                                "timestamp": candle[0],
                                "open": float(candle[1]),
                                "high": float(candle[2]),
                                "low": float(candle[3]),
                                "close": float(candle[4]),
                                "volume": float(candle[5])
                            }
                            for candle in candles['list']
                        ]
                        return standardized_candles
                    raise Exception(f"Bybit API Error: {response.get('retMsg')}")
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching candles for {ticker}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while fetching candles for {ticker}: {e}")
            raise