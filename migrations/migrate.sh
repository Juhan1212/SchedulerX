#!/bin/sh
# 모든 .sql 파일을 순서대로 실행

for sql in ./sql/*.sql; do
  echo "[migration.sh] 실행: $sql"
  sqlite3 ../app.db < "$sql"
done

echo "[migration.sh] 모든 마이그레이션 완료"