-- version1_create_users.sql
-- users 테이블 DROP & CREATE
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS tickers;
DROP TABLE IF EXISTS seed;
DROP TABLE IF EXISTS user_ticker;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE tickers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange TEXT NOT NULL,
    name TEXT NOT NULL,
    dw_pos_yn INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(exchange, name)
);

CREATE TABLE seed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    amt INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE user_ticker (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    ticker_name TEXT NOT NULL,
    manual_del_yn INTEGER DEFAULT 0,
    manual_pick_yn INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id),
    UNIQUE(user_id, ticker_name)
);