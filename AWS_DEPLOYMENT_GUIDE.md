# AWS EC2 배포 가이드

## 🏗️ 아키텍처 개요

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Scheduler     │    │    Worker 1     │    │    Worker N     │
│   Instance      │    │   Instance      │    │   Instance      │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Redis       │◄├────┤ │ Celery      │ │    │ │ Celery      │ │
│ │ RabbitMQ    │◄├────┤ │ Worker      │ │    │ │ Worker      │ │
│ │ Scheduler   │ │    │ │             │ │    │ │             │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   RDS PostgreSQL │
                    │    Database      │
                    └─────────────────┘
```

## 📋 배포 단계

### 1단계: RDS PostgreSQL 인스턴스 생성

1. AWS RDS 콘솔에서 PostgreSQL 인스턴스 생성
2. Free Tier 템플릿 선택
3. DB 인스턴스 식별자: `kimchi-premium-db`
4. 마스터 사용자명: `admin`
5. 보안 그룹에서 5432 포트 개방 (EC2 인스턴스들만 접근)

### 2단계: 스케줄러 인스턴스 배포

```bash
# EC2 인스턴스 생성 후 스케줄러 배포
chmod +x deploy-scheduler.sh
./deploy-scheduler.sh
```

**스케줄러 인스턴스 설정:**

- 인스턴스 타입: `t3.small` 이상 권장 (Redis + RabbitMQ 운영)
- 보안 그룹: 6379 (Redis), 5672 (RabbitMQ), 15672 (RabbitMQ Management) 포트 개방
- 스토리지: 20GB 이상

### 3단계: Worker 인스턴스들 배포

```bash
# 각 Worker EC2 인스턴스에서 실행
chmod +x deploy.sh
./deploy.sh
```

**Worker 인스턴스 설정:**

- 인스턴스 타입: `t3.micro` (Free Tier 가능)
- 보안 그룹: 아웃바운드 6379, 5672 포트 허용
- 스토리지: 8GB (기본값)

### 4단계: 환경 변수 설정

#### 스케줄러 인스턴스 (.env):

```env
REDIS_HOST=localhost
RABBITMQ_HOST=localhost
DATABASE_URL=postgresql://admin:YOUR_RDS_PASSWORD@your-rds-endpoint.amazonaws.com:5432/postgres
# ... 기타 환경변수
```

#### Worker 인스턴스들 (.env):

```env
REDIS_HOST=SCHEDULER_INSTANCE_PRIVATE_IP
RABBITMQ_HOST=SCHEDULER_INSTANCE_PRIVATE_IP
DATABASE_URL=postgresql://admin:YOUR_RDS_PASSWORD@your-rds-endpoint.amazonaws.com:5432/postgres
# ... 기타 환경변수
```

## 🚀 서비스 시작

### 스케줄러 시작:

```bash
sudo systemctl start kimchi-scheduler
sudo systemctl status kimchi-scheduler
```

### Worker들 시작:

```bash
sudo systemctl start kimchi-celery-worker
sudo systemctl status kimchi-celery-worker
```

## 📊 모니터링

### 로그 확인:

```bash
# 스케줄러 로그
sudo journalctl -u kimchi-scheduler -f

# Worker 로그
sudo journalctl -u kimchi-celery-worker -f
```

### RabbitMQ 관리 UI:

- URL: `http://SCHEDULER_PUBLIC_IP:15672`
- 계정: `celery` / `123`

### Redis 모니터링:

```bash
# 스케줄러 인스턴스에서
redis-cli info
redis-cli monitor
```

## 🔒 보안 설정

### 보안 그룹 설정:

#### 스케줄러 인스턴스 보안 그룹:

- **인바운드:**
  - 6379/tcp: Worker 인스턴스들만 접근
  - 5672/tcp: Worker 인스턴스들만 접근
  - 15672/tcp: 관리자 IP만 접근 (RabbitMQ Management UI)
  - 22/tcp: 관리자 IP만 접근 (SSH)

#### Worker 인스턴스 보안 그룹:

- **아웃바운드:**
  - 6379/tcp: 스케줄러 인스턴스로
  - 5672/tcp: 스케줄러 인스턴스로
  - 5432/tcp: RDS로
  - 443/tcp: 외부 API 호출용

#### RDS 보안 그룹:

- **인바운드:**
  - 5432/tcp: 모든 EC2 인스턴스들만 접근

## 💰 비용 최적화

### Free Tier 활용:

- RDS: `db.t3.micro` (12개월 무료)
- EC2: `t3.micro` × 4개 (각각 750시간/월 무료)
- 총 예상 비용 (12개월 후): 월 $30-40

### 비용 절약 팁:

1. Worker 인스턴스는 필요 시에만 확장
2. CloudWatch로 사용량 모니터링
3. 야간 시간대 인스턴스 스케일 다운 고려

## 🔧 트러블슈팅

### 연결 문제:

```bash
# Redis 연결 테스트
redis-cli -h SCHEDULER_IP ping

# RabbitMQ 연결 테스트
curl -u celery:123 http://SCHEDULER_IP:15672/api/overview

# PostgreSQL 연결 테스트
psql -h RDS_ENDPOINT -U admin -d postgres
```

### 서비스 재시작:

```bash
# 전체 스택 재시작 (스케줄러에서)
sudo systemctl restart redis-server
sudo systemctl restart rabbitmq-server
sudo systemctl restart kimchi-scheduler

# Worker 재시작 (각 Worker 인스턴스에서)
sudo systemctl restart kimchi-celery-worker
```

## 📈 확장성

### Worker 인스턴스 추가:

1. 새 EC2 인스턴스 생성
2. `deploy.sh` 실행
3. 환경변수 설정 (스케줄러 IP 입력)
4. Worker 서비스 시작

### 모니터링 추가:

- CloudWatch로 EC2 메트릭 모니터링
- RabbitMQ 큐 길이 모니터링
- Redis 메모리 사용량 모니터링
