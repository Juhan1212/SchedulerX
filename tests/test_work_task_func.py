import pytest
from unittest.mock import patch
from consumer import work_task

@pytest.fixture
def mock_get_usdt_ticker_ob_price():
    with patch("consumer.get_usdt_ticker_ob_price", return_value={'price': 1400}):
        yield

@pytest.fixture
def mock_calc_exrate_batch():
    with patch("backend.core.ex_manager.exMgr.calc_exrate_batch", return_value=[{'name': 'XRP', 'ex_rate': 1350}]):
        yield

@pytest.fixture
def mock_redis_publish():
    with patch("consumer.redis_client.publish", return_value=None):
        yield

def test_work_task_order(caplog, monkeypatch, mock_get_usdt_ticker_ob_price, mock_calc_exrate_batch, mock_redis_publish):
    # 실제 주문 함수들은 mock하지 않음
    data = ['XRP']
    seed = 10000
    exchange1 = 'upbit'
    exchange2 = 'bybit'
    with caplog.at_level("INFO", logger="consumer"):
        work_task(data, seed, exchange1, exchange2)
    print(caplog.text)

