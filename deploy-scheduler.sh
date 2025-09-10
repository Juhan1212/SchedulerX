#!/bin/bash

# EC2 Amazon Linux 스케줄러 배포 스크립트 (Redis + RabbitMQ + Scheduler)

echo "🚀 Starting scheduler deployment on Amazon Linux EC2..."

# 시스템 업데이트
sudo yum update -y

# # 개발 도구 및 필수 패키지 설치
# sudo yum groupinstall -y "Development Tools"
# sudo yum install -y git wget curl openssl-devel bzip2-devel libffi-devel zlib-devel

# # Python 3.11 설치 (Amazon Linux 2023의 경우)
# sudo yum install -y python3.11 python3.11-pip python3.11-devel

# # Python 3.11이 없는 경우 소스에서 컴파일 설치
# if ! command -v python3.11 &> /dev/null; then
#     echo "📦 Installing Python 3.11 from source..."
#     cd /tmp
#     wget https://www.python.org/ftp/python/3.11.7/Python-3.11.7.tgz
#     tar xzf Python-3.11.7.tgz
#     cd Python-3.11.7
#     ./configure --enable-optimizations
#     make altinstall
#     sudo ln -sf /usr/local/bin/python3.11 /usr/bin/python3.11
#     sudo ln -sf /usr/local/bin/pip3.11 /usr/bin/pip3.11
# fi

# curl -LsSf https://astral.sh/uv/install.sh | sh

# Redis 설치 및 설정
echo "📦 Installing Redis..."

# Redis 소스 컴파일 설치
cd /tmp
wget http://download.redis.io/redis-stable.tar.gz
tar xvzf redis-stable.tar.gz
cd redis-stable
make
sudo make install

# Redis CLI 심볼릭 링크 생성 (PATH에서 접근 가능하도록)
sudo ln -sf /usr/local/bin/redis-cli /usr/bin/redis-cli || true

# Redis 설정 디렉토리 생성
sudo mkdir -p /etc/redis
sudo mkdir -p /var/lib/redis
sudo mkdir -p /var/log/redis

# Redis 사용자 생성
sudo useradd --system --home /var/lib/redis --shell /bin/false redis || true
sudo chown redis:redis /var/lib/redis
sudo chown redis:redis /var/log/redis

# Redis 설정 파일 생성
sudo tee /etc/redis/redis.conf > /dev/null <<EOF
bind 0.0.0.0
port 6379
timeout 0
tcp-keepalive 300
daemonize yes
pidfile /var/run/redis.pid
loglevel notice
logfile /var/log/redis/redis-server.log
databases 16
dir /var/lib/redis
requireauth redis123
EOF

# Redis systemd 서비스 파일 생성
sudo tee /etc/systemd/system/redis.service > /dev/null <<EOF
[Unit]
Description=Advanced key-value store
After=network.target

[Service]
Type=notify
ExecStart=/usr/local/bin/redis-server /etc/redis/redis.conf
ExecStop=/usr/local/bin/redis-cli shutdown
TimeoutStopSec=0
Restart=always
User=redis
Group=redis
RuntimeDirectory=redis
RuntimeDirectoryMode=0755

[Install]
WantedBy=multi-user.target
EOF

# Redis 서비스 시작 및 활성화
sudo systemctl daemon-reload
sudo systemctl enable redis
sudo systemctl start redis

echo "✅ Redis installed and configured"

# RabbitMQ 설치 및 설정 (직접 설치)
echo "📦 Installing RabbitMQ..."

# Erlang 설치 (RabbitMQ 의존성)
sudo dnf install -y epel-release
sudo dnf install -y erlang

# RabbitMQ 공식 RPM 저장소 추가
curl -s https://packagecloud.io/install/repositories/rabbitmq/rabbitmq-server/script.rpm.sh | sudo bash

# RabbitMQ 서버 설치
sudo dnf install -y rabbitmq-server

# RabbitMQ 설정 파일 생성
sudo tee /etc/rabbitmq/rabbitmq.conf > /dev/null <<EOF
listeners.tcp.default = 5672
management.tcp.port = 15672
default_user = celery
default_pass = 123
EOF

# RabbitMQ 서비스 시작 및 활성화
sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server

# RabbitMQ 관리 플러그인 활성화
sudo rabbitmq-plugins enable rabbitmq_management

# 사용자 생성 및 권한 설정 (설정 파일의 기본 사용자 외에)
sleep 5
sudo rabbitmqctl add_user celery 123 || true
sudo rabbitmqctl set_user_tags celery administrator
sudo rabbitmqctl set_permissions -p / celery ".*" ".*" ".*"

echo "✅ RabbitMQ installed and configured"

# Python 가상환경 생성 및 활성화
sudo -u ec2-user python3.11 -m venv .venv
sudo -u ec2-user bash -c "source .venv/bin/activate && pip install --upgrade pip"

# uv로 패키지 동기화
uv sync

# PostgreSQL 클라이언트 라이브러리 설치 (psycopg2 빌드를 위해)
sudo dnf install -y libpq-devel

# 환경변수 파일 생성 (스케줄러용)
sudo -u ec2-user tee .env > /dev/null <<EOF
# Environment variables for Scheduler
REDIS_HOST=localhost
RABBITMQ_HOST=localhost
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

echo "📝 Please edit .env file with your RDS endpoint information"

# Scheduler를 위한 systemd 서비스 생성
sudo tee /etc/systemd/system/kimchi-scheduler.service > /dev/null <<EOF
[Unit]
Description=Kimchi Premium Scheduler
After=network.target redis.service rabbitmq-server.service
Requires=redis.service rabbitmq-server.service

[Service]
Type=exec
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/kimchi_premium_strategy_implementation
Environment=PATH=/home/ec2-user/kimchi_premium_strategy_implementation/venv/bin
ExecStart=/home/ec2-user/kimchi_premium_strategy_implementation/venv/bin/python scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable kimchi-scheduler

echo "✅ Scheduler service created. Start with: sudo systemctl start kimchi-scheduler"

# 로그 디렉토리 권한 설정
sudo -u ec2-user mkdir -p logs
sudo chmod 755 logs

# 서비스 상태 확인
echo "🔍 Checking services status..."
sudo systemctl status redis --no-pager
sudo systemctl status rabbitmq-server --no-pager

# 연결 테스트
echo "🧪 Testing connections..."

# Redis 연결 테스트
echo "Testing Redis connection..."
redis-cli -a redis123 ping

# RabbitMQ 연결 테스트
echo "Testing RabbitMQ connection..."
sudo rabbitmqctl status

echo "🎉 Scheduler deployment completed!"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env file with your RDS endpoint information"
echo "2. Test Redis connection: redis-cli -a redis123 ping"
echo "3. Test RabbitMQ: sudo rabbitmqctl status"
echo "4. Start scheduler: sudo systemctl start kimchi-scheduler"
echo "5. Monitor scheduler logs: sudo journalctl -u kimchi-scheduler -f"
echo ""
echo "🌐 Access points:"
echo "- Redis: localhost:6379 (password: redis123)"
echo "- RabbitMQ: localhost:5672 (user: celery, password: 123)"
echo "- RabbitMQ Management UI: http://\$(curl -s ifconfig.me):15672 (user: celery, password: 123)"
echo ""
echo "🔒 Security note:"
echo "- Redis password: redis123"
echo "- RabbitMQ user: celery/123"
echo "- Make sure to update security groups to allow worker instances to connect"
echo "- Allow ports 6379 (Redis), 5672 (RabbitMQ), and 15672 (RabbitMQ Management) in security groups"
echo ""
echo "📊 Service management:"
echo "- Redis: sudo systemctl start/stop/restart redis"
echo "- RabbitMQ: sudo systemctl start/stop/restart rabbitmq-server"
echo "- Scheduler: sudo systemctl start/stop/restart kimchi-scheduler"
