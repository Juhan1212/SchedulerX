#!/bin/bash

# EC2 인스턴스 초기 설정 및 프로젝트 배포 스크립트

echo "🚀 Starting deployment on EC2..."

# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Python 3.11 설치
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev python3-pip -y

# Git 설치
sudo apt install git -y

# 프로젝트 클론
cd /home/ubuntu
git clone https://github.com/JuhanKimSeoul/kimchi_premium_strategy_implementation.git
cd kimchi_premium_strategy_implementation

# Python 가상환경 생성 및 활성화
python3.11 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install --upgrade pip

# uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# uv로 패키지 동기화
uv sync

# PostgreSQL 클라이언트 라이브러리 설치 (psycopg2 빌드를 위해)
sudo apt install postgresql-client libpq-dev -y

# Celery Worker를 위한 systemd 서비스 생성
sudo tee /etc/systemd/system/kimchi-celery-worker.service > /dev/null <<EOF
[Unit]
Description=Kimchi Premium Celery Worker
After=network.target

[Service]
Type=exec
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/kimchi_premium_strategy_implementation
Environment=PATH=/home/ubuntu/kimchi_premium_strategy_implementation/venv/bin
ExecStart=/home/ubuntu/kimchi_premium_strategy_implementation/venv/bin/celery -A consumer worker --loglevel=info
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
mkdir -p logs
chmod 755 logs

echo "🎉 Deployment completed!"
echo "📝 Next steps:"
echo "1. Edit .env file with your RDS, Redis endpoints"
echo "2. Run database migrations if needed"
echo "3. Start celery worker: sudo systemctl start kimchi-celery-worker"
echo "4. Monitor logs: sudo journalctl -u kimchi-celery-worker -f"
