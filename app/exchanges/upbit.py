import os
import logging
import uuid
import aiohttp
import dotenv
import jwt
from .base import Exchange

dotenv.load_dotenv()

logger = logging.getLogger(__name__)

class UpbitExchange(Exchange):
    """
    Upbit 거래소 API와 상호작용하기 위한 클래스.

    이 클래스는 시장 데이터를 가져오고 Upbit의 거래 서비스를 이용하기 위한 메서드를 제공합니다.
    """
    name = "upbit"
    server_url = "https://api.upbit.com"

    async def get_tickers(self):
        """
        Upbit에서 KRW 티커 목록을 가져옵니다.

        Returns:
            list[str]: KRW 티커 목록 (KRW- 접두사가 제거된 티커 이름 리스트)

        Raises:
            Exception: API 호출 실패 시 발생하는 예외
        """
        try:
            url = f"{self.server_url}/v1/market/all?is_details=true"
            headers = {"accept": "application/json"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as res:
                    if res.status != 200:
                        raise Exception(f"Upbit API Error: {res.status} - {await res.text()}")
                    
                    # filter로 KRW-로 시작하는 티커만 필터링
                    krw_tickers = filter(lambda x: x['market'].startswith('KRW-'), await res.json())

                    # map으로 market에서 "KRW-"를 제거
                    processed_tickers = map(
                        lambda x: x["market"].replace("KRW-", ""), krw_tickers
                    )

                    return list(processed_tickers)
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching tickers: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while fetching tickers: {e}")
            raise

    async def get_depo_with_pos_tickers(self):
        """
        Upbit에서 입출금 상태정보를 포함한 모든 티커 정보를 가져옵니다.

        Returns:
            dict: 티커 정보 (각 티커의 상세 정보가 포함된 딕셔너리)

        Raises:
            Exception: API 호출 실패 시 발생하는 예외
        """
        try:
            access_key = os.getenv("UPBIT_ACCESS_KEY")
            secret_key = os.getenv("UPBIT_SECRET_KEY")

            payload = {
                'access_key': access_key,
                'nonce': str(uuid.uuid4()),
            }

            jwt_token = jwt.encode(payload, secret_key)
            authorization = f"Bearer {jwt_token}"
            headers = {
                'Authorization': authorization,
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/v1/status/wallet", headers=headers) as res:
                    if res.status != 200:
                        raise Exception(f"Upbit API Error: {res.status} - {await res.text()}")
                    
                    dep_withdraw_pos_tickers = filter(
                        lambda x: x['wallet_state'] == 'working',
                        await res.json()
                    )
                    processed_tickers = map(
                        lambda x: x["currency"],
                        dep_withdraw_pos_tickers
                    )
                    return list(set(processed_tickers))
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching deposit/withdrawal tickers: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while fetching deposit/withdrawal tickers: {e}")
            raise

    async def get_orderbook(self, ticker: str):
        """
        Upbit에서 특정 티커의 주문서를 가져옵니다.

        Args:
            ticker (str): 티커 이름 (예: "BTC")

        Returns:
            dict: 표준화된 주문서 정보

        Raises:
            Exception: API 호출 실패 시 발생하는 예외
        """
        try:
            url = f"{self.server_url}/v1/orderbook?markets=KRW-{ticker}"
            headers = {"accept": "application/json"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as res:
                    if res.status != 200:
                        raise Exception(f"Upbit API Error: {res.status} - {await res.text()}")
                    
                    response = await res.json()
                    orderbook_data = response[0]
                    standardized_orderbook = {
                        "ticker": ticker,
                        "timestamp": orderbook_data["timestamp"],
                        "orderbook": [
                            {
                                "ask_price": unit["ask_price"],
                                "bid_price": unit["bid_price"],
                                "ask_size": unit["ask_size"],
                                "bid_size": unit["bid_size"]
                            }
                            for unit in orderbook_data["orderbook_units"]
                        ]
                    }
                    return standardized_orderbook
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching orderbook for {ticker}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while fetching orderbook for {ticker}: {e}")
            raise

    async def get_ticker_simple_price(self, ticker: str):
        """
        Upbit에서 현재 티커 가격을 가져옵니다.
        실제 가격과 차이는 있을 수 있으나, 이 프로젝트에서는 USDT 가격을 가져오기 위함이며, 보수적으로 가격을 가져옵니다.

        Returns:
            dict: 티커 가격 정보 (예: {"ticker": "BTC", "price": 50000})

        Raises:
            Exception: API 호출 실패 시 발생하는 예외
        """
        try:
            orderbook = await self.get_orderbook(ticker)
            if orderbook and orderbook["orderbook"]:
                return {"ticker": ticker, "price": orderbook["orderbook"][0]["ask_price"]}
            return {"ticker": ticker, "price": None}
        except Exception as e:
            logger.error(f"Error fetching ticker price for {ticker}: {e}")
            raise