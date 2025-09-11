#!/bin/bash

# EC2 Amazon Linux 스케줄러 배포 스크립트 (Redis + RabbitMQ + Scheduler)

echo "🚀 Starting scheduler deployment on Amazon Linux EC2..."

# Redis 설치 및 설정
echo "📦 Installing Redis..."

sudo dnf install redis6
sudo sed -i 's/bind 127.0.0.1 -::1/bind 0.0.0.0/g' /etc/redis/redis.conf
sudo sed -i 's/daemonize no/daemonize yes/g' /etc/redis/redis.conf
sudo systemctl restart redis6
sudo systemctl enable redis6

# Redis 설정 변경
sudo sed -i 's/bind 127.0.0.1 -::1/bind 0.0.0.0/g' /etc/redis6/redis6.conf
sudo sed -i 's/daemonize no/daemonize yes/g' /etc/redis6/redis6.conf
sudo sed -i 's/protected-mode yes/protected-mode no/g' /etc/redis6/redis6.conf

# Redis 연결 테스트
echo "Testing Redis connection..."
redis-cli ping

echo "✅ Redis installed and configured"

# RabbitMQ 설치 및 설정 (직접 설치)
echo "📦 Installing RabbitMQ..."

## primary RabbitMQ signing key
sudo rpm --import 'https://github.com/rabbitmq/signing-keys/releases/download/3.0/rabbitmq-release-signing-key.asc'
## modern Erlang repository
sudo rpm --import 'https://github.com/rabbitmq/signing-keys/releases/download/3.0/cloudsmith.rabbitmq-erlang.E495BB49CC4BBE5B.key'
## RabbitMQ server repository
sudo rpm --import 'https://github.com/rabbitmq/signing-keys/releases/download/3.0/cloudsmith.rabbitmq-server.9F4587F226208342.key'

sudo tee /etc/yum.repos.d/rabbitmq.repo > /dev/null <<EOF
# In /etc/yum.repos.d/rabbitmq.repo

##
## Zero dependency Erlang RPM
##

[modern-erlang]
name=modern-erlang-el9
# Use a set of mirrors maintained by the RabbitMQ core team.
# The mirrors have significantly higher bandwidth quotas.
baseurl=https://yum1.rabbitmq.com/erlang/el/9/$basearch https://yum2.rabbitmq.com/erlang/el/9/$basearch
repo_gpgcheck=1
enabled=1
gpgkey=https://github.com/rabbitmq/signing-keys/releases/download/3.0/cloudsmith.rabbitmq-erlang.E495BB49CC4BBE5B.key
gpgcheck=1
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
metadata_expire=300
pkg_gpgcheck=1
autorefresh=1
type=rpm-md

[modern-erlang-noarch]
name=modern-erlang-el9-noarch
# Use a set of mirrors maintained by the RabbitMQ core team.
# The mirrors have significantly higher bandwidth quotas.
baseurl=https://yum1.rabbitmq.com/erlang/el/9/noarch https://yum2.rabbitmq.com/erlang/el/9/noarch
repo_gpgcheck=1
enabled=1
gpgkey=https://github.com/rabbitmq/signing-keys/releases/download/3.0/cloudsmith.rabbitmq-erlang.E495BB49CC4BBE5B.key https://github.com/rabbitmq/signing-keys/releases/download/3.0/rabbitmq-release-signing-key.asc
gpgcheck=1
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
metadata_expire=300
pkg_gpgcheck=1
autorefresh=1
type=rpm-md


##
## RabbitMQ Server
##

[rabbitmq-el9]
name=rabbitmq-el9
baseurl=https://yum2.rabbitmq.com/rabbitmq/el/9/$basearch https://yum1.rabbitmq.com/rabbitmq/el/9/$basearch
repo_gpgcheck=1
enabled=1
# Cloudsmith's repository key and RabbitMQ package signing key
gpgkey=https://github.com/rabbitmq/signing-keys/releases/download/3.0/cloudsmith.rabbitmq-server.9F4587F226208342.key https://github.com/rabbitmq/signing-keys/releases/download/3.0/rabbitmq-release-signing-key.asc
gpgcheck=1
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
metadata_expire=300
pkg_gpgcheck=1
autorefresh=1
type=rpm-md

[rabbitmq-el9-noarch]
name=rabbitmq-el9-noarch
baseurl=https://yum2.rabbitmq.com/rabbitmq/el/9/noarch https://yum1.rabbitmq.com/rabbitmq/el/9/noarch
repo_gpgcheck=1
enabled=1
# Cloudsmith's repository key and RabbitMQ package signing key
gpgkey=https://github.com/rabbitmq/signing-keys/releases/download/3.0/cloudsmith.rabbitmq-server.9F4587F226208342.key https://github.com/rabbitmq/signing-keys/releases/download/3.0/rabbitmq-release-signing-key.asc
gpgcheck=1
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
metadata_expire=300
pkg_gpgcheck=1
autorefresh=1
type=rpm-md
EOF

## install these dependencies from standard OS repositories
dnf install -y logrotate

## install RabbitMQ and zero dependency Erlang
dnf install -y erlang rabbitmq-server

systemctl start rabbitmq-server
systemctl enable rabbitmq-server

# RabbitMQ 연결 테스트
echo "Testing RabbitMQ connection..."
sudo rabbitmqctl status

# RabbitMQ 사용자 및 권한 설정 (외부 접속을 허용하려면 새 계정을 만들고 권한을 부여해야 함)
sudo rabbitmqctl add_user celery 123
sudo rabbitmqctl set_user_tags celery administrator
sudo rabbitmqctl set_permissions -p / celery ".*" ".*" ".*"

# RabbitMQ 관리 콘솔 사용 시 계정 필요 → 관리 플러그인 활성화 필요
sudo rabbitmq-plugins enable rabbitmq_management

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
REDIS_HOST=3.39.252.79
RABBITMQ_HOST=3.39.252.79
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

echo "📝 Please edit .env file with your RDS endpoint information"

# Scheduler를 위한 systemd 서비스 생성
sudo tee /etc/systemd/system/kimchi-scheduler.service > /dev/null <<EOF
[Unit]
Description=Kimchi Premium Scheduler
After=network.target redis6.service rabbitmq-server.service
Requires=redis6.service rabbitmq-server.service

[Service]
Type=exec
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/kimchi_premium_strategy_implementation
Environment=PATH=/home/ec2-user/kimchi_premium_strategy_implementation/.venv/bin
ExecStart=/home/ec2-user/.local/bin/uv run scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable kimchi-scheduler
sudo systemctl start kimchi-scheduler

echo "✅ Scheduler service created. Start with: sudo systemctl start kimchi-scheduler"

echo "🎉 Scheduler deployment completed!"
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
