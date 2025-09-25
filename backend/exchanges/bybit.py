import time
import hmac
import hashlib
import json as pyjson
import logging
import os
from urllib.parse import urlencode
import aiohttp
from .base import ForeignExchange
import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class BybitExchange(ForeignExchange):
    """
    Bybit 거래소 API와 상호작용하기 위한 클래스.

    이 클래스는 시장 데이터를 가져오고 Bybit의 거래 서비스를 이용하기 위한 메서드를 제공합니다.

    속성:
        client (HTTP): Bybit 통합 거래 HTTP 클라이언트 인스턴스.
    """
    name = "bybit"
    server_url = "https://api.bybit.com"

    def __init__(self, api_key: str = "", secret_key: str = ""):
        self.api_key = api_key
        self.secret_key = secret_key

    @classmethod
    def from_env(cls):
        """
        환경 변수에서 API 키와 시크릿 키를 로드하여 BybitExchange 인스턴스를 생성합니다.

        Returns:
            BybitExchange: BybitExchange 인스턴스
        """
        api_key = os.getenv("BYBIT_ACCESS_KEY")
        secret_key = os.getenv("BYBIT_SECRET_KEY")
        if not api_key or not secret_key:
            raise ValueError("BYBIT_ACCESS_KEY and BYBIT_SECRET_KEY must be set in environment variables.")
        return cls(api_key, secret_key)

    @classmethod
    async def get_tickers(cls):
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
                        return [
                            (x['symbol'].replace('USDT', ''), x['symbol'].replace('USDT', ''))
                            for x in response.get("result", {}).get("list", [])
                            if x['symbol'].endswith('USDT')
                        ]
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
            url = f"{cls.server_url}/v5/market/orderbook?category=linear&symbol={ticker}USDT&limit=500"
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

            # tradeMode 확인
            position_info = await self.get_position_info(ticker)
            trade_mode = None
            if position_info and 'list' in position_info and len(position_info['list']) > 0:
                trade_mode = position_info['list'][0].get('tradeMode')

            # 시장가 매수
            if side.lower() == "bid":
                body = {
                    "category": "linear",
                    "symbol": f"{ticker}USDT",
                    "side": "Buy",
                    "orderType": "Market",
                    "qty": '0',
                    "orderLinkId": f"{ticker}_{datetime.datetime.now().strftime('%Y%m%d %H:%M:%S')}"
                }
                if trade_mode == 1:
                    body["positionIdx"] = '1'
            # 시장가 매도
            elif side.lower() == "ask":
                body = {
                    "category": "linear",
                    "symbol": f"{ticker}USDT",
                    "side": "Sell",
                    "orderType": "Market",
                    "qty": str(seed),
                    "orderLinkId": f"{ticker}_{datetime.datetime.now().strftime('%Y%m%d %H:%M:%S')}"
                }
                if trade_mode == 1:
                    body["positionIdx"] = '2'
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
    
    async def close_position(self, ticker: str):
        """
        Bybit에서 특정 티커의 포지션을 청산합니다.

        Args:
            ticker (str): 티커 이름 (예: "BTC")

        Returns:
            dict: 청산 결과

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

            body = {
                "category": "linear",
                "symbol": f"{ticker}USDT",
                "side": "Buy",
                "orderType": "Market",
                "qty": '0',
                "reduceOnly": True,
                "closeOnTrigger": True
            }

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
            logger.error(f"Network error while closing position for {ticker}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while closing position for {ticker}: {e}")
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
        
    async def get_order(self, order_id: str):
        """
        Bybit에서 특정 티커의 주문 내역을 조회합니다.

        Args:
            ticker (str): 티커 이름 (예: "BTC")
            order_id (str): 주문 ID

        Returns:
            dict: 주문 내역

        Raises:
            Exception: API 호출 실패 시 발생하는 예외
        """
        try:
            query_string = f"category=linear&&orderId={order_id}"
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
                        return response.get("result", {}).get("list", [])[0]
                    raise Exception(f"Bybit API Error: {response.get('retMsg')}")
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching orders for {order_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while fetching orders for {order_id}: {e}")
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
                        return float(response["result"]["list"][0].get('totalAvailableBalance', 0.0))
                    raise Exception(f"Bybit API Error: {response.get('retMsg')}")
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching available balance: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while fetching available balance: {e}")
            raise
        
    async def get_depo_with_pos_tickers(self, coin: str = "") -> list[dict]:
        """
        Bybit에서 각 코인별 입금/출금 가능 여부, 수수료, 최소 금액, 확인 횟수 등 정보를 반환합니다.

        Args:
            coin (str, optional): 특정 코인 심볼. 빈 문자열이면 전체 반환.

        Returns:
            list[dict]: 각 코인별 입출금 정보 리스트
        """
        try:
            url = f"{self.server_url}/v5/asset/coin/query-info"
            params = {}
            if coin:
                params["coin"] = coin
            # 쿼리스트링 생성
            query_string = urlencode(params)
            
            recv_window = "5000"
            timestamp = str(int(time.time() * 1000))
            # Bybit signature 생성 (key 순서 고정, GET은 쿼리스트링 포함)
            sign_payload = timestamp + self.api_key + recv_window + query_string
            signature = hmac.new(
                self.secret_key.encode("utf-8"),
                sign_payload.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()

            headers = {
                "Accept": "application/json",
                "X-BAPI-SIGN": signature,
                "X-BAPI-API-KEY": self.api_key,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-RECV-WINDOW": recv_window
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as res:
                    if res.status != 200:
                        raise Exception(f"Bybit API Error: {res.status} - {await res.text()}")
                    data = await res.json()
                    if data.get("retCode") != 0:
                        raise Exception(f"Bybit API Error: {data.get('retMsg')}")
                    result = []
                    for coin_info in data.get("result", {}).get("rows", []):
                        for chain in coin_info.get('chains', []):
                            result.append({
                                "coin": coin_info.get("name"),
                                "chain": chain.get("chainType"),
                                "deposit_yn": chain.get("chainDeposit"),
                                "withdraw_yn": chain.get("chainWithdraw"),
                            })
                    return result
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching coin deposit/withdraw info: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while fetching coin deposit/withdraw info: {e}")
            raise
        
    async def get_full_ticker_info(self):
        """
        USDT 티커 목록, 네트워크, 입출금 가능여부를 모두 합성하여 반환
        Returns:
            list[dict]: [{ticker, display_name, chain, deposit_enabled, withdraw_enabled, deposit_min, withdraw_min, withdraw_fee, confirm_count}, ...]
        """
        tickers = await self.get_tickers()  # [('BTC', 'BTC'), ...]
        # Bybit은 네트워크 정보가 chain으로 제공됨
        coin_list = [ticker for ticker, _ in tickers]
        # 입출금 정보 전체 조회
        coin_infos = await self.get_depo_with_pos_tickers()
        result = []
        for ticker, display_name in tickers:
            # 여러 체인 중 대표 체인(chainType==ticker) 우선
            chains = [info for info in coin_infos if info['coin'] == ticker]
            for chain in chains:
                result.append({
                    'ticker': ticker,
                    'display_name': display_name,
                    'net_type': chain.get('chain'),
                    'deposit_yn': chain.get('deposit_yn'),
                    'withdraw_yn': chain.get('withdraw_yn'),
                })
        return result
    
    async def set_leverage(self, ticker: str, leverage: str) -> dict:
        """
        레버리지를 설정합니다.
        """
        try:
            url = f"{self.server_url}/v5/position/set-leverage"
            recv_window = "5000"
            timestamp = str(int(time.time() * 1000))
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            body = {
                "category" : "linear",
                "symbol": f"{ticker}USDT",
                "buyLeverage": leverage,
                "sellLeverage": leverage
            }

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