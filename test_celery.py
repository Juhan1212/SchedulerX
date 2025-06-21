from celery_app import add

if __name__ == "__main__":
    # 더하기 작업 전송
    result = add.apply_async((4, 6))  # 4 + 6 작업 전송
    print("Task sent to SQS!")

    # 결과 확인
    print("Waiting for result...")
    print("Result:", result.get(timeout=10))  # 결과를 10초 안에 가져옴