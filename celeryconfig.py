import os
from dotenv import load_dotenv

load_dotenv()

redis_host = f"{os.getenv('REDIS_HOST')}"
broker_url = f"amqp://guest:guest@{os.getenv('RABBITMQ_HOST')}:5672//"
result_backend = f'redis://{redis_host}:6379/1'
worker_prefetch_multiplier = 10  # I/O bound task이므로 prefetch 수를 늘립니다.
broker_connection_timeout = 5  # 브로커 연결 타임아웃 설정
broker_connection_retry_on_startup = True  # 브로커 연결 실패 시 재시도 설정