#!/bin/sh
set -eu
: "${APP_DB_PASSWORD:?APP_DB_PASSWORD must be set}"
psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set=app_db_password="$APP_DB_PASSWORD" \
  --set=db_name="$POSTGRES_DB" <<'EOSQL'
CREATE ROLE career_app
  LOGIN PASSWORD :'app_db_password'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
GRANT CONNECT ON DATABASE :"db_name" TO career_app;
GRANT USAGE ON SCHEMA public TO career_app;
EOSQL
