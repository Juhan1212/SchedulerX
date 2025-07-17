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
    db=0,
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
                db=0,
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
def work_task(data, seed):
    '''
    Celery 작업을 처리하는 함수입니다.
    Args:
        data (list): 티커 리스트
    '''
    logger.info(f"수신된 데이터 : {data}")
    
    tasks = [exMgr.calc_exrate(ticker, seed) for ticker in data]
    res = asyncio.gather(*tasks)
    
    if res:
        try:
            # res 전체를 JSON 문자열로 변환하여 한 번에 publish
            redis_client.publish('exchange_rate', json.dumps(res))
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis connection error: {e}")
            reconnect_redis()
            redis_client.publish('exchange_rate', json.dumps(res))

    logger.info("작업이 성공적으로 완료되었습니다.")
    
if __name__ == "__main__":
    app.worker_main()
    