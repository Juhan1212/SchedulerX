import json
import asyncio
import os
import logging
import time
from celery import Celery
import redis
from dotenv import load_dotenv
from backend.core.ex_manager import exMgr

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(funcName)s - %(message)s')

load_dotenv()

logger = logging.getLogger(__name__)

# Redis 클라이언트 생성 (글로벌 네임스페이스)
redis_host = os.getenv('REDIS_HOST')
if redis_host is None:
    raise ValueError("Environment variable 'REDIS_HOST' is not set.")

redis_client = redis.StrictRedis(
    host=redis_host,
    port=6379,
    db=1,
    socket_connect_timeout=5,  # 연결 타임아웃 설정
)

# Celery 인스턴스 생성
app = Celery('consumer')
app.config_from_object('celeryconfig')

def reconnect_redis():
    global redis_client
    while True:
        try:
            if redis_host is None:
                raise ValueError("Environment variable 'REDIS_HOST' is not set.")
            
            redis_client = redis.StrictRedis(
                host=redis_host,
                port=6379,
                db=1,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            # 연결 테스트
            redis_client.ping()
            logger.info("Reconnected to Redis")
            break
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Retrying Redis connection: {e}")
            time.sleep(5)

@app.task(name='producer.calculate_orderbook_exrate_task', ignore_result=True)
def work_task(data, seed, retry_count=0):
    '''
    Celery 작업을 처리하는 함수입니다.
    Args:
        data (list): 티커 리스트
    '''
    logger.info(f"수신된 데이터 : {data}")

    try:
        res = asyncio.run(exMgr.calc_exrate_batch(data, seed))
        if res:
            redis_client.publish('exchange_rate', json.dumps(res))
            for item in res:
                redis_client.set(f"{item['ticker']}", json.dumps(item["exchange_rate"]))
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis connection error: {e}")
        if retry_count < 3:  # 무한루프 방지
            reconnect_redis()
            logger.info("작업 전체를 재시도합니다.")
            work_task(data, seed, retry_count + 1)
        else:
            logger.error("최대 재시도 횟수 초과. 작업을 중단합니다.")
            return

    logger.info("작업이 성공적으로 완료되었습니다.")
    
if __name__ == "__main__":
    app.worker_main()
    