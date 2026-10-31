#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env ]; then
    echo "[SecTicket] Tworzenie konfiguracji .env..."

    umask 077

    SECRET="$(od -An -N32 -tx1 /dev/urandom | tr -d '[:space:]')"

    printf 'SECRET_KEY=%s\n' "$SECRET" > .env
    printf 'COOKIE_SECURE=false\n' >> .env
fi

echo "[SecTicket] Budowanie i uruchamianie..."

docker compose up -d --build

echo ""
echo "[SecTicket] Kontenery uruchomione."
echo "Aplikacja: http://localhost:5000"
echo "Health:    http://localhost:5000/health"
