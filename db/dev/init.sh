#!/bin/sh
# Hanya untuk Postgres lokal (docker-compose.dev.yml). Berjalan otomatis saat volume masih kosong.
set -e
P="psql -v ON_ERROR_STOP=1 -U $POSTGRES_USER -d $POSTGRES_DB"
$P -v sandi=dev-sandi-lokal -f /db/role-app.sql
for f in /db/migrations/*.sql; do $P -f "$f"; done
$P -f /db/seed.sql
