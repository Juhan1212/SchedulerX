#!/bin/bash

# Amazon Linux EC2 인스턴스 초기 설정 및 프로젝트 배포 스크립트

echo "🚀 Starting deployment on Amazon Linux EC2..."

# 시스템 업데이트
sudo yum update -y

# # 개발 도구 및 필수 패키지 설치
# sudo yum groupinstall -y "Development Tools"
# sudo yum install -y git wget curl openssl-devel bzip2-devel libffi-devel zlib-devel

# # Python 3.11 설치 시도 (Amazon Linux 2023의 경우)
# if ! command -v python3.11 &> /dev/null; then
#     echo "📦 Installing Python 3.11 from source..."
#     cd /tmp
#     wget https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz
#     tar xzf Python-3.11.9.tgz
#     cd Python-3.11.9
#     ./configure --enable-optimizations --with-ensurepip=install
#     make altinstall
#     sudo ln -sf /usr/local/bin/python3.11 /usr/bin/python3.11
#     sudo ln -sf /usr/local/bin/pip3.11 /usr/bin/pip3.11
# else
#     echo "✅ Python 3.11 already installed"
# fi

# curl -LsSf https://astral.sh/uv/install.sh | sh

# PostgreSQL 클라이언트 라이브러리 설치 (psycopg2 빌드를 위해)
# sudo yum install -y postgresql-devel

# Python 가상환경 생성 및 활성화 (Python 3.11 사용)
sudo -u ec2-user python3.11 -m venv venv
sudo -u ec2-user bash -c "source venv/bin/activate && pip install --upgrade pip"

# uv로 패키지 동기화
uv sync

# 환경변수 파일 생성 (Worker용 - 스케줄러 인스턴스 정보 입력 필요)
sudo -u ec2-user tee .env > /dev/null <<EOF
# Environment variables for Worker
REDIS_HOST=SCHEDULER_INSTANCE_PRIVATE_IP
RABBITMQ_HOST=SCHEDULER_INSTANCE_PRIVATE_IP
UPBIT_ACCESS_KEY=GPni76hBOOmIiFwAyEIQlUibHiX4JuWawK4RkeDR
UPBIT_SECRET_KEY=iQjPyvSrfzoigQKp5YBAskt8FRFLln2KyIlpcOFv
BYBIT_ACCESS_KEY=UwOQ7JsyFFpxqiQpG5
BYBIT_SECRET_KEY=hQGPXfsmoear7R99PbV8dfX9s6SIjPm3h80k
BITHUMB_ACCESS_KEY=e07105dc17f872426bf9cd6092eab167598d6cb843e021
BITHUMB_SECRET_KEY=N2FlZTlhMzZiYjk2ZjIwNzAyZDUxOWY4Nzc0MjE4ODljYjYyOTFlOGJkNjY1MzhmNmJiZjRhZWIyMmI2MA==
GATEIO_API_KEY=63bb1b5c4dee3aa890c9dc33653ed1a8
GATEIO_SECRET_KEY=2adf281422945ab760a66072c1de9f81f2c423047c0a01113b4fc9bdf35c6942
DATABASE_URL=postgresql://postgres:qVUR3fUBgGb$z77EU6S-X_:6d8*F@postgresdb.cjoqmc0qg73c.ap-northeast-2.rds.amazonaws.com:5432/postgres
ENCODING_KEY=secret_key
ENCODING_ALGORITHM=HS256
TELEGRAM_BOT_TOKEN=7560818075:AAE7Kf8NF8sJYeGgbCv7dD7K3dQ9v4ZICbc
TELEGRAM_CHAT_ID=2085145028
EOF

echo "📝 Please edit .env file with scheduler instance IP and RDS endpoint"

# Celery Worker를 위한 systemd 서비스 생성
sudo tee /etc/systemd/system/kimchi-celery-worker.service > /dev/null <<EOF
[Unit]
Description=Kimchi Premium Celery Worker
After=network.target

[Service]
Type=exec
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/kimchi_premium_strategy_implementation
Environment=PATH=/home/ec2-user/kimchi_premium_strategy_implementation/venv/bin
ExecStart=/home/ec2-user/kimchi_premium_strategy_implementation/venv/bin/celery -A consumer worker --loglevel=info
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 서비스 활성화 및 시작
sudo systemctl daemon-reload
sudo systemctl enable kimchi-celery-worker
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
