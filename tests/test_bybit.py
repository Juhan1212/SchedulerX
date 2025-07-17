import aiohttp
import pytest
from backend.exchanges.bybit import BybitExchange
from unittest.mock import AsyncMock, MagicMock
import json

@pytest.fixture
def bybit_service():
    # BybitExchange 인스턴스를 생성하고, HTTP 클라이언트를 모킹합니다.
    return BybitExchange('test_api_key', 'test_api_secret')
    # exchange.client = MagicMock()  # HTTP 클라이언트를 모킹
    
@pytest.mark.asyncio
async def test_get_tickers_success(bybit_service):
    # Bybit API의 성공적인 응답을 모킹합니다.
    # mock_response = {
    #     "retCode": 0,
    #     "result": {
    #         "list": [
    #             {"symbol": "BTCUSDT"},
    #             {"symbol": "ETHUSDT"},
    #             {"symbol": "XRPBTC"}
    #         ]
    #     }
    # }
    # aiohttp.ClientSession.get = AsyncMock(return_value=MagicMock(
    #     status=200,
    #     json=AsyncMock(return_value=mock_response)
    # ))

    # get_tickers 호출
    tickers = await bybit_service.get_tickers()
    print(tickers)

    # 결과 검증
    # assert tickers == ["BTC", "ETH"]

@pytest.mark.asyncio
async def test_get_tickers_failure(bybit_service):
    # Bybit API의 실패 응답을 모킹합니다.
    aiohttp.ClientSession.get = AsyncMock(return_value=MagicMock(
        status=500,
        text=AsyncMock(return_value="Internal Server Error")
    ))

    # get_tickers 호출 및 예외 검증
    with pytest.raises(Exception, match="Bybit API Error: 500 - Internal Server Error"):
        await bybit_service.get_tickers()

@pytest.mark.asyncio
async def test_get_orderbook_success(bybit_service):
    # Bybit API의 성공적인 주문서 응답을 모킹합니다.
    # mock_orderbook_response = {
    #     "result": {
    #         "orderBook": {
    #             "bids": [[50000, 1], [49900, 2]],
    #             "asks": [[50100, 1], [50200, 2]]
    #         }
    #     }
    # }
    # aiohttp.ClientSession.get = AsyncMock(return_value=MagicMock(
    #     status=200,
    #     json=AsyncMock(return_value=mock_orderbook_response)
    # ))

    # get_orderbook 호출
    orderbook = await bybit_service.get_orderbook("BTC")
    print(orderbook)
    
    # 결과 검증
    # assert orderbook == mock_orderbook_response["result"]["orderBook"]