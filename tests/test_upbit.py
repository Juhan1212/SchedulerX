import aiohttp
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.exchanges.upbit import UpbitExchange

@pytest.fixture
def upbit_service():
    # UpbitExchange 인스턴스를 생성합니다.
    return UpbitExchange('test_api_key', 'test_api_secret')

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
async def test_get_orderbook_success(upbit_service):
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
    orderbook = await upbit_service.get_orderbook("BTC")
    print(orderbook)

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