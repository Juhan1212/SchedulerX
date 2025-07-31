import os
from dotenv import load_dotenv

load_dotenv()

redis_host = f"{os.getenv('REDIS_HOST')}"
broker_url = f"amqp://celery:123@{os.getenv('RABBITMQ_HOST')}:5672//"
result_backend = f'redis://{redis_host}:6379/1'
worker_prefetch_multiplier = 10  # I/O bound task이므로 prefetch 수를 늘립니다.
broker_connection_timeout = 5  # 브로커 연결 타임아웃 설정
broker_connection_retry_on_startup = True  # 브로커 연결 실패 시 재시도 설정
result_expires = 60 * 60 * 24  # 결과 만료 시간 (24시간)
task_reject_on_worker_lost = True # 작업이 실패한 경우 재시도
broker_heartbeat = 10 # 브로커 하트비트 설정
task_soft_time_limit = 5  # 작업 소프트 타임 리밋 설정
worker_max_tasks_per_child=100 # worker 프로세스 메모리 누수 방지를 위한 최대 작업 수 설정