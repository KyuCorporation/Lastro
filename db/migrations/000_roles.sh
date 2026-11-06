#!/bin/bash
# 000_roles.sh — cria os papéis de aplicação com senhas vindas do .env (roda no init do container postgres)
set -euo pipefail
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  create role lastro_app login password '${APP_DB_PASSWORD}' nobypassrls nosuperuser nocreatedb nocreaterole;
  create role lastro_ingest login password '${INGEST_DB_PASSWORD}' nobypassrls nosuperuser nocreatedb nocreaterole;
EOSQL
