import os
import pytest
import logging
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 환경변수 로드
load_dotenv()


class TestPostgreSQLRDS:
    """PostgreSQL RDS 연결 테스트"""
    
    database_url: Optional[str] = None
    
    @classmethod
    def setup_class(cls):
        """테스트 클래스 초기화"""
        cls.database_url = os.getenv("DATABASE_URL")
        if not cls.database_url:
            pytest.skip("DATABASE_URL environment variable not set")
        
        db_url = cls.database_url or ""
        db_info = db_url.split('@')[1] if '@' in db_url else 'hidden'
        logger.info("Testing database connection to: %s", db_info)
    
    def test_database_url_exists(self):
        """데이터베이스 URL 환경변수 존재 확인"""
        assert self.database_url is not None, "DATABASE_URL environment variable should be set"
        assert self.database_url.startswith("postgresql://"), "DATABASE_URL should start with postgresql://"
    
    def test_database_connection(self):
        """기본 데이터베이스 연결 테스트"""
        assert self.database_url is not None, "DATABASE_URL should be set"
        try:
            engine = create_engine(self.database_url)
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                row = result.fetchone()
                assert row is not None, "Query should return a result"
                assert row[0] == 1
            logger.info("✓ Database connection successful")
        except SQLAlchemyError as e:
            pytest.fail(f"Database connection failed: {str(e)}")
    
    def test_database_version(self):
        """PostgreSQL 버전 확인"""
        assert self.database_url is not None, "DATABASE_URL should be set"
        try:
            engine = create_engine(self.database_url)
            with engine.connect() as connection:
                result = connection.execute(text("SELECT version()"))
                row = result.fetchone()
                assert row is not None, "Version query should return a result"
                version = row[0]
                logger.info(f"PostgreSQL version: {version}")
                assert "PostgreSQL" in version
        except SQLAlchemyError as e:
            pytest.fail(f"Failed to get PostgreSQL version: {str(e)}")
    
    def test_session_creation(self):
        """SQLAlchemy 세션 생성 테스트"""
        assert self.database_url is not None, "DATABASE_URL should be set"
        try:
            engine = create_engine(self.database_url)
            SessionLocal = sessionmaker(bind=engine)
            session = SessionLocal()
            
            # 간단한 쿼리 실행
            result = session.execute(text("SELECT current_database()"))
            row = result.fetchone()
            assert row is not None, "Database name query should return a result"
            db_name = row[0]
            logger.info(f"Connected to database: {db_name}")
            
            session.close()
            assert db_name is not None
        except SQLAlchemyError as e:
            pytest.fail(f"Session creation failed: {str(e)}")
    
    def test_table_existence(self):
        """주요 테이블들의 존재 확인"""
        assert self.database_url is not None, "DATABASE_URL should be set"
        try:
            engine = create_engine(self.database_url)
            with engine.connect() as connection:
                # 테이블 목록 조회
                result = connection.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                tables = [row[0] for row in result.fetchall()]
                logger.info(f"Available tables: {tables}")
                
                # 예상되는 주요 테이블들 확인 (있을 경우만)
                expected_tables = ["users", "tickers", "exchanges", "user_tickers"]
                existing_expected = [table for table in expected_tables if table in tables]
                
                if existing_expected:
                    logger.info(f"Found expected tables: {existing_expected}")
                else:
                    logger.info("No expected tables found - this might be a fresh database")
                
        except SQLAlchemyError as e:
            pytest.fail(f"Failed to check table existence: {str(e)}")
    
    def test_database_permissions(self):
        """데이터베이스 권한 테스트"""
        assert self.database_url is not None, "DATABASE_URL should be set"
        try:
            engine = create_engine(self.database_url)
            with engine.connect() as connection:
                # 임시 테이블 생성으로 쓰기 권한 확인
                connection.execute(text("""
                    CREATE TEMPORARY TABLE test_permissions (
                        id SERIAL PRIMARY KEY,
                        test_data VARCHAR(50)
                    )
                """))
                
                # 데이터 삽입
                connection.execute(text("""
                    INSERT INTO test_permissions (test_data) VALUES ('test')
                """))
                
                # 데이터 조회
                result = connection.execute(text("""
                    SELECT test_data FROM test_permissions WHERE id = 1
                """))
                row = result.fetchone()
                assert row is not None, "Test data query should return a result"
                data = row[0]
                assert data == "test"
                
                logger.info("✓ Database read/write permissions verified")
                connection.commit()
                
        except SQLAlchemyError as e:
            pytest.fail(f"Database permissions test failed: {str(e)}")
    
    def test_connection_pool(self):
        """커넥션 풀 테스트"""
        assert self.database_url is not None, "DATABASE_URL should be set"
        try:
            # 커넥션 풀 설정
            engine = create_engine(
                self.database_url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=3600
            )
            
            # 여러 커넥션으로 동시 작업 시뮬레이션
            connections = []
            for i in range(3):
                conn = engine.connect()
                result = conn.execute(text(f"SELECT {i+1} as connection_test"))
                row = result.fetchone()
                assert row is not None, f"Connection {i+1} query should return a result"
                assert row[0] == i+1
                connections.append(conn)
            
            # 커넥션들 정리
            for conn in connections:
                conn.close()
                
            logger.info("✓ Connection pool test successful")
            
        except SQLAlchemyError as e:
            pytest.fail(f"Connection pool test failed: {str(e)}")
    
    def test_transaction_rollback(self):
        """트랜잭션 롤백 테스트"""
        assert self.database_url is not None, "DATABASE_URL should be set"
        try:
            engine = create_engine(self.database_url)
            with engine.connect() as connection:
                # 트랜잭션 시작
                trans = connection.begin()
                
                try:
                    # 임시 테이블 생성
                    connection.execute(text("""
                        CREATE TEMPORARY TABLE test_transaction (
                            id SERIAL PRIMARY KEY,
                            test_data VARCHAR(50)
                        )
                    """))
                    
                    # 데이터 삽입
                    connection.execute(text("""
                        INSERT INTO test_transaction (test_data) VALUES ('test_rollback')
                    """))
                    
                    # 의도적으로 롤백
                    trans.rollback()
                    
                    logger.info("✓ Transaction rollback test successful")
                    
                except Exception as e:
                    trans.rollback()
                    raise e
                    
        except SQLAlchemyError as e:
            pytest.fail(f"Transaction rollback test failed: {str(e)}")


if __name__ == "__main__":
    # 직접 실행시 테스트 수행
    pytest.main([__file__, "-v"])
