import os
import json
import redis
import pytest

# 실제 Redis 연결 (환경변수 또는 기본값 사용)
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = 6379
REDIS_DB = 1

@pytest.fixture(scope="module")
def redis_client():
    if not REDIS_HOST:
        raise ValueError("Environment variable 'REDIS_HOST' is not set.")
    
    client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    yield client
    # 필요시 cleanup: client.flushdb()

def test_redis_mget(redis_client):
    exchange1 = "upbit"
    exchange2 = "bybit"
    
    # 테스트용 데이터 삽입
    redis_client.set(f"{exchange1}_{exchange2}_order_test:BTC", json.dumps({'ex_rate': 1400, 'size': 0.1}))
    redis_client.set(f"{exchange1}_{exchange2}_order_test:ETH", json.dumps({'ex_rate': 1400, 'size': 1}))

    # Redis 키 리스트 생성
    redis_keys = [f"{exchange1}_{exchange2}_order_test:BTC", f"{exchange1}_{exchange2}_order_test:ETH"]
    redis_orders = redis_client.mget(redis_keys)
    print(redis_orders)
    
    
