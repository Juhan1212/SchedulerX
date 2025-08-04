import os
from contextlib import contextmanager
import asyncio
from pathlib import Path
import sqlite3
import logging
import logging.config
import time
import dotenv
from celery import Celery, group
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from pytz import timezone
import yaml  # 추가
from backend.core.ex_manager import exMgr
from backend.exchanges.base import Exchange
from backend.exchanges.bybit import BybitExchange
from backend.exchanges.gateio import GateioExchange
from backend.exchanges.upbit import UpbitExchange

# 환경 변수 로드
dotenv.load_dotenv()

# YAML 파일 경로
LOGGING_CONFIG_PATH = Path(__file__).resolve().parent / "celery_logging_config.yaml"

# YAML 파일에서 로깅 설정 로드
def setup_logging():
    """
    YAML 파일에서 로깅 설정을 로드합니다.

    Args:
        None

    Returns:
        None

    Raises:
        FileNotFoundError: YAML 파일이 존재하지 않을 경우.
        yaml.YAMLError: YAML 파일 파싱 중 오류가 발생한 경우.
    """
    try:
        with open(LOGGING_CONFIG_PATH, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
            logging.config.dictConfig(config)
    except FileNotFoundError as fnf_error:
        print(f"Logging config file not found: {fnf_error}")
        logging.basicConfig(level=logging.INFO)
    except yaml.YAMLError as yaml_error:
        print(f"Error parsing YAML logging config: {yaml_error}")
        logging.basicConfig(level=logging.INFO)

# 로깅 설정 초기화
setup_logging()

# 로거 생성
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
    
    try:
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
    except sqlite3.Error as e:
        logger.error(f"DB 에러: {e}")
        return []

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
    Celery publish를 asyncio loop의 run_in_executor로 비동기 실행하여
    스케줄러 스레드풀 block을 방지합니다.
    upbit/bybit, upbit/gateio 조합 모두에 대해 작업을 생성합니다.
    """
    try:
        exchange_pairs = [
            ("upbit", "bybit"),
            ("upbit", "gateio"),
        ]
        batch_size = 10
        seed = get_admin_seed_money()

        async def async_publish():
            total_tasks = 0
            loop = asyncio.get_running_loop()
            
            for ex1, ex2 in exchange_pairs:
                tickers = get_common_tickers((exMgr.exchanges[ex1], exMgr.exchanges[ex2]))
                logger.debug(f"공통 진입가능 티커 ({ex1}, {ex2}): {tickers}")
                
                if not tickers:
                    logger.info(f"공통 진입가능 티커가 없습니다: {ex1}, {ex2}")
                    continue
                
                tasks = []
                for i in range(0, len(tickers), batch_size):
                    batch = tickers[i:i + batch_size]
                    tasks.append(calculate_orderbook_exrate_task.s(batch, seed, ex1, ex2))
                    
                total = len(tasks)
                total_tasks += total
                if tasks:
                    # Celery publish를 thread executor에 위임
                    loop.run_in_executor(None, lambda: group(tasks).apply_async(retry=False, expires=5))
            logger.info(f"{total_tasks}개 tasks를 publish to celery broker")

        asyncio.run(async_publish())
        logger.info("스케줄러 작업이 성공적으로 실행되었습니다.")
    except Exception as e:
        logger.error(f"스케줄러 작업 중 오류 발생: {e}")


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
    
    executors = {
        'default': ThreadPoolExecutor(2),  # 기본 스레드 풀
    }
    
    # 스케줄러 설정
    kst = timezone('Asia/Seoul')  # 한국 시간대 설정
    scheduler = BlockingScheduler(executors=executors, timezone=kst, job_defaults={
        'coalesce': True,  # 중복된 작업을 하나로 합침
        'misfire_grace_time': 10,  # 작업이 지연되었을 때 최대 10초까지 기다림
        'max_instances': 2,  # 동시에 실행되는 작업의 최대 인스턴스 수
    })
    scheduler.add_job(renew_tickers_task, 'cron', minute='*/5')  # 5분마다 실행
    scheduler.add_job(schedule_workers_task, 'interval', seconds=5)  # 10초마다 작업 스케줄링
    scheduler.start()