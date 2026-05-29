#!/usr/bin/env bash
set -euo pipefail
: "${DATABASE_URL:?Set DATABASE_URL, for example postgresql://dsm:dsm_password@localhost:5432/dsm_api}"
OUT="${1:-backups/dsm_api_$(date +%Y%m%d_%H%M%S).dump}"
mkdir -p "$(dirname "$OUT")"
pg_dump --format=custom --no-owner --no-acl "$DATABASE_URL" --file "$OUT"
echo "Backup written to $OUT"
