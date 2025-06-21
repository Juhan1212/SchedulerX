import asyncio
import sqlite3
import logging
from celery import Celery, group
from apscheduler.schedulers.blocking import BlockingScheduler
from app.core.ex_manager import exMgr
from app.exchanges.bybit import BybitExchange
from app.exchanges.upbit import UpbitExchange

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(funcName)s - %(message)s')
logger = logging.getLogger(__name__)

# Celery 인스턴스 생성
app = Celery('producer')
app.config_from_object('celeryconfig')

# 데이터베이스 초기화
def initialize_db():
    """
    데이터베이스와 테이블을 초기화합니다.
    이 함수는 데이터베이스 파일이 없으면 생성하고,
    tickers 테이블을 생성합니다.
    """
    conn = sqlite3.connect("tickers.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exchange TEXT NOT NULL,
            ticker TEXT NOT NULL,
            dw_pos_yn INTEGER DEFAULT 0, -- 입출금 가능 여부 (1: 가능, 0: 불가능)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(id, exchange, ticker)
        )
    """)
    
    # Create the seed table if it does not exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amt INTERGER DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()
    
def upsert_seed_money(amount: int):
    """
    seed 테이블에 초기 자본금을 삽입합니다.
    이미 데이터가 존재하면 업데이트합니다.
    """
    conn = sqlite3.connect("tickers.db")
    cursor = conn.cursor()
    
    # INSERT OR REPLACE로 seed 테이블에 자본금 삽입
    cursor.execute("""
        INSERT INTO seed (amt) VALUES (?)
        ON CONFLICT(id) DO UPDATE SET amt = ?
    """, (amount, amount))
    
    conn.commit()
    conn.close()
    
async def insert_tickers(exchange):
    """
    데이터베이스에 티커를 삽입합니다.
    """
    conn = sqlite3.connect("tickers.db")
    cursor = conn.cursor()
    
    tickers = await exMgr.exchanges[exchange].get_tickers()
    
    # DELETE 기존 데이터
    cursor.execute("DELETE FROM tickers WHERE exchange = ?", (exchange,))

    # INSERT 새로운 데이터 (한꺼번에)
    cursor.executemany(
        "INSERT INTO tickers (exchange, ticker) VALUES (?, ?)",
        [(exchange, ticker) for ticker in tickers]
    )
    
    conn.commit()
    conn.close()

def get_common_tickers(exchanges: tuple[UpbitExchange, BybitExchange]) -> list[str]:
    """
    db에서 공통 진입가능 티커를 반환합니다.
    """
    if len(exchanges) != 2:
        raise ValueError("공통 진입가능 티커는 2개의 거래소가 필요합니다.")
    
    if not isinstance(exchanges[0], UpbitExchange):
        raise TypeError("첫 번째 거래소는 UpbitExchange 타입이어야 합니다.")
    
    if not isinstance(exchanges[1], BybitExchange):
        raise TypeError("두 번째 거래소는 BybitExchange 타입이어야 합니다.")
    
    conn = sqlite3.connect("tickers.db")
    cursor = conn.cursor()

    # 교집합 쿼리 실행
    exchange1 = exchanges[0].name
    exchange2 = exchanges[1].name

    query = """
        SELECT t1.ticker
        FROM tickers t1
        INNER JOIN tickers t2
        ON t1.ticker = t2.ticker
        WHERE t1.exchange = ? AND t2.exchange = ?
        AND t1.dw_pos_yn = 1
        AND t1.ticker NOT IN ('USDT');
    """

    cursor.execute(query, (exchange1, exchange2))
    intersection_tickers = [row[0] for row in cursor.fetchall()]

    conn.close()
    return intersection_tickers

async def renew_tickers():
    """
    티커 정보를 갱신합니다.
    """
    # Bybit 티커 삽입
    await insert_tickers("bybit")

    # Upbit 티커 삽입
    await insert_tickers("upbit")

    conn = sqlite3.connect("tickers.db")
    cursor = conn.cursor()
    
    dep_with_pos_tickers = await UpbitExchange().get_depo_with_pos_tickers()
    
    cursor.executemany(
        "UPDATE tickers SET dw_pos_yn = ? WHERE exchange = ? AND ticker = ?",
        [(1, "upbit", ticker) for ticker in dep_with_pos_tickers]
    )

    conn.commit()
    conn.close()
    
@app.task
def calculate_orderbook_exrate_task(tickers: list[str], seed: int):
    """
    worker가 tickers를 받아서 환율을 계산하는 작업입니다.
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
    """
    tickers = get_common_tickers((exMgr.exchanges["upbit"], exMgr.exchanges["bybit"]))
    
    logger.debug(f"공통 진입가능 티커: {tickers}")
    
    if not tickers:
        logger.info("공통 진입가능 티커가 없습니다.")
        return
    
    # batch_size = 10
    # tasks = []
    # seed = get_seed_money()
    # for i in range(0, len(tickers), batch_size):
    #     batch = tickers[i:i + batch_size]
    #     tasks.append(calculate_orderbook_exrate.s(batch, seed))
    # logger.info(f"스케줄링된 작업 수: {len(tasks)}")
    # group(tasks).apply_async()
    # logger.info("작업이 SQS에 전달되었습니다.")
    seed = get_seed_money()
    logger.info(seed)
    calculate_orderbook_exrate_task.apply_async(args=(['BTC', 'ETH'], seed))


def get_seed_money():
    """Retrieve the first row from the seed table."""
    conn = sqlite3.connect("tickers.db")
    cursor = conn.cursor()

    cursor.execute("SELECT amt FROM seed ORDER BY id ASC LIMIT 1")
    result = cursor.fetchone()

    conn.close()

    return result[0] if result else None


if __name__ == "__main__":
    exMgr.register_exchange("bybit", BybitExchange())
    exMgr.register_exchange("upbit", UpbitExchange())
    
    # 데이터베이스 초기화
    initialize_db()
    
    # 초기 자본금 설정
    upsert_seed_money(1_000_000)
    
    # 초기 티커 갱신
    renew_tickers_task() 
    
    # 스케줄러 설정
    scheduler = BlockingScheduler()
    scheduler.add_job(renew_tickers_task, 'cron', minute='*/5')  # 5분마다 실행
    scheduler.add_job(schedule_workers_task, 'cron', minute='*/1')  # 매분마다 작업 스케줄링
    scheduler.start()
    
