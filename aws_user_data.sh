#!/bin/bash
# -------------------------------
# EC2 초기 부팅 시 Swap 메모리 설정
# -------------------------------

# 스왑 파일 위치와 크기 (예: 2GB)
SWAPFILE=/swapfile
SWAPSIZE=2G

# 기존 스왑 비활성화 및 삭제 (있으면)
if [ -f $SWAPFILE ]; then
    swapoff $SWAPFILE
    rm -f $SWAPFILE
fi

# 스왑 파일 생성
fallocate -l $SWAPSIZE $SWAPFILE
chmod 600 $SWAPFILE

# 스왑 영역 설정
mkswap $SWAPFILE

# 스왑 활성화
swapon $SWAPFILE

# fstab에 등록 (재부팅 후에도 활성화)
grep -qxF "$SWAPFILE swap swap defaults 0 0" /etc/fstab || echo "$SWAPFILE swap swap defaults 0 0" >> /etc/fstab

# 확인
swapon --show
free -h

# 시스템 업데이트
sudo yum update -y

# 개발 도구 및 필수 패키지 설치
sudo yum groupinstall -y "Development Tools"
sudo yum install -y git wget curl openssl-devel bzip2-devel libffi-devel zlib-devel

# Python 3.11 설치 (Amazon Linux 2023의 경우)
sudo yum install -y python3.11 python3.11-pip python3.11-devel

# Python 3.11이 없는 경우 소스에서 컴파일 설치
if ! command -v python3.11 &> /dev/null; then
    echo "📦 Installing Python 3.11 from source..."
    cd /tmp
    wget https://www.python.org/ftp/python/3.11.7/Python-3.11.7.tgz
    tar xzf Python-3.11.7.tgz
    cd Python-3.11.7
    ./configure --enable-optimizations
    make altinstall
    sudo ln -sf /usr/local/bin/python3.11 /usr/bin/python3.11
    sudo ln -sf /usr/local/bin/pip3.11 /usr/bin/pip3.11
fi

# uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# PostgreSQL 클라이언트 설치 (RDS 연결용)
sudo yum install -y postgresql15

# 저널 로그 설정 (로그 용량 제한 및 보존 기간 설정)
sudo sed -i 's/^#SystemMaxUse=.*/SystemMaxUse=10M/' /etc/systemd/journald.conf
sudo sed -i 's/^#MaxRetentionSec=.*/MaxRetentionSec=7day/' /etc/systemd/journald.conf

# nodejs 설치 (프론트엔드 빌드용)
sudo yum install -y nodejs