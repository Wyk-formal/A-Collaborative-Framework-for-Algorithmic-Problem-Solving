#!/usr/bin/env bash
set -euo pipefail

URL="$1"
OUTFILE="${2:-neo4j.dump}"

mkdir -p ./dumps
curl -L -o "./dumps/${OUTFILE}" "$URL"

if [ -f "./dumps/${OUTFILE}.sha256" ]; then
  echo "[INFO] Verifying checksum..."
  shasum -a 256 -c "./dumps/${OUTFILE}.sha256"
else
  echo "[WARN] No checksum file provided, skipping verification."
fi

echo "[INFO] Dump downloaded to ./dumps/${OUTFILE}"
