# PostgreSQL RDS 연결 테스트 가이드

## 개요

`test_rds.py` 파일은 PostgreSQL RDS 인스턴스와의 연결을 종합적으로 테스트하는 파이썬 테스트 스위트입니다.

## 테스트 항목

### 1. 환경 설정 테스트

- `test_database_url_exists`: DATABASE_URL 환경변수 존재 및 형식 확인

### 2. 연결 테스트

- `test_database_connection`: 기본 데이터베이스 연결 테스트
- `test_database_version`: PostgreSQL 버전 확인
- `test_session_creation`: SQLAlchemy 세션 생성 및 사용 테스트

### 3. 데이터베이스 구조 테스트

- `test_table_existence`: 주요 테이블들의 존재 확인

### 4. 권한 테스트

- `test_database_permissions`: 읽기/쓰기 권한 확인

### 5. 성능 및 안정성 테스트

- `test_connection_pool`: 커넥션 풀 동작 확인
- `test_transaction_rollback`: 트랜잭션 롤백 기능 확인

## 사용 방법

### 환경변수 설정

```bash
export DATABASE_URL="postgresql://username:password@your-rds-endpoint:5432/database_name"
```

또는 `.env` 파일에 설정:

```
DATABASE_URL=postgresql://username:password@your-rds-endpoint:5432/database_name
```

### 테스트 실행

#### 전체 테스트 실행

```bash
# pytest 사용
pytest tests/test_rds.py -v

# 직접 실행
python tests/test_rds.py
```

#### 특정 테스트 실행

```bash
# 연결 테스트만 실행
pytest tests/test_rds.py::TestPostgreSQLRDS::test_database_connection -v

# 권한 테스트만 실행
pytest tests/test_rds.py::TestPostgreSQLRDS::test_database_permissions -v
```

#### 상세한 로그와 함께 실행

```bash
pytest tests/test_rds.py -v -s --log-cli-level=INFO
```

## 예상 출력 예시

```
================ test session starts ================
tests/test_rds.py::TestPostgreSQLRDS::test_database_url_exists PASSED
tests/test_rds.py::TestPostgreSQLRDS::test_database_connection PASSED
INFO:__main__:✓ Database connection successful
tests/test_rds.py::TestPostgreSQLRDS::test_database_version PASSED
INFO:__main__:PostgreSQL version: PostgreSQL 13.7 on x86_64-pc-linux-gnu
tests/test_rds.py::TestPostgreSQLRDS::test_session_creation PASSED
INFO:__main__:Connected to database: mydb
tests/test_rds.py::TestPostgreSQLRDS::test_table_existence PASSED
INFO:__main__:Available tables: ['users', 'tickers', 'exchanges', 'user_tickers']
tests/test_rds.py::TestPostgreSQLRDS::test_database_permissions PASSED
INFO:__main__:✓ Database read/write permissions verified
tests/test_rds.py::TestPostgreSQLRDS::test_connection_pool PASSED
INFO:__main__:✓ Connection pool test successful
tests/test_rds.py::TestPostgreSQLRDS::test_transaction_rollback PASSED
INFO:__main__:✓ Transaction rollback test successful
================ 8 passed in 2.34s ================
```

## 오류 해결

### 일반적인 오류들

1. **DATABASE_URL 미설정**

   ```
   SKIPPED [1] DATABASE_URL environment variable not set
   ```

   - 해결: DATABASE_URL 환경변수를 설정하세요.

2. **연결 실패**

   ```
   Database connection failed: could not connect to server
   ```

   - 해결: RDS 엔드포인트, 포트, 보안그룹 설정을 확인하세요.

3. **인증 실패**

   ```
   Database connection failed: password authentication failed
   ```

   - 해결: 사용자명과 비밀번호를 확인하세요.

4. **데이터베이스 미존재**
   ```
   Database connection failed: database "dbname" does not exist
   ```

   - 해결: 데이터베이스 이름을 확인하고 필요시 생성하세요.

## 테스트 전 확인사항

1. **RDS 보안그룹**: 애플리케이션에서 RDS로의 접근 허용 확인
2. **네트워크 연결**: VPC, 서브넷 설정 확인
3. **데이터베이스 사용자**: 적절한 권한을 가진 사용자 계정 확인
4. **SSL/TLS 설정**: 필요시 SSL 인증서 설정 확인

## 추가 고려사항

- **프로덕션 환경**: 프로덕션 데이터베이스에 대한 테스트는 주의해서 수행
- **테스트 데이터**: 테스트는 임시 테이블을 사용하므로 기존 데이터에 영향 없음
- **성능**: 대용량 데이터베이스의 경우 테스트 시간이 길어질 수 있음
