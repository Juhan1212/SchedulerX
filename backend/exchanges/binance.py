import asyncio
import logging
import os
from .base import Exchange

from binance import AsyncClient
from binance.exceptions import BinanceAPIException

logger = logging.getLogger(__name__)

class BinanceExchange(Exchange):
    """
    python-binance AsyncClient 기반 Binance API 비동기 래퍼 클래스 (현물 USDT 마켓 기준)
    """
    name = "binance"

    def __init__(self, api_key: str = '', secret_key: str = ''):
        self.api_key = api_key
        self.secret_key = secret_key

    @classmethod
    async def get_tickers(cls) -> list[str]: 
        """
        Binance에서 USDT 마켓 티커 목록을 가져옵니다.
        Returns:
            list[str]: USDT 마켓 티커 리스트 (USDT 접미사 제거)
        """
        try:
            client = await AsyncClient.create()
            tickers = await client.get_all_tickers()
            usdt_tickers = filter(lambda x: x['symbol'].endswith('USDT'), tickers)
            processed = map(lambda x: x['symbol'].replace('USDT', ''), usdt_tickers)
            return list(processed)
        except BinanceAPIException as e:
            logger.error("Binance API error: %s", e)
            raise

    @classmethod
    async def get_ticker_orderbook(cls, ticker: str):
        """
        Binance에서 특정 티커의 오더북을 조회합니다.
        Args:
            ticker (str): 티커 이름 (예: 'BTC')
        Returns:
            dict: 표준화된 오더북 정보
        """
        try:
            client = await AsyncClient.create()
            ob = await client.get_order_book(symbol=f"{ticker}USDT")
            orderbook = {
                "ticker": ticker,
                "timestamp": ob.get("lastUpdateId"),
                "orderbook": [
                    {
                        "ask_price": float(ask[0]),
                        "ask_size": float(ask[1]),
                        "bid_price": float(bid[0]),
                        "bid_size": float(bid[1])
                    }
                    for ask, bid in zip(ob["asks"], ob["bids"])
                ]
            }
            return orderbook
        except BinanceAPIException as e:
            logger.error("Binance API error: %s", e)
            raise

    @classmethod
    async def get_ticker_candles(cls, ticker: str, interval: str = "1m", limit: int = 200):
        """
        Binance에서 특정 티커의 캔들 데이터를 조회합니다.
        Args:
            ticker (str): 티커 이름 (예: 'BTC')
            interval (str): 캔들 간격 (예: '1m', '5m', ...)
            limit (int): 캔들 개수
        Returns:
            list[dict]: 표준화된 캔들 데이터 리스트
        """
        try:
            client = await AsyncClient.create()
            klines = await client.get_klines(symbol=f"{ticker}USDT", interval=interval, limit=limit)
            candles = [
                {
                    "timestamp": int(item[0] / 1000),
                    "open": float(item[1]),
                    "high": float(item[2]),
                    "low": float(item[3]),
                    "close": float(item[4]),
                    "volume": float(item[5])
                }
                for item in klines
            ]
            return candles
        except BinanceAPIException as e:
            logger.error("Binance API error: %s", e)
            raise
        