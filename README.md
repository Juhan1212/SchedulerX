# SchedulerX - 김치 프리미엄 자동매매 백엔드

<div align="center">

![SchedulerX](https://img.shields.io/badge/SchedulerX-Trading_Backend-blue?style=for-the-badge)

**알트코인 김치 프리미엄을 활용한 분산 자동매매 백엔드 시스템**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Celery](https://img.shields.io/badge/Celery-5.3-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7.2-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

[특징](#-주요-기능) • [시작하기](#-시작하기) • [아키텍처](#-시스템-아키텍처) • [배포](#-배포-가이드) • [클라이언트](#-클라이언트-연동)

</div>

---

## 📖 프로젝트 개요

**SchedulerX**는 한국과 해외 암호화폐 거래소 간의 가격 차이(김치 프리미엄)를 실시간으로 모니터링하고, 최적의 타이밍에 자동으로 포지션을 진입/종료하는 분산 백엔드 시스템입니다.

### 💡 김치 프리미엄이란?

> **환율은 화폐의 상대적 가치입니다.**

국제환율과 마찬가지로, 같은 암호화폐라도 국가별 거래소에서 서로 다른 가격에 거래됩니다. 특히 한국 거래소에서는 프리미엄(김치 프리미엄)이 발생하는 경우가 많습니다.

![알트코인 환율 예시](./assets/img/altcoin_kimchi_premium.png)

- **국내 거래소**: 현물 매수만 가능
- **해외 거래소**: 선물 매도 가능
- **전략**: 국내에서 매수 + 해외에서 매도 = 환율 차익 포착

이는 실제 코인을 보유하지 않으면서도(헤지), 환율 상승 시 수익을 얻을 수 있는 **환차익 거래 전략**입니다.

### ⚠️ 리스크

- **환율 리스크**: USD/KRW 환율 변동에 영향을 받음 (2025년 초 1500원 → 중반 1350원)
- **상대적 저위험**: 직접 코인 매수보다 리스크가 낮지만, 절대적 저위험은 아님
- **타이밍**: 불장 시 김치 프리미엄 폭등 (최대 100%), 하지만 예측 어려움

---

## ✨ 주요 기능

### 🏦 거래소 통합

- **국내 거래소**: Upbit, Bithumb
- **해외 거래소**: Bybit, Binance
- 실시간 호가창 기반 환율 계산
- API Rate Limit 관리 (Upbit: 30 req/s, Bybit: 120 req/s)

### 📈 트레이딩 전략

#### 비용 구조
- 국내→해외 테더 전송비 (온체인, 거의 무시)
- 포지션 진입 수수료 (시장가, ~0.075%)
- 포지션 종료 수수료 (시장가, ~0.075%)
- 해외→국내 테더 전송비

> **손익분기점**: 환율 상승 0.15% 이상

#### 핵심 전략
1. **슬리피지 최소화**: 호가창 실시간 분석으로 정확한 환율 계산
2. **유동성 확보**: 주요 거래소만 사용, 입출금 가능 코인만 거래
3. **실시간 모니터링**: 30초 간격으로 131개 공통 티커 환율 계산
4. **자동 진입/종료**: 
   - 진입: 환율이 테더 가격 대비 낮을 때
   - 종료: 사용자 지정 목표 환율 도달 시

### 🔄 분산 아키텍처

- **스케줄러 인스턴스**: 태스크 발행 및 데이터 집계
- **워커 인스턴스 x5**: 병렬 환율 계산 (IP 분산으로 Rate Limit 우회)
- **메시지 큐**: RabbitMQ 기반 태스크 분배
- **실시간 통신**: Redis Pub/Sub (gzip 압축 적용)

---

## 🛠️ 기술 스택

### Backend Core

```
Python 3.11 + FastAPI
├── FastAPI              # REST API 서버
├── Celery               # 분산 태스크 큐
├── RabbitMQ             # 메시지 브로커
├── APScheduler          # 주기적 스케줄링
├── Redis                # Pub/Sub + 캐싱
└── uv                   # 패키지 관리
```

### Database

```
PostgreSQL (RDS)
├── Users & Auth         # 사용자 인증/관리
├── Exchanges            # 거래소 정보
├── Strategies           # 자동매매 전략
├── Positions            # 활성 포지션
└── Trading History      # 거래 내역
```

### Exchange APIs

```
Exchange Integration
├── Upbit               # 한국 거래소 #1
├── Bithumb             # 한국 거래소 #2
├── Bybit               # 해외 거래소 #1
└── Binance             # 해외 거래소 #2
```

---

## 🏗️ 시스템 아키텍처

![인프라 구성도](./assets/img/architecture.png)

### 주요 컴포넌트

#### 스케줄러 인스턴스 (EC2 t3.micro)
- **APScheduler**: 5분마다 공통 티커 갱신
- **Celery Producer**: 30초마다 RabbitMQ에 태스크 발행
- **Redis Server**: 클라이언트 실시간 데이터 전송
- **RabbitMQ**: 메시지 브로커
- **FastAPI**: REST API 서버 (클라이언트 앱과 동일 서버)

#### 워커 인스턴스 (EC2 t2.micro x5)
- **Celery Consumer**: RabbitMQ에서 태스크 수신
- **환율 계산 엔진**: 호가창 기반 실시간 환율 계산
- **자동매매 엔진**: 조건 만족 시 포지션 진입/종료
- **IP 분산**: 거래소 Rate Limit 우회

### 데이터 흐름

1. **스케줄러** → 공통 티커 DB 갱신 (5분)
2. **스케줄러** → RabbitMQ에 태스크 발행 (30초)
3. **워커들** → RabbitMQ에서 태스크 폴링
4. **워커들** → 거래소 API 호출, 환율 계산
5. **워커들** → Redis에 gzip 압축 데이터 발행
6. **클라이언트** → Redis SSE로 실시간 수신
7. **자동매매** → 조건 만족 시 포지션 자동 실행

---

## 🚀 시작하기

### 사전 요구사항

- **Python** >= 3.11
- **PostgreSQL** >= 16
- **Redis** >= 7.2
- **RabbitMQ** >= 3.12
- **AWS Account** (EC2, RDS)
- **uv** (패키지 관리자)

### 로컬 개발 환경 설정

1. **저장소 클론**

   ```bash
   git clone https://github.com/Juhan1212/SchedulerX.git
   cd SchedulerX
   ```

2. **의존성 설치**

   ```bash
   # uv 설치 (없는 경우)
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # 패키지 설치
   uv sync
   ```

3. **환경 변수 설정**

   ```bash
   cp .env.example .env
   ```

   `.env` 파일 편집:

   ```env
   # Database
   DATABASE_URL=postgresql://user:password@localhost:5432/schedulerx
   
   # Redis
   REDIS_HOST=localhost
   REDIS_PORT=6379
   
   # RabbitMQ
   RABBITMQ_URL=amqp://guest:guest@localhost:5672//
   
   # Exchange API Keys
   UPBIT_ACCESS_KEY=your_upbit_access_key
   UPBIT_SECRET_KEY=your_upbit_secret_key
   BYBIT_API_KEY=your_bybit_api_key
   BYBIT_SECRET_KEY=your_bybit_secret_key
   # ... 기타 거래소 API 키
   ```

4. **데이터베이스 마이그레이션**

   ```bash
   # RDS 설정 가이드 참조
   cat RDS_SETUP_GUIDE.md
   
   # 마이그레이션 실행
   ./migrations/migrate.sh
   ```

5. **로컬 서비스 실행**

   ```bash
   # Redis 실행 (Docker)
   docker run -d -p 6379:6379 redis:7.2-alpine
   
   # RabbitMQ 실행 (Docker)
   docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:3.12-management
   
   # Celery Worker 실행
   celery -A consumer worker --loglevel=info
   
   # Scheduler 실행
   python scheduler.py
   
   # FastAPI 서버 실행 (선택사항)
   uvicorn main:app --reload
   ```

---

## 📋 배포 가이드

### AWS EC2 배포

#### 1. EC2 인스턴스 생성 시 User Data 입력

EC2 생성 시 **User Data** 섹션에 `aws_user_data.sh` 파일 내용을 입력하세요.

```bash
# aws_user_data.sh 내용 확인
cat aws_user_data.sh
```

이 스크립트는 다음을 자동으로 실행합니다:
- Python, Redis, RabbitMQ 설치
- uv 패키지 관리자 설치
- 프로젝트 클론 및 의존성 설치
- 환경 변수 설정

#### 2. 인스턴스 타입별 배포

**스케줄러 인스턴스 (EC2 t3.micro)**

```bash
ssh ec2-user@scheduler-instance-ip
cd SchedulerX
./deploy-scheduler.sh
```

이 스크립트는 다음을 실행합니다:
- FastAPI 서버 시작
- APScheduler 데몬 실행
- Celery Producer 실행
- Redis 서버 시작
- RabbitMQ 서버 시작

**워커 인스턴스 (EC2 t2.micro x5)**

```bash
ssh ec2-user@worker-instance-ip
cd SchedulerX
./deploy-celery-worker.sh
```

이 스크립트는 Celery Worker를 데몬으로 실행합니다.

#### 3. 서비스 상태 확인

```bash
# 스케줄러 인스턴스
systemctl status scheduler
systemctl status celery-producer
systemctl status redis
systemctl status rabbitmq

# 워커 인스턴스
systemctl status celery-worker
```

### 인프라 최적화 전략

> **비용 절감 우선 (90%) + 네트워크 지연 최소화 (10%)**

- **스케줄러**: FastAPI와 동일 서버 (t3.micro)
  - 장점: 비용 절감, 네트워크 레이턴시 최소화
  - 단점: 장애 전파 위험, 확장성 제한
  - 결정: 서비스 확대 전까지 최적화 우선

- **워커**: 여러 AWS 계정의 Free Tier 활용 (t2.micro x5)
  - IP 분산으로 거래소 Rate Limit 우회
  - 호가창 API는 티커당 1개씩만 호출 가능
  - 131개 티커 처리 위해 최소 5개 인스턴스 필요

---

## 🔗 클라이언트 연동

### Karbit 프론트엔드

본 프로젝트는 [**Karbit**](https://github.com/Juhan1212/karbit) 웹 애플리케이션의 백엔드입니다.

- **프레임워크**: React Router v7 + TypeScript
- **실시간 통신**: Redis SSE (Server-Sent Events)
- **데이터 압축**: gzip + base64 (Data Transfer 비용 절감)

### 데이터 압축 처리

**서버 측 (consumer.py)**

```python
import gzip
import base64
import json

# Redis에 압축된 데이터 발행
raw_json = json.dumps({"results": res})
compressed = gzip.compress(raw_json.encode('utf-8'))
encoded = base64.b64encode(compressed).decode('utf-8')
redis_client.publish('exchange_rate', encoded)
```

**클라이언트 측 (TypeScript)**

```typescript
import zlib from "zlib";

function decodeGzipBase64Message(msg: string) {
  const binary = Buffer.from(msg, "base64");
  const jsonStr = zlib.gunzipSync(binary).toString("utf-8");
  return JSON.parse(jsonStr);
}
```

> **반드시 백엔드와 클라이언트가 연동되어야** 실시간 환율/프리미엄 데이터가 정상적으로 표시됩니다.

---

## 📊 제약 조건 및 해결 방안

### API Rate Limits

| 거래소 | 제한                          | 해결 방안                    |
| ------ | ----------------------------- | ---------------------------- |
| Upbit  | 30 req/s                      | 워커 분산                    |
| Upbit  | Origin 헤더 시 10초당 1회     | Origin 헤더 제거             |
| Bybit  | 120 req/s                     | 워커 분산                    |
| Bithumb| WebSocket 오더북 미제공       | REST API 폴링                |

### 인프라 제약

- **Lambda 불가**: 거래소 IP 제한으로 서버리스 불가능
- **최소 5개 인스턴스**: 호가창 API 1개 티커당 1회 호출 제한
- **30초 간격**: AWS 비용 최적화 (SQS/RabbitMQ 호출 비용)

---

## 🔒 보안

### 구현된 보안 기능

- ✅ **API 키 암호화**: 거래소 API 키 DB 암호화 저장
- ✅ **환경 변수 관리**: 민감 정보 .env 분리
- ✅ **SQL 인젝션 방지**: ORM 사용
- ✅ **Rate Limiting**: 거래소 API 호출 제한 준수

---

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](./LICENSE) 파일을 참조하세요.

---

## 📞 지원 및 문의

- **이슈 리포트**: [GitHub Issues](https://github.com/Juhan1212/SchedulerX/issues)
- **클라이언트 프로젝트**: [Karbit Frontend](https://github.com/Juhan1212/karbit)

<div align="center">

**Built for Karbit Trading Platform**

[⬆ 맨 위로](#schedulerx---김치-프리미엄-자동매매-백엔드)

</div>
