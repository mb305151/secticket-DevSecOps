#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env ]; then
    echo "[SecTicket] Generowanie konfiguracji..."

    umask 077

    SECRET="$(od -An -N32 -tx1 /dev/urandom | tr -d '[:space:]')"

    printf 'SECRET_KEY=%s\n' "$SECRET" > .env
    printf 'COOKIE_SECURE=false\n' >> .env
fi

echo "[SecTicket] Budowanie i uruchamianie kontenera..."

if ! docker compose up --build --wait --wait-timeout 120; then
    echo "[SecTicket] BLAD uruchamiania!"
    docker compose logs --tail=80 app
    exit 1
fi

echo ""
echo "[SecTicket] Aplikacja gotowa!"
echo "Panel:  http://localhost:5000"
echo "Health: http://localhost:5000/health"
