#!/bin/sh
set -eu

echo "[SecTicket] Aktualizacja schematu bazy danych..."

flask --app 'app:create_app()' db upgrade

echo "[SecTicket] Migracje zakonczone."
echo "[SecTicket] Uruchamianie aplikacji..."

exec "$@"
