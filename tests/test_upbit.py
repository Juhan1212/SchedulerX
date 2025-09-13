import json
import os
import aiohttp
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.exchanges.upbit import UpbitExchange

@pytest.fixture
def upbit_service():
    # UpbitExchange 인스턴스를 생성합니다.
    api_key = os.getenv("UPBIT_ACCESS_KEY")
    secret_key = os.getenv("UPBIT_SECRET_KEY")
    if not api_key or not secret_key:
        raise ValueError("UPBIT_ACCESS_KEY and UPBIT_SECRET_KEY must be set in environment variables.")
    return UpbitExchange(api_key, secret_key)

@pytest.mark.asyncio
async def test_get_tickers_success(upbit_service):
    # Upbit API의 성공적인 응답을 모킹합니다.
    # mock_response = [
    #     {"market": "KRW-BTC"},
    #     {"market": "KRW-ETH"},
    #     {"market": "BTC-USD"}
    # ]
    # aiohttp.ClientSession.get = AsyncMock(return_value=MagicMock(
    #     status=200,
    #     json=AsyncMock(return_value=mock_response)
    # ))

    # get_tickers 호출
    tickers = await upbit_service.get_tickers()
    print(tickers)

    # 결과 검증
    # assert tickers == ["BTC", "ETH"]

@pytest.mark.asyncio
async def test_get_tickers_failure(upbit_service):
    # Upbit API의 실패 응답을 모킹합니다.
    aiohttp.ClientSession.get = AsyncMock(return_value=MagicMock(
        status=500,
        text=AsyncMock(return_value="Internal Server Error")
    ))

    # get_tickers 호출 및 예외 검증
    with pytest.raises(Exception, match="Upbit API Error: 500 - Internal Server Error"):
        await upbit_service.get_tickers()

@pytest.mark.asyncio
async def test_get_depo_with_pos_tickers_success(upbit_service):
    # Upbit API의 성공적인 응답을 모킹합니다.
    mock_response = [
        {"currency": "BTC", "wallet_state": "working"},
        {"currency": "ETH", "wallet_state": "working"},
        {"currency": "XRP", "wallet_state": "disabled"}
    ]
    aiohttp.ClientSession.get = AsyncMock(return_value=MagicMock(
        status=200,
        json=AsyncMock(return_value=mock_response)
    ))

    # get_depo_with_pos_tickers 호출
    tickers = await upbit_service.get_depo_with_pos_tickers()

    # 결과 검증
    assert tickers == ["BTC", "ETH"]

@pytest.mark.asyncio
async def test_get_depo_with_pos_tickers_failure(upbit_service):
    # Upbit API의 실패 응답을 모킹합니다.
    aiohttp.ClientSession.get = AsyncMock(return_value=MagicMock(
        status=403,
        text=AsyncMock(return_value="Forbidden")
    ))

    # get_depo_with_pos_tickers 호출 및 예외 검증
    with pytest.raises(Exception, match="Upbit API Error: 403 - Forbidden"):
        await upbit_service.get_depo_with_pos_tickers()

@pytest.mark.asyncio
async def test_get_ticker_orderbook_success():
    # Upbit API의 성공적인 응답을 모킹합니다.
    # mock_response = {
    #     "orderbook_units": [
    #         {"ask_price": 30000000.0, "bid_price": 29900000.0, "ask_size": 1.0, "bid_size": 1.5},
    #         {"ask_price": 29950000.0, "bid_price": 29900000.0, "ask_size": 0.5, "bid_size": 2.0}
    #     ]
    # }
    # aiohttp.ClientSession.get = AsyncMock(return_value=MagicMock(
    #     status=200,
    #     json=AsyncMock(return_value=mock_response)
    # ))

    # get_orderbook 호출
    orderbook = await UpbitExchange.get_ticker_orderbook(['BTC', 'ETH'])
    print(json.dumps(orderbook, indent=2))

    # 결과 검증
    # assert len(orderbook["orderbook_units"]) == 2
    # assert orderbook["orderbook_units"][0]["ask_price"] == 30000000.0
    # assert orderbook["orderbook_units"][1]["bid_price"] == 29900000.0

@pytest.mark.asyncio
async def test_get_orderbook_failure(upbit_service):
    # Upbit API의 실패 응답을 모킹합니다.
    aiohttp.ClientSession.get = AsyncMock(return_value=MagicMock(
        status=404,
        text=AsyncMock(return_value="Not Found")
    ))

    # get_orderbook 호출 및 예외 검증
    with pytest.raises(Exception, match="Upbit API Error: 404 - Not Found"):
        await upbit_service.get_orderbook("BTC")
    # assert len(ticker_info) == 2
    # assert ticker_info[0]["market"] == "KRW-BTC"
    # assert ticker_info[1]["market"] == "KRW-ETH"
    

@pytest.mark.asyncio
async def test_get_ticker_price_success(upbit_service):
    # Upbit API의 성공적인 티커 가격 응답을 모킹합니다.
    # mock_response = {"market": "KRW-BTC", "trade_price": 50000000.0}
    # aiohttp.ClientSession.get = AsyncMock(return_value=MagicMock(
    #     status=200,
    #     json=AsyncMock(return_value=mock_response)
    # ))

    # get_ticker_price 호출
    ticker_price = await upbit_service.get_ticker_price("USDT")
    print(ticker_price)

    # 결과 검증
    # assert ticker_price == {"ticker": "BTC", "price": 50000000.0}
    
@pytest.mark.asyncio
async def test_order(upbit_service):    
    # Upbit API의 주문 성공 응답을 모킹합니다.
    # mock_order_response = {
    #     "uuid": "12345678-1234-1234-1234-123456789012",
    #     "side": "bid",
    #     "price": 50000000.0,
    #     "state": "done",
    #     "created_at": "2023-01-01T00:00:00Z"
    # }
    # aiohttp.ClientSession.post = AsyncMock(return_value=MagicMock(
    #     status=201,
    #     json=AsyncMock(return_value=mock_order_response)
    # ))

    # order 호출
    await upbit_service.order("XRP", "bid", 10000)
    orders = await upbit_service.get_orders("XRP")
    print(json.dumps(orders, indent=2))

    # 결과 검증
    # assert order_result["uuid"] == "12345678-1234-1234-1234-123456789012"
    
@pytest.mark.asyncio
async def test_get_orders(upbit_service):
    # Upbit API의 주문 목록 응답을 모킹합니다.
    # mock_orders_response = [
    #     {"uuid": "12345678-1234-1234-1234-123456789012", "side": "bid", "price": 50000000.0, "state": "done"},
    #     {"uuid": "87654321-4321-4321-4321-210987654321", "side": "ask", "price": 51000000.0, "state": "cancelled"}
    # ]
    # aiohttp.ClientSession.get = AsyncMock(return_value=MagicMock(
    #     status=200,
    #     json=AsyncMock(return_value=mock_orders_response)
    # ))

    # get_orders 호출
    orders = await upbit_service.get_orders("XRP")
    print(json.dumps(orders, indent=2))

    # 결과 검증
    # assert len(orders) == 2
    # assert orders[0]["uuid"] == "12345678-1234-1234-1234-123456789012"
    