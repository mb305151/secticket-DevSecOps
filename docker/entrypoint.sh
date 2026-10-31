#!/bin/sh
set -eu

echo "[SecTicket] Aktualizacja schematu bazy..."
flask --app 'app:create_app()' db upgrade

echo "[SecTicket] Czyszczenie wygaslych licznikow..."

python - <<'PY'
from app import create_app
from app.rate_limit import cleanup_expired_buckets

app = create_app()

with app.app_context():
    removed = cleanup_expired_buckets()
    print(
        f"[SecTicket] Usunieto {removed} wygaslych wpisow.",
        flush=True
    )
PY

echo "[SecTicket] Uruchamianie aplikacji..."
exec "$@"
