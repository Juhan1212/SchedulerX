import os
import dotenv
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from backend.exchanges.bithumb import BithumbExchange
from backend.exchanges.bybit import BybitExchange
from backend.exchanges.upbit import UpbitExchange
from backend.core.ex_manager import exMgr
import scheduler
from dotenv import load_dotenv

load_dotenv()

def test_renew_tickers():
    scheduler.exMgr = exMgr
    exMgr.register_exchange("upbit", UpbitExchange.from_env())
    exMgr.register_exchange("bybit", BybitExchange.from_env())
    exMgr.register_exchange("bithumb", BithumbExchange.from_env())
    scheduler.renew_tickers_job(exMgr)

@pytest.mark.asyncio
@patch("scheduler.get_db_cursor")
@patch("scheduler.exMgr")
@patch("scheduler.logger")
async def test_upsert_tickers_success(mock_logger, mock_exMgr, mock_get_db_cursor):
    # Setup mocks
    mock_cursor = MagicMock()
    mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
    mock_exMgr.exchanges = {
        "bybit": MagicMock(get_tickers=AsyncMock(return_value=[("BTC", "Bitcoin"), ("ETH", "Ethereum")]))
    }
    mock_cursor.fetchone.return_value = [1]

    await upsert_tickers("bybit")

    mock_cursor.execute.assert_called_once_with("SELECT id FROM exchanges WHERE eng_name = %s", ("bybit",))
    mock_cursor.executemany.assert_called_once_with(
        "INSERT INTO coins_exchanges (exchange_id, coin_symbol, display_name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        [(1, "BTC", "Bitcoin"), (1, "ETH", "Ethereum")]
    )
    mock_logger.error.assert_not_called()

@pytest.mark.asyncio
@patch("scheduler.get_db_cursor")
@patch("scheduler.exMgr")
@patch("scheduler.logger")
async def test_upsert_tickers_exchange_id_not_found(mock_logger, mock_exMgr, mock_get_db_cursor):
    mock_cursor = MagicMock()
    mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
    mock_exMgr.exchanges = {
        "bybit": MagicMock(get_tickers=AsyncMock(return_value=[("BTC", "Bitcoin")]))
    }
    mock_cursor.fetchone.return_value = None

    await upsert_tickers("bybit")

    mock_logger.error.assert_called_once_with("Exchange id not found for bybit")
    mock_cursor.executemany.assert_not_called()

@pytest.mark.asyncio
@patch("scheduler.get_db_cursor")
@patch("scheduler.exMgr")
@patch("scheduler.logger")
async def test_upsert_tickers_no_tickers(mock_logger, mock_exMgr, mock_get_db_cursor):
    mock_cursor = MagicMock()
    mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
    mock_exMgr.exchanges = {
        "bybit": MagicMock(get_tickers=AsyncMock(return_value=[]))
    }
    mock_cursor.fetchone.return_value = [1]

    await upsert_tickers("bybit")

    mock_cursor.executemany.assert_called_once_with(
        "INSERT INTO coins_exchanges (exchange_id, coin_symbol, display_name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        []
    )
    mock_logger.error.assert_not_called()