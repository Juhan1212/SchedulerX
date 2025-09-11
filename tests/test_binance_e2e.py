import pytest
from backend.exchanges.binance import BinanceExchange

@pytest.mark.asyncio
async def test_e2e_get_tickers():
    try:
        tickers = await BinanceExchange.get_tickers()
    except Exception as e:
        pytest.skip(f"실제 API 호출 실패: {e}")
        
    print(tickers)
    assert isinstance(tickers, list)
    assert "BTC" in tickers

@pytest.mark.asyncio
async def test_e2e_get_ticker_orderbook():
    bex = BinanceExchange()
    try:
        ob = await bex.get_ticker_orderbook("BTC")
    except Exception as e:
        pytest.skip(f"실제 API 호출 실패: {e}")
        
    print(ob)
    assert ob["ticker"] == "BTC"
    assert len(ob["orderbook"]) > 0

@pytest.mark.asyncio
async def test_e2e_get_ticker_candles():
    bex = BinanceExchange()
    try:
        candles = await bex.get_ticker_candles("BTC")
    except Exception as e:
        pytest.skip(f"실제 API 호출 실패: {e}")
        
    print(candles)
    assert isinstance(candles, list)
    assert "open" in candles[0]
    assert "close" in candles[0]
