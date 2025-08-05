import time
import hmac
import hashlib
import json as pyjson
import logging
import os
import aiohttp
from .base import Exchange
import datetime

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
    async def get_ticker_candles(cls, ticker: str, interval: str = "1m", to: int = 0, count: int = 200):
        """
        Bybit에서 특정 티커의 캔들 데이터를 가져옵니다.

        Args:
            ticker (str): 티커 이름 (예: 'BTC')
            interval (str): 캔들 간격 (예: '1m','3m','5m','15m','30m','1h','4h','8h','1d','1w')
            count (int): 가져올 캔들의 개수

        Returns:
            list[dict]: 표준화된 캔들 데이터 리스트

        Raises:
            Exception: API 호출 실패 시 발생하는 예외
        """
        # interval 변환: 프론트/내부 표준 → Bybit API 규격
        interval_map = {
            "1m": "1", 
            "3m": "3", 
            "5m": "5", 
            "15m": "15", 
            "30m": "30",
            "1h": "60", 
            "4h": "240", 
            "8h": "480",
            "1d": "D", 
            "1w": "W"
        }
        bybit_interval = interval_map.get(interval, interval)
        try:
            url = f"{cls.server_url}/v5/market/kline?category=linear&symbol={ticker}USDT&interval={bybit_interval}&limit={count}"
            if to != 0:
                url += f"&end={to * 1000}"  # Bybit expects milliseconds
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
                                "timestamp": float(candle[0]) / 1000,  # Bybit timestamp is in milliseconds
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
        
    async def order(self, ticker: str, side: str, seed: float):
        """
        Bybit에서 지정가/시장가 주문을 실행합니다.

        Args:
            ticker (str): 티커 이름 (예: "BTC")
            side (str): 주문 방향 ("Buy" 또는 "Sell")
            seed (float): 주문 가격 (시장가 매수 시 사용)
            size (float): 주문 수량 (시장가 매도 시 사용)

        Returns:
            dict: 주문 결과 정보

        Raises:
            Exception: API 호출 실패 시 발생하는 예외
        """
        try:
            url = f"{self.server_url}/v5/order/create"
            recv_window = "5000"
            timestamp = str(int(time.time() * 1000))
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            # 시장가 매수
            if side.lower() == "bid":
                body = {
                    "category": "linear",
                    "symbol": f"{ticker}USDT",
                    "side": "Buy",
                    "orderType": "Market",
                    "qty": '0',
                    "positionIdx": 1,
                    "orderLinkId": f"{ticker}_{datetime.datetime.now().strftime('%Y%m%d %H:%M:%S')}"  # 고유 주문 ID
                }
            # 시장가 매도
            elif side.lower() == "ask":
                body = {
                    "category": "linear",
                    "symbol": f"{ticker}USDT",
                    "side": "Sell",
                    "orderType": "Market",
                    "qty": str(seed),
                    "positionIdx": 2,
                    "orderLinkId": f"{ticker}_{datetime.datetime.now().strftime('%Y%m%d %H:%M:%S')}"  # 고유 주문 ID
                }
            else:
                raise ValueError("Invalid side: must be 'bid' or 'ask'")

            # Bybit signature 생성 (key 순서 고정)
            body_str = pyjson.dumps(body)
            sign_payload = timestamp + self.api_key + recv_window + body_str
            signature = hmac.new(
                self.secret_key.encode("utf-8"),
                sign_payload.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()

            headers["X-BAPI-SIGN"] = signature
            headers["X-BAPI-API-KEY"] = self.api_key
            headers["X-BAPI-TIMESTAMP"] = timestamp
            headers["X-BAPI-RECV-WINDOW"] = recv_window

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=body, headers=headers) as res:
                    if res.status != 200:
                        raise Exception(f"Bybit API Error: {res.status} - {await res.text()}")
                    return await res.json()
        except aiohttp.ClientError as e:
            logger.error(f"Network error while placing order for {ticker}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while placing order for {ticker}: {e}")
            raise
    
    async def get_position_info(self, ticker: str):
        """
        Bybit에서 특정 티커의 포지션 정보를 가져옵니다.

        Args:
            ticker (str): 티커 이름 (예: "BTC")

        Returns:
            dict: 포지션 정보

        Raises:
            Exception: API 호출 실패 시 발생하는 예외
        """
        try:
            query_string = f"category=linear&symbol={ticker}USDT"
            url = f"{self.server_url}/v5/position/list?{query_string}"
            recv_window = "5000"
            timestamp = str(int(time.time() * 1000))
            headers = {
                "Accept": "application/json"
            }
            # Bybit signature 생성 (key 순서 고정, GET은 쿼리스트링 포함)
            sign_payload = timestamp + self.api_key + recv_window + query_string
            signature = hmac.new(
                self.secret_key.encode("utf-8"),
                sign_payload.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()

            headers["X-BAPI-SIGN"] = signature
            headers["X-BAPI-API-KEY"] = self.api_key
            headers["X-BAPI-TIMESTAMP"] = timestamp
            headers["X-BAPI-RECV-WINDOW"] = recv_window

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as res:
                    if res.status != 200:
                        raise Exception(f"Bybit API Error: {res.status} - {await res.text()}")

                    response = await res.json()
                    if response.get("retCode") == 0:
                        return response["result"]
                    raise Exception(f"Bybit API Error: {response.get('retMsg')}")
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching position info for {ticker}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while fetching position info for {ticker}: {e}")
            raise
        
    async def get_lot_size(self, ticker: str) -> float | None:
        """
        Bybit에서 해당 티커의 최소 주문 단위(lot size)를 조회합니다.

        Args:
            ticker (str): 티커 이름 (예: "BTC")

        Returns:
            float | None: 최소 주문 단위(qtyStep), 조회 실패 시 None
        """
        url = f"{self.server_url}/v5/market/instruments-info?category=linear&symbol={ticker}USDT"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as res:
                    if res.status != 200:
                        logger.error(f"Bybit lot size 조회 실패: {res.status} - {await res.text()}")
                        return None
                    data = await res.json()
                    try:
                        return float(data['result']['list'][0]['lotSizeFilter']['qtyStep'])
                    except Exception as e:
                        logger.error(f"Bybit lot size 파싱 실패: {e}")
                        return None
        except Exception as e:
            logger.error(f"Bybit lot size 조회 중 예외 발생: {e}")
            return None
        
    async def get_orders(self, ticker: str, order_id: str):
        """
        Bybit에서 특정 티커의 주문 내역을 조회합니다.

        Args:
            ticker (str): 티커 이름 (예: "BTC")
            order_id (str): 주문 ID

        Returns:
            list[dict]: 주문 내역 리스트

        Raises:
            Exception: API 호출 실패 시 발생하는 예외
        """
        try:
            query_string = f"category=linear&symbol={ticker}USDT&orderId={order_id}"
            url = f"{self.server_url}/v5/order/realtime?{query_string}"
            recv_window = "5000"
            timestamp = str(int(time.time() * 1000))
            headers = {
                "Accept": "application/json"
            }
            # Bybit signature 생성 (key 순서 고정, GET은 쿼리스트링 포함)
            sign_payload = timestamp + self.api_key + recv_window + query_string
            signature = hmac.new(
                self.secret_key.encode("utf-8"),
                sign_payload.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()

            headers["X-BAPI-SIGN"] = signature
            headers["X-BAPI-API-KEY"] = self.api_key
            headers["X-BAPI-TIMESTAMP"] = timestamp
            headers["X-BAPI-RECV-WINDOW"] = recv_window
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as res:
                    if res.status != 200:
                        raise Exception(f"Bybit API Error: {res.status} - {await res.text()}")

                    response = await res.json()
                    if response.get("retCode") == 0:
                        return response.get("result", {}).get("list", [])
                    raise Exception(f"Bybit API Error: {response.get('retMsg')}")
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching orders for {ticker}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while fetching orders for {ticker}: {e}")
            raise
        
    async def get_available_balance(self) -> float:
        """
        Bybit에서 사용 가능한 잔액을 조회합니다.

        Returns:
            float: 사용 가능한 잔액

        Raises:
            Exception: API 호출 실패 시 발생하는 예외
        """
        try:
            query_string = "accountType=UNIFIED"
            url = f"{self.server_url}/v5/account/wallet-balance?{query_string}"
            recv_window = "5000"
            timestamp = str(int(time.time() * 1000))
            headers = {
                "Accept": "application/json"
            }
            # Bybit signature 생성 (key 순서 고정)
            sign_payload = timestamp + self.api_key + recv_window + query_string
            signature = hmac.new(
                self.secret_key.encode("utf-8"),
                sign_payload.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()

            headers["X-BAPI-SIGN"] = signature
            headers["X-BAPI-API-KEY"] = self.api_key
            headers["X-BAPI-TIMESTAMP"] = timestamp
            headers["X-BAPI-RECV-WINDOW"] = recv_window
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as res:
                    if res.status != 200:
                        raise Exception(f"Bybit API Error: {res.status} - {await res.text()}")

                    response = await res.json()
                    if response.get("retCode") == 0:
                        return response["result"]["list"][0].get('totalAvailableBalance', 0.0)
                    raise Exception(f"Bybit API Error: {response.get('retMsg')}")
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching available balance: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while fetching available balance: {e}")
            raise