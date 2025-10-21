import json
import os
import time
import pytest

from backend.exchanges.bybit import BybitExchange


REQUIRED_ENV_VARS = ("BYBIT_ACCESS_KEY", "BYBIT_SECRET_KEY")


def _env_ready() -> bool:
    return all(os.getenv(k) for k in REQUIRED_ENV_VARS)


def _skip_if_env_missing():
    if not _env_ready():
        missing = [k for k in REQUIRED_ENV_VARS if not os.getenv(k)]
        pytest.skip(f"Missing Bybit credentials in environment: {', '.join(missing)}")


@pytest.fixture(scope="module")
def bybit_service():
    _skip_if_env_missing()
    return BybitExchange.from_env()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_get_tickers_e2e(bybit_service: BybitExchange):
    tickers = await bybit_service.get_tickers()
    print(len(tickers))
    assert isinstance(tickers, list)
    assert len(tickers) > 0
    # each item should be a (ticker, display_name) tuple
    sym, disp = tickers[0]
    assert isinstance(sym, str) and isinstance(disp, str)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_orderbook_e2e(bybit_service: BybitExchange):
    # Use a liquid symbol like BTC
    ob = await bybit_service.get_ticker_orderbook("BTC")
    assert isinstance(ob, dict)
    assert ob.get("ticker") == "BTC"
    assert isinstance(ob.get("timestamp"), (int, float))
    orderbook = ob.get("orderbook")
    assert isinstance(orderbook, list)
    if orderbook:  # at least one row present
        row = orderbook[0]
        for k in ("ask_price", "bid_price", "ask_size", "bid_size"):
            assert k in row


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_candles_e2e(bybit_service: BybitExchange):
    candles = await bybit_service.get_ticker_candles("BTC", interval="1m", count=50)
    assert isinstance(candles, list)
    if candles:
        c = candles[0]
        for k in ("timestamp", "open", "high", "low", "close", "volume"):
            assert k in c


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_position_info_e2e(bybit_service: BybitExchange):
    pos = await bybit_service.get_position_info("BTC")
    assert isinstance(pos, dict)
    # 'list' may be empty if no position
    _ = pos.get("list", [])
    assert isinstance(_, list)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_lot_size_e2e(bybit_service: BybitExchange):
    step = await bybit_service.get_lot_size("BTC")
    # Some symbols may not return lot size; accept None or positive float
    assert (step is None) or (isinstance(step, float) and step > 0)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_available_balance_e2e(bybit_service: BybitExchange):
    bal = await bybit_service.get_available_balance()
    assert isinstance(bal, float)
    assert bal >= 0.0


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_closed_pnl_e2e(bybit_service: BybitExchange):
    # query a recent window (last 7 days)
    # end_s = int(time.time())
    # start_s = end_s - 7 * 24 * 60 * 60
    result = await bybit_service.get_position_closed_pnl(
        "PUMPBTC"
    )
    print(json.dumps(result, indent=4))
    assert isinstance(result, dict)
    # result may contain keys like 'list' and 'nextPageCursor'
    pnl_list = result.get("list", [])
    assert isinstance(pnl_list, list)
