#!/bin/bash

# Amazon Linux EC2 인스턴스 초기 설정 및 프로젝트 배포 스크립트

echo "🚀 Starting deployment on Amazon Linux EC2..."

# uv로 패키지 동기화
uv sync

# 환경변수 파일이 없을 때만 생성 (Worker용 - 스케줄러 인스턴스 정보 입력 필요)
if [ ! -f .env ]; then
	sudo -u ec2-user tee .env > /dev/null <<EOF
# Environment variables for Worker
REDIS_HOST=10.0.5.242
RABBITMQ_HOST=10.0.5.242
RABBITMQ_USER=celery
RABBITMQ_PASSWORD=123
UPBIT_ACCESS_KEY=GPni76hBOOmIiFwAyEIQlUibHiX4JuWawK4RkeDR
UPBIT_SECRET_KEY=iQjPyvSrfzoigQKp5YBAskt8FRFLln2KyIlpcOFv
BYBIT_ACCESS_KEY=UwOQ7JsyFFpxqiQpG5
BYBIT_SECRET_KEY=hQGPXfsmoear7R99PbV8dfX9s6SIjPm3h80k
BITHUMB_ACCESS_KEY=e07105dc17f872426bf9cd6092eab167598d6cb843e021
BITHUMB_SECRET_KEY=N2FlZTlhMzZiYjk2ZjIwNzAyZDUxOWY4Nzc0MjE4ODljYjYyOTFlOGJkNjY1MzhmNmJiZjRhZWIyMmI2MA==
GATEIO_API_KEY=63bb1b5c4dee3aa890c9dc33653ed1a8
GATEIO_SECRET_KEY=2adf281422945ab760a66072c1de9f81f2c423047c0a01113b4fc9bdf35c6942
DATABASE_URL=postgresql://postgres:jXg4zJRdI]Y5.*Ii#*CeNjiSLFWN@postgresdb.cjoqmc0qg73c.ap-northeast-2.rds.amazonaws.com:5432/postgres
ENCODING_KEY=secret_key
ENCODING_ALGORITHM=HS256
TELEGRAM_BOT_TOKEN=7560818075:AAE7Kf8NF8sJYeGgbCv7dD7K3dQ9v4ZICbc
TELEGRAM_CHAT_ID=2085145028
EOF
fi

# Celery Worker를 위한 systemd 서비스 생성
sudo tee /etc/systemd/system/kimchi-celery-worker.service > /dev/null <<EOF
[Unit]
Description=Kimchi Premium Celery Worker
After=network.target

[Service]
Type=simple
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/SchedulerX
Environment=PATH=/home/ec2-user/SchedulerX/.venv/bin
ExecStart=/home/ec2-user/SchedulerX/.venv/bin/celery -A consumer worker --loglevel=info --concurrency=1
Restart=always
RestartSec=3
CPUQuota=15%

[Install]
WantedBy=multi-user.target
EOF

# 서비스 활성화 및 시작
sudo systemctl daemon-reload
sudo systemctl enable kimchi-celery-worker
sudo systemctl start kimchi-celery-worker
echo "✅ Celery worker service created. Start with: sudo systemctl start kimchi-celery-worker"

# 로그 디렉토리 권한 설정
sudo -u ec2-user mkdir -p logs
sudo chmod 755 logs

echo "🎉 Deployment completed!"
echo "📝 Next steps:"
echo "1. Edit .env file with your scheduler instance private IP"
echo "   Example: REDIS_HOST=10.0.1.100"
echo "   Example: RABBITMQ_HOST=10.0.1.100"
echo "2. Run database migrations if needed"
echo "3. Start celery worker: sudo systemctl start kimchi-celery-worker"
echo "4. Monitor logs: sudo journalctl -u kimchi-celery-worker -f"
echo ""
echo "🔒 Security note:"
echo "- Make sure security groups allow connections to Redis (6379) and RabbitMQ (5672) from this instance"
echo "- Update the SCHEDULER_INSTANCE_PRIVATE_IP in .env file"
