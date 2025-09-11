
import pytest
from backend.exchanges.binance import BinanceExchange
from binance.exceptions import BinanceAPIException
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_get_tickers_success():
    dummy_client = AsyncMock()
    dummy_client.get_all_tickers.return_value = [
        {"symbol": "BTCUSDT"},
        {"symbol": "ETHUSDT"},
        {"symbol": "XRPBTC"}
    ]
    dummy_client.close_connection.return_value = None
    with patch("backend.exchanges.binance.AsyncClient.create", new=AsyncMock(return_value=dummy_client)):
        tickers = await BinanceExchange.get_tickers()
        assert "BTC" in tickers and "ETH" in tickers and "XRPBTC" not in tickers

@pytest.mark.asyncio
async def test_get_ticker_orderbook_success():
    dummy_client = AsyncMock()
    dummy_client.get_order_book.return_value = {
        "lastUpdateId": 123,
        "asks": [["50100", "1.0"]],
        "bids": [["50000", "2.0"]]
    }
    dummy_client.close_connection.return_value = None
    
    with patch("backend.exchanges.binance.AsyncClient.create", new=AsyncMock(return_value=dummy_client)):
        bex = BinanceExchange()
        ob = await bex.get_ticker_orderbook("BTC")
        assert ob["ticker"] == "BTC"
        assert ob["orderbook"][0]["ask_price"] == 50100.0
        assert ob["orderbook"][0]["bid_size"] == 2.0

@pytest.mark.asyncio
async def test_get_ticker_candles_success():
    dummy_client = AsyncMock()
    dummy_client.get_klines.return_value = [[1620000000000, "100", "110", "90", "105", "1000"]]
    dummy_client.close_connection.return_value = None

    with patch("backend.exchanges.binance.AsyncClient.create", new=AsyncMock(return_value=dummy_client)):
        bex = BinanceExchange()
        candles = await bex.get_ticker_candles("BTC")
        assert candles[0]["open"] == 100.0
        assert candles[0]["close"] == 105.0
