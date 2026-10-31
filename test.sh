#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "[SecTicket] Budowanie obrazu testowego..."

docker build --target test -t secticket:test .

echo "[SecTicket] Uruchamianie testow..."

docker run \
  --rm \
  --network none \
  --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m,mode=1777 \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  secticket:test

echo "[SecTicket] Wszystkie testy zaliczone!"
