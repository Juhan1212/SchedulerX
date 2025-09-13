import asyncio
from pathlib import Path
import logging
import logging.config
import dotenv
from celery import Celery, group
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from pytz import timezone
import yaml  # 추가
from backend.core.ex_manager import ExchangeManager, exMgr
from backend.exchanges.bithumb import BithumbExchange
from backend.exchanges.bybit import BybitExchange
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

@app.task
def calculate_orderbook_exrate_task(tickers: list[tuple]):
    """
    worker가 tickers를 받아서 환율을 계산하는 작업입니다.
    consumer.py에서 이 작업을 구현하고 실행합니다.
    Args:
        tickers (list[tuple]): (upbit, bybit, coin_symbol) 형식의 튜플 리스트
    """
    pass

def renew_tickers_job(exMgr: ExchangeManager):
    """
    스케줄러가 티커 정보를 갱신합니다.
    """
    asyncio.run(exMgr.upsert_tickers())
    logger.info("티커 정보가 갱신되었습니다.")

def celery_worker_job():
    """
    스케줄러가 worker 작업을 스케줄링합니다.
    Celery publish를 asyncio loop의 run_in_executor로 비동기 실행하여
    스케줄러 스레드풀 block을 방지합니다.
    """
    try:
        batch_size = 10

        async def async_publish():
            total_tasks = 0
            loop = asyncio.get_running_loop()
            
            tickers = exMgr.get_common_tickers_from_db()
            
            if not tickers:
                logger.info(f"공통 진입가능 티커가 없습니다")
                return

            tasks = []
            for i in range(0, len(tickers), batch_size):
                batch = tickers[i:i + batch_size]
                tasks.append(calculate_orderbook_exrate_task.s(batch))

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


if __name__ == "__main__":
    # facade exMgr 객체에 거래소 등록
    exMgr.register_exchange("upbit", UpbitExchange.from_env())
    exMgr.register_exchange("bybit", BybitExchange.from_env())
    exMgr.register_exchange("bithumb", BithumbExchange.from_env())

    # 초기 티커 갱신
    renew_tickers_job(exMgr) 
    
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
    scheduler.add_job(renew_tickers_job, 'cron', minute='*/5', args=[exMgr])  # 5분마다 실행
    scheduler.add_job(celery_worker_job, 'interval', seconds=5)  # 10초마다 작업 스케줄링
    scheduler.start()