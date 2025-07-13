-- migration_v2.sql
-- 기존 테이블 구조와 SQLAlchemy 모델의 차이를 반영한 마이그레이션

-- 1. exchanges 테이블 신규 생성
CREATE TABLE IF NOT EXISTS exchanges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    uid TEXT,
    api_key TEXT,
    secret_key TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- 2. tickers 테이블에 user_tickers 관계 컬럼 추가 (user_ticker가 ticker_id를 FK로 가짐)
-- tickers 테이블은 이미 존재하므로 구조 변경 없음

-- 3. user_ticker 테이블 구조 변경: ticker_id 컬럼 추가, UNIQUE 제약 변경
ALTER TABLE user_ticker RENAME TO user_ticker_old;

CREATE TABLE user_ticker (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    ticker_id INTEGER NOT NULL,
    ticker_name TEXT,
    manual_del_yn INTEGER DEFAULT 0,
    manual_pick_yn INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(ticker_id) REFERENCES tickers(id),
    UNIQUE(user_id, ticker_id)
);

INSERT INTO user_ticker (id, user_id, ticker_id, ticker_name, manual_del_yn, manual_pick_yn)
SELECT id, user_id, NULL, ticker_name, manual_del_yn, manual_pick_yn FROM user_ticker_old;

DROP TABLE user_ticker_old;

-- 4. users 테이블은 변경 없음

-- 5. seed 테이블은 변경 없음

-- 6. tickers 테이블에 UNIQUE(exchange, name) 이미 존재, created_at 기본값 있음
-- tickers 테이블에 user_tickers 관계는 ORM상에서만 관리, DB에는 영향 없음

-- 7. 기타: 필요시 created_at, updated_at 컬럼에 DEFAULT CURRENT_TIMESTAMP, ON UPDATE CURRENT_TIMESTAMP 등 추가 가능
