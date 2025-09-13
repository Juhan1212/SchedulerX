import os
import redis
import pytest
from dotenv import load_dotenv

load_dotenv()

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

def test_redis_connection(redis_client):
    """Redis 클라이언트 연결 상태만 확인하는 간단한 테스트"""
    try:
        # ping 명령으로 연결 확인
        response = redis_client.ping()
        assert response is True, "Redis ping should return True"
        print("✅ Redis connection successful")
        
        # 추가적으로 간단한 set/get 테스트
        test_key = "connection_test"
        test_value = "test_value"
        
        # 값 설정
        redis_client.set(test_key, test_value)
        
        # 값 조회
        retrieved_value = redis_client.get(test_key)
        assert retrieved_value == test_value, f"Expected {test_value}, got {retrieved_value}"
        
        # 테스트 키 삭제
        redis_client.delete(test_key)
        
        print("✅ Redis basic operations (set/get/delete) successful")
        
    except redis.ConnectionError as e:
        pytest.fail(f"Redis connection failed: {e}")
    except redis.RedisError as e:
        pytest.fail(f"Redis operation failed: {e}")
    except AssertionError:
        raise
    except Exception as e:
        pytest.fail(f"Unexpected error occurred: {e}")
