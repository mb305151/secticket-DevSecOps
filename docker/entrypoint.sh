#!/bin/sh
set -eu

echo "[SecTicket] Aktualizacja schematu bazy..."
flask --app 'app:create_app()' db upgrade

echo "[SecTicket] Czyszczenie wygaslych licznikow..."

python - <<'PY'
from app import create_app
from app.rate_limit import cleanup_expired_buckets
from app.audit import cleanup_expired_audit_events

app = create_app()

with app.app_context():
    removed = cleanup_expired_buckets()
    removed_audit = cleanup_expired_audit_events()

    print(
        f"[SecTicket] Usunieto {removed_audit} "
        "przestarzalych zdarzen audytu.",
        flush=True,
    )
    print(
        f"[SecTicket] Usunieto {removed} wygaslych wpisow.",
        flush=True
    )
PY

echo "[SecTicket] Uruchamianie aplikacji..."
exec "$@"
