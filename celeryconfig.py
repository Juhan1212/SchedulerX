import os
from dotenv import load_dotenv

load_dotenv()

redis_host = f"{os.getenv('REDIS_HOST')}"
broker_url = f'redis://{redis_host}:6379/0'  
result_backend = f'redis://{redis_host}:6379/1'
worker_prefetch_multiplier = 10  # 작업자가 한 번에 최대 10개의 작업 가져오기
broker_connection_timeout = 5  # 브로커 연결 타임아웃 설정 ~ 