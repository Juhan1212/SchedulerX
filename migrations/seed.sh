#!/bin/sh
sqlite3 ../app.db < ./sql/seed.sql

echo "[seed.sh] 데이터베이스 시드 데이터 삽입 완료"