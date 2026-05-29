#!/usr/bin/env bash
set -euo pipefail
: "${DATABASE_URL:?Set DATABASE_URL, for example postgresql://dsm:dsm_password@localhost:5432/dsm_api}"
: "${1:?Usage: scripts/restore_db.sh backups/file.dump}"
pg_restore --clean --if-exists --no-owner --no-acl --dbname "$DATABASE_URL" "$1"
echo "Restore completed from $1"
