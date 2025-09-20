#!/usr/bin/env bash
set -euo pipefail

DB="neo4j"
DUMP_BASENAME="${DUMP_BASENAME:-neo4j.dump}"
DUMP_PATH="/imports/${DUMP_BASENAME}"

echo "[INFO] Neo4j version pin: 5.26.10"
echo "[INFO] Target DB: ${DB}"
echo "[INFO] Dump path: ${DUMP_PATH}"

if [ -d "/data/databases/${DB}" ] || [ -f "/data/databases/${DB}" ]; then
  echo "[INFO] Database '${DB}' already exists under /data. Skipping load."
else
  if [ ! -f "${DUMP_PATH}" ]; then
    echo "[ERROR] Dump not found: ${DUMP_PATH}"
    echo "        Put your dump into ./dumps/ or provide DUMP_BASENAME env."
    exit 1
  fi
  echo "[INFO] Loading dump..."
  /var/lib/neo4j/bin/neo4j-admin database load "${DB}"     --from-path="$(dirname "${DUMP_PATH}")"     --overwrite-destination
  echo "[INFO] Load OK."
fi

echo "[INFO] Starting Neo4j..."
exec /startup/docker-entrypoint.sh neo4j
