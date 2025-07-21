import os
from contextlib import contextmanager
import asyncio
import sqlite3
import logging
import dotenv
from celery import Celery, group
from apscheduler.schedulers.blocking import BlockingScheduler
from pytz import timezone  # 추가
from backend.core.ex_manager import exMgr
from backend.exchanges.base import Exchange
from backend.exchanges.bybit import BybitExchange
from backend.exchanges.gateio import GateioExchange
from backend.exchanges.upbit import UpbitExchange

# 환경 변수 로드
dotenv.load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(funcName)s - %(message)s')
logger = logging.getLogger(__name__)

# Celery 인스턴스 생성
app = Celery('producer')
app.config_from_object('celeryconfig')

@contextmanager
def get_db_cursor(db_path="app.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    finally:
        conn.close()

async def upsert_tickers(exchange):
    """
    데이터베이스에 티커를 삽입합니다.
    """
    with get_db_cursor() as cursor:
        tickers = await exMgr.exchanges[exchange].get_tickers()
        cursor.executemany(
            "INSERT OR IGNORE INTO tickers (exchange, name) VALUES (?, ?)",
            [(exchange, ticker) for ticker in tickers]
        )

def get_common_tickers(exchanges: tuple[Exchange, Exchange]) -> list[str]:
    """
    db에서 공통 진입가능 티커를 반환합니다.
    """
    if len(exchanges) != 2:
        raise ValueError("공통 진입가능 티커는 2개의 거래소가 필요합니다.")
    
    with get_db_cursor() as cursor:
        exchange1 = exchanges[0].name
        exchange2 = exchanges[1].name
        query = """
            SELECT t1.name
            FROM tickers t1
            INNER JOIN tickers t2
            ON t1.name = t2.name
            WHERE t1.exchange = ? AND t2.exchange = ?
            AND t1.dw_pos_yn = 1
            AND t1.name != 'USDT'
        """
        cursor.execute(query, (exchange1, exchange2))
        intersection_tickers = [row[0] for row in cursor.fetchall()]
        return intersection_tickers

async def renew_tickers():
    """
    티커 정보를 갱신합니다.
    """
    await asyncio.gather(
        *(upsert_tickers(exchange) for exchange in list(exMgr.exchanges.keys()))
    )
    with get_db_cursor() as cursor:
        dep_with_pos_tickers = await exMgr.exchanges["upbit"].get_depo_with_pos_tickers()
        cursor.executemany(
            "UPDATE tickers SET dw_pos_yn = ? WHERE exchange = ? AND name = ?",
            [(1, "upbit", ticker) for ticker in dep_with_pos_tickers]
        )

@app.task
def calculate_orderbook_exrate_task(tickers: list[str], seed: int, exchange1: str, exchange2: str):
    """
    worker가 tickers를 받아서 환율을 계산하는 작업입니다.
    consumer.py에서 이 작업을 구현하고 실행합니다.
    Args:
        tickers (list): 티커 리스트
        seed (int): 시드 금액
        exchange1 (str): 첫 번째 거래소 이름
        exchange2 (str): 두 번째 거래소 이름
    """
    pass

def renew_tickers_task():
    """
    스케줄러가 티커 정보를 갱신합니다.
    """
    asyncio.run(renew_tickers())
    logger.info("티커 정보가 갱신되었습니다.")



def schedule_workers_task():
    """
    스케줄러가 worker 작업을 스케줄링합니다.
    upbit/bybit, upbit/gateio 조합 모두에 대해 작업을 생성합니다.
    """
    exchange_pairs = [
        ("upbit", "bybit"),
        ("upbit", "gateio"),
    ]
    batch_size = 10
    seed = get_admin_seed_money()
    for ex1, ex2 in exchange_pairs:
        total_tasks = 0
        tickers = get_common_tickers((exMgr.exchanges[ex1], exMgr.exchanges[ex2]))
        logger.debug(f"공통 진입가능 티커 ({ex1}, {ex2}): {tickers}")
        if not tickers:
            logger.info(f"공통 진입가능 티커가 없습니다: {ex1}, {ex2}")
            continue
        tasks = []
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            tasks.append(calculate_orderbook_exrate_task.s(batch, seed, ex1, ex2))
        total_tasks += len(tasks)
        if tasks:
            group(tasks).apply_async()
        logger.info(f"스케줄링된 작업 수: {total_tasks}")
    logger.info("작업이 브로커에 전달되었습니다.")


def get_admin_seed_money():
    """Retrieve amt from seed for user.email = 'admin@test.com'."""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT s.amt
            FROM seed s
            JOIN users u ON s.user_id = u.id
            WHERE u.email = ?
            LIMIT 1
        """, ("admin@test.com",))
        result = cursor.fetchone()
        return result[0] if result else None


if __name__ == "__main__":
    upbit_access_key = os.getenv("UPBIT_ACCESS_KEY")
    upbit_secret_key = os.getenv("UPBIT_SECRET_KEY")
    bybit_api_key = os.getenv("BYBIT_ACCESS_KEY")
    bybit_secret_key = os.getenv("BYBIT_SECRET_KEY")
    gateio_api_key = os.getenv("GATEIO_API_KEY")
    gateio_secret_key = os.getenv("GATEIO_SECRET_KEY")
    
    if not upbit_access_key or not upbit_secret_key:
        raise ValueError("UPBIT_ACCESS_KEY and UPBIT_SECRET_KEY must be set in environment variables.")
    if not bybit_api_key or not bybit_secret_key:
        raise ValueError("BYBIT_ACCESS_KEY and BYBIT_SECRET_KEY must be set in environment variables.")
    if not gateio_api_key or not gateio_secret_key:
        raise ValueError("GATEIO_API_KEY and GATEIO_SECRET_KEY must be set in environment variables.")

    exMgr.register_exchange("bybit", BybitExchange(bybit_api_key, bybit_secret_key))
    exMgr.register_exchange("upbit", UpbitExchange(upbit_access_key, upbit_secret_key))
    exMgr.register_exchange("gateio", GateioExchange(gateio_api_key, gateio_secret_key))

    # 초기 티커 갱신
    renew_tickers_task() 
    
    # 스케줄러 설정
    kst = timezone('Asia/Seoul')  # 한국 시간대 설정
    scheduler = BlockingScheduler(timezone=kst)
    scheduler.add_job(renew_tickers_task, 'cron', minute='*/5')  # 5분마다 실행
    scheduler.add_job(schedule_workers_task, 'interval', seconds=5)  # 5초마다 작업 스케줄링
    scheduler.start()
