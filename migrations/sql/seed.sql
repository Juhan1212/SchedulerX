-- seed.sql
-- admin@test.com / password: 123
INSERT INTO users (email, password_hash) VALUES ('admin@test.com', 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3');
INSERT INTO seed (user_id, amt) VALUES (
    (SELECT id FROM users WHERE email = 'admin@test.com'), 1000000
);
-- 필요하다면 tickers 등도 추가