import aiohttp
import pytest
from backend.exchanges.bybit import BybitExchange
from unittest.mock import AsyncMock, MagicMock
import json
import os

api_key = os.getenv('BYBIT_ACCESS_KEY')
secret_key = os.getenv('BYBIT_SECRET_KEY')

@pytest.fixture
def bybit_service():
    if not api_key or not secret_key:
        raise ValueError("BYBIT_API_KEY and BYBIT_SECRET_KEY must be set in environment variables.")
    
    # BybitExchange 인스턴스를 생성하고, HTTP 클라이언트를 모킹합니다.
    return BybitExchange(api_key, secret_key)
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
    
@pytest.mark.asyncio
async def test_order(bybit_service):
    # Bybit API의 주문 성공 응답을 모킹합니다.
    # mock_order_response = {
    #     "retCode": 0,
    #     "result": {
    #         "orderId": "1234567890",
    #         "symbol": "BTCUSDT",
    #         "side": "Buy",
    #         "price": 50000,
    #         "qty": 1
    #     }
    # }
    # aiohttp.ClientSession.post = AsyncMock(return_value=MagicMock(
    #     status=200,
    #     json=AsyncMock(return_value=mock_order_response)
    # ))

    # order 호출
    order_result = await bybit_service.order("BNB", "ask", 0.5)
    
    print(order_result)
    
    # 결과 검증
    # assert order_result["retCode"] == 0
    
@pytest.mark.asyncio
async def test_get_position_info(bybit_service):
    # Bybit API의 포지션 정보 응답을 모킹합니다.
    # mock_position_response = {
    #     "retCode": 0,
    #     "result": {
    #         "list": [
    #             {"symbol": "BTCUSDT", "side": "Buy", "size": 1, "entryPrice": 50000},
    #             {"symbol": "ETHUSDT", "side": "Sell", "size": 2, "entryPrice": 3000}
    #         ]
    #     }
    # }
    # aiohttp.ClientSession.get = AsyncMock(return_value=MagicMock(
    #     status=200,
    #     json=AsyncMock(return_value=mock_position_response)
    # ))

    # get_position_info 호출
    positions = await bybit_service.get_position_info("BTC")
    res = list(filter(lambda x: float(x.get('size', 0)) > 0, positions.get('list', [])))
    
    print(json.dumps(positions, indent=2))
    print(json.dumps(res, indent=2))
    
    # 결과 검증
    # assert len(positions) > 0
    
@pytest.mark.asyncio
async def test_get_lot_size(bybit_service):
    # Bybit API의 최소 주문 단위(lot size) 응답을 모킹합니다.
    # mock_lot_size_response = {
    #     "retCode": 0,
    #     "result": {
    #         "lotSize": 0.01
    #     }
    # }
    # aiohttp.ClientSession.get = AsyncMock(return_value=MagicMock(
    #     status=200,
    #     json=AsyncMock(return_value=mock_lot_size_response)
    # ))

    # get_lot_size 호출
    lot_size = await bybit_service.get_lot_size("ETH")
    
    print(lot_size)
    
    # 결과 검증
    # assert lot_size == 0.01
    
@pytest.mark.asyncio
async def test_get_available_balance(bybit_service):
    # Bybit API의 잔액 조회 응답을 모킹합니다.
    # mock_balance_response = {
    #     "retCode": 0,
    #     "result": {
    #         "availableBalance": 1000.0
    #     }
    # }
    # aiohttp.ClientSession.get = AsyncMock(return_value=MagicMock(
    #     status=200,
    #     json=AsyncMock(return_value=mock_balance_response)
    # ))

    # get_available_balance 호출
    balance = await bybit_service.get_available_balance()
    print(balance)
    # balance = list(filter(lambda x: float(x.get('usdValue', 0)) > 1 , balance))
    # print(json.dumps(balance, indent=2))

    # 결과 검증
    # assert balance == 1000.0