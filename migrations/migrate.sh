#!/bin/sh
# version_1.0.sh
# users 테이블 생성 마이그레이션

sqlite3 ../app.db < ./sql/migration_v1.sql

echo "[migration.sh] users 테이블 생성 완료 (version 1.0)"
