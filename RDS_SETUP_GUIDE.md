# AWS RDS PostgreSQL 설정 가이드

## 1. RDS 인스턴스 생성

### AWS 콘솔에서 생성:

1. RDS 대시보드 → "데이터베이스 생성"
2. 엔진 옵션: PostgreSQL
3. 템플릿: 프리 티어
4. DB 인스턴스 식별자: `kimchi-premium-db`
5. 마스터 사용자명: `admin`
6. 마스터 암호: 안전한 암호 설정
7. DB 인스턴스 클래스: `db.t3.micro`
8. 스토리지: 20GB gp2
9. 퍼블릭 액세스: 예 (EC2에서 접근하기 위해)

### 또는 AWS CLI로 생성:

```bash
aws rds create-db-instance \
    --db-instance-identifier kimchi-premium-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15.4 \
    --master-username admin \
    --master-user-password YOUR_SECURE_PASSWORD \
    --allocated-storage 20 \
    --storage-type gp2 \
    --publicly-accessible \
    --port 5432 \
    --backup-retention-period 7 \
    --storage-encrypted \
    --region ap-northeast-2
```

## 2. 보안 그룹 설정

### RDS 보안 그룹 인바운드 규칙:

- **타입**: PostgreSQL
- **프로토콜**: TCP
- **포트**: 5432
- **소스**: EC2 인스턴스들의 보안 그룹 ID 또는 IP 대역

### EC2 보안 그룹 아웃바운드 규칙:

- **타입**: PostgreSQL
- **프로토콜**: TCP
- **포트**: 5432
- **대상**: RDS 보안 그룹 ID

## 3. 네트워크 설정

### VPC 서브넷 그룹:

- RDS는 최소 2개의 서로 다른 가용 영역에 서브넷이 필요
- Default VPC 사용 시 자동으로 생성됨
- 커스텀 VPC 사용 시 DB 서브넷 그룹 생성 필요

## 4. 연결 테스트

### EC2에서 RDS 연결 테스트:

```bash
# PostgreSQL 클라이언트 설치
sudo apt install postgresql-client -y

# 연결 테스트
psql -h your-rds-endpoint.amazonaws.com -U admin -d postgres

# Python에서 연결 테스트
python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='your-rds-endpoint.amazonaws.com',
        port=5432,
        database='postgres',
        user='admin',
        password='your-password'
    )
    print('✅ RDS 연결 성공!')
    conn.close()
except Exception as e:
    print(f'❌ RDS 연결 실패: {e}')
"
```

## 5. 모니터링 및 유지보수

### CloudWatch 메트릭 확인:

- CPU 사용률
- 데이터베이스 연결 수
- 읽기/쓰기 IOPS
- 스토리지 사용량

### 백업 및 복원:

- 자동 백업: 7일간 보관 (설정 가능)
- 수동 스냅샷: 필요 시 생성
- 복원: 스냅샷에서 새 인스턴스 생성

### 비용 최적화:

- 사용하지 않는 시간에는 인스턴스 중지 (Free Tier에서도 중지 시간은 과금되지 않음)
- CloudWatch로 사용량 모니터링
- 12개월 후 인스턴스 크기 재검토

## 6. 마이그레이션

### 현재 SQLite에서 PostgreSQL로 데이터 마이그레이션:

```bash
# 1. 현재 SQLite 데이터 덤프
sqlite3 app.db .dump > sqlite_dump.sql

# 2. PostgreSQL 형식으로 변환 (수동 편집 필요)
# - AUTOINCREMENT → SERIAL
# - 데이터 타입 조정
# - SQL 문법 차이 해결

# 3. PostgreSQL에 데이터 적재
psql -h your-rds-endpoint.amazonaws.com -U admin -d postgres -f converted_dump.sql
```
