import json
import pytest
import types
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from backend.core.ex_manager import ExchangeManager
from backend.core.ex_manager import exMgr

@pytest.fixture
def ex_manager():
    return ExchangeManager()

@pytest.fixture
def tickers():
    return [('bithumb', 'bybit', 'MANTA')]

def test_register_exchange(ex_manager):
    dummy_exchange = object()
    ex_manager.register_exchange("test", dummy_exchange)
    assert ex_manager.exchanges["test"] is dummy_exchange

def test_get_common_tickers_from_db(ex_manager):
    result = ex_manager.get_common_tickers_from_db()
    print(result)

@pytest.mark.asyncio
async def test_calc_exrate_batch(ex_manager, tickers):
    result = await ex_manager.calc_exrate_batch(tickers)
    # with open('test_calc_exrate_batch_output.json', 'w') as f:
    #     json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))