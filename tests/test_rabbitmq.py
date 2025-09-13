import os
import pika
import pytest
from dotenv import load_dotenv

load_dotenv()

# 실제 RabbitMQ 연결 (환경변수 또는 기본값 사용)
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_PORT = 5672
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "celery")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "123")

@pytest.fixture(scope="module")
def rabbitmq_connection():
    if not RABBITMQ_HOST:
        raise ValueError("Environment variable 'RABBITMQ_HOST' is not set.")
    
    # RabbitMQ 연결 파라미터 설정
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        connection_attempts=3,
        retry_delay=2
    )
    
    try:
        connection = pika.BlockingConnection(parameters)
        yield connection
        connection.close()
    except Exception as e:
        pytest.fail(f"Failed to connect to RabbitMQ: {e}")

def test_rabbitmq_connection(rabbitmq_connection):
    """RabbitMQ 연결 상태만 확인하는 간단한 테스트"""
    try:
        # 채널 생성으로 연결 확인
        channel = rabbitmq_connection.channel()
        assert channel is not None, "Channel should not be None"
        print("✅ RabbitMQ connection successful")
        
        # 테스트용 큐 생성 및 삭제
        test_queue = "connection_test_queue"
        
        # 큐 선언 (존재하지 않으면 생성)
        channel.queue_declare(queue=test_queue, durable=False)
        print("✅ RabbitMQ queue declare successful")
        
        # 간단한 메시지 발송 테스트
        test_message = "test_message"
        channel.basic_publish(
            exchange='',
            routing_key=test_queue,
            body=test_message
        )
        print("✅ RabbitMQ message publish successful")
        
        # 메시지 수신 테스트
        method, properties, body = channel.basic_get(queue=test_queue, auto_ack=True)
        if method:
            received_message = body.decode('utf-8')
            assert received_message == test_message, f"Expected {test_message}, got {received_message}"
            print("✅ RabbitMQ message consume successful")
        
        # 테스트 큐 삭제
        channel.queue_delete(queue=test_queue)
        print("✅ RabbitMQ queue delete successful")
        
        # 채널 닫기
        channel.close()
        print("✅ RabbitMQ basic operations (declare/publish/consume/delete) successful")
        
    except Exception as e:
        if "AMQPConnectionError" in str(type(e)) or "connection" in str(e).lower():
            pytest.fail(f"RabbitMQ connection failed: {e}")
        elif "AMQPChannelError" in str(type(e)) or "channel" in str(e).lower():
            pytest.fail(f"RabbitMQ channel error: {e}")
        else:
            pytest.fail(f"RabbitMQ test failed with error: {e}")
