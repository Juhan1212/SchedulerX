from decimal import ROUND_DOWN, Decimal
import json
import math
from pathlib import Path
from cachetools import TTLCache, cached
import asyncio
import os
import logging
import logging.config
import time
from typing import List
from celery import Celery
import redis
from dotenv import load_dotenv
import yaml
from backend.core.ex_manager import exMgr
from backend.exchanges.bybit import BybitExchange
from backend.exchanges.upbit import UpbitExchange

load_dotenv()

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

# Redis 재연결 함수
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

# Celery 인스턴스 생성
app = Celery('consumer')
app.config_from_object('celeryconfig')

# 테더 가격 호출 api 캐시설정            
usdt_cache = TTLCache(maxsize=10, ttl=1)

@cached(usdt_cache)
def get_usdt_ticker_ob_price():
    return asyncio.run(UpbitExchange.get_ticker_ob_price('USDT'))

@app.task(name='producer.calculate_orderbook_exrate_task', ignore_result=True, soft_time_limit=5)
def work_task(data, seed, exchange1, exchange2, retry_count=0):
    '''
    Celery 작업을 처리하는 함수입니다.
    Args:
        data (list): 티커 리스트
        exchange1 (str): 첫 번째 거래소 이름
        exchange2 (str): 두 번째 거래소 이름
    '''
    logger.debug(f"수신된 데이터 : {data}, {exchange1}, {exchange2}")

    try:
        # 테더 가격 1초 캐시 적용되어있음.
        usdt = get_usdt_ticker_ob_price() 
        usdt_price = usdt.get('price', 0)
        if usdt_price == 0:
            raise ValueError("테더 가격이 0입니다. API 호출이 실패했을 수 있습니다.")
        
        res = asyncio.run(exMgr.calc_exrate_batch(data, seed, exchange1, exchange2))
        if res:
            # 거래소 조합별로 키를 구분하여 저장
            for item in res:
                redis_key = f"{exchange1}_{exchange2}:{item['name']}"
                redis_client.set(redis_key, json.dumps(item["ex_rate"]))

                if item['ex_rate'] < usdt_price * 0.995: # USDT 가격의 99.5% 이하인 경우
                    if exchange2 == 'bybit':
                        bybit_api_key = os.getenv('BYBIT_ACCESS_KEY')
                        bybit_secret_key = os.getenv('BYBIT_SECRET_KEY')
                        if not bybit_api_key or not bybit_secret_key:
                            raise ValueError("BYBIT_ACCESS_KEY and BYBIT_SECRET_KEY must be set in environment variables.")
                        bybit_service = BybitExchange(bybit_api_key, bybit_secret_key)

                        # 포지션 유무 확인
                        res = asyncio.run(bybit_service.get_position_info(item['name']))
                        position = list(filter(lambda x: float(x.get('size', 0)) > 0, res.get('list', [])))

                        if len(position) > 0:
                            # 포지션이 있는 경우, skip
                            logger.info(f"포지션이 존재하여 작업을 건너뜁니다: {item['name']}")
                            continue
                        else:
                            # 포지션이 없는 경우, upbit에서 KRW로 매수 후 체결된 volume만큼 bybit에서 매도
                            upbit_api_key = os.getenv('UPBIT_ACCESS_KEY')
                            upbit_secret_key = os.getenv('UPBIT_SECRET_KEY')
                            if not upbit_api_key or not upbit_secret_key:
                                raise ValueError("UPBIT_ACCESS_KEY and UPBIT_SECRET_KEY must be set in environment variables.")
                            upbit_service = UpbitExchange(upbit_api_key, upbit_secret_key)

                            # Upbit에서 KRW로 매수 주문 실행
                            upbit_order = asyncio.run(upbit_service.order(item['name'], 'bid', seed))
                            upbit_order_id = upbit_order.get('uuid')
                            logger.info(f"Upbit 주문 ID: {upbit_order_id}")
                            if not upbit_order_id:
                                logger.error(f"Upbit 주문 실행 실패: {upbit_order}")
                                return None

                            # Upbit 주문내역 조회
                            upbit_order_result: List[dict] = asyncio.run(upbit_service.get_orders(item['name'], upbit_order_id))
                            upbit_order_volume = upbit_order_result[0].get('executed_volume')
                            logger.info(f"Upbit 주문 체결량: {upbit_order_volume}")
                            if not upbit_order_volume:
                                logger.error(f"Upbit 주문 결과에서 volume을 찾을 수 없습니다: {upbit_order_result}")
                                return None

                            # Bybit 최소 주문 단위(lot size) 조회 
                            lot_size = asyncio.run(bybit_service.get_lot_size(item['name']))
                            logger.info(f"Bybit lot size: {lot_size}")
                            if not lot_size:
                                logger.error(f"Bybit lot size 정보를 가져올 수 없습니다: {item['name']}")
                                return None

                            # volume을 lot_size 단위로 내림(round down)
                            rounded_volume = math.floor(float(upbit_order_volume) / lot_size) * lot_size
                            logger.info(f"Rounded volume for Bybit order: {rounded_volume}")
                            if rounded_volume <= 0:
                                logger.error(f"Bybit 주문 가능한 최소 수량 미만: {upbit_order_volume} -> {rounded_volume}")
                                return None

                            # Bybit에서 rounded_volume만큼 매도 주문 실행
                            bybit_order = asyncio.run(bybit_service.order(item['name'], 'ask', rounded_volume))
                            bybit_order_id = bybit_order.get('result', {}).get('orderId')
                            logger.info(f"Bybit 주문 ID: {bybit_order_id}")
                            if not bybit_order_id:
                                logger.error(f"Bybit 주문 실행 실패: {bybit_order}")
                                return None
                            
                            # Bybit 주문내역 조회
                            bybit_order_result: List[dict] = asyncio.run(bybit_service.get_orders(item['name'], bybit_order_id))
                            price = Decimal(str(bybit_order_result[0].get('price', 0)))
                            qty = Decimal(str(bybit_order_result[0].get('qty', 0)))
                            bybit_order_usdt = (price * qty).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)

                            seed_decimal = Decimal(str(seed))
                            order_rate = (seed_decimal / bybit_order_usdt).quantize(Decimal('0.01'), rounding=ROUND_DOWN) if bybit_order_usdt else None
                            logger.info(f"주문을 실행했습니다: {item['name']} KRW매수금액={seed_decimal} USDT매도금액={bybit_order_usdt} 주문환율={order_rate}")
                            
                            
            # publish 시에도 조합 정보 포함
            redis_client.publish('exchange_rate', json.dumps({
                "exchange1": exchange1,
                "exchange2": exchange2,
                "results": res
            }))
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis connection error: {e}")
        if retry_count < 3:  # 무한루프 방지
            reconnect_redis()
            logger.info("작업 전체를 재시도합니다.")
            work_task(data, seed, exchange1, exchange2, retry_count + 1)
        else:
            logger.error("최대 재시도 횟수 초과. 작업을 중단합니다.")
            return

    logger.info("작업이 성공적으로 완료되었습니다.")
    
if __name__ == "__main__":
    app.worker_main()
    