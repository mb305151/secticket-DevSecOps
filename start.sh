#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

source scripts/check-docker.sh
secticket_check_docker yes

if [[ ! -e .env ]]; then
    echo '[SecTicket] Generowanie konfiguracji...'
    umask 077
    SECRET="$(od -An -N32 -tx1 /dev/urandom | tr -d '[:space:]')"
    if [[ ${#SECRET} -ne 64 ]]; then
        echo '[SecTicket] BLAD: Nie udalo sie utworzyc bezpiecznego klucza sesji.' >&2
        exit 1
    fi
    printf 'SECRET_KEY=%s\nCOOKIE_SECURE=false\n' "$SECRET" > .env
elif [[ ! -f .env ]]; then
    echo '[SecTicket] BLAD: .env istnieje, ale nie jest zwyklym plikiem.' >&2
    exit 1
fi

if ! docker compose config -q; then
    echo '[SecTicket] BLAD: Niepoprawna konfiguracja Docker Compose.' >&2
    exit 1
fi

echo '[SecTicket] Budowanie i uruchamianie kontenera...'
if ! docker compose up --build --detach --wait --wait-timeout 120; then
    echo '[SecTicket] BLAD uruchamiania! Ostatnie logi:' >&2
    docker compose ps >&2 || true
    docker compose logs --tail=80 app >&2 || true
    exit 1
fi

echo ''
echo '[SecTicket] Aplikacja gotowa!'
echo 'Panel:  http://localhost:5000'
echo 'Health: http://localhost:5000/health'
