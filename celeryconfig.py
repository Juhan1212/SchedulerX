import os
from dotenv import load_dotenv
from kombu import Queue

load_dotenv()

redis_host = f"{os.getenv('REDIS_HOST')}"
broker_url = f"sqs://{os.getenv('AWS_ACCESS_KEY_ID')}:{os.getenv('AWS_SECRET_ACCESS_KEY')}@"
result_backend = f'redis://{redis_host}:6379/0'  # Use the Redis server's host address
broker_transport_options = {
    'region': 'ap-northeast-2',
    'visibility_timeout': 3600,  # 1 hour
    'polling_interval': 10,  # 10 seconds
}
task_default_queue = 'testQueue'
task_queues = {
    Queue('testQueue'),
}

worker_prefetch_multiplier = 10  # 작업자가 한 번에 최대 10개의 작업 가져오기
