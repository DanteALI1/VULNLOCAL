#!/usr/bin/env bash
set -euo pipefail

if [[ "${WAIT_FOR_DB:-0}" == "1" ]]; then
  echo "Waiting for database..."
  python - <<'PY'
import os, time
import psycopg
url = os.environ.get("DATABASE_URL", "")
for i in range(60):
    try:
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        print("DB ready")
        break
    except Exception as e:
        print(f"DB not ready ({e}), retry {i+1}/60")
        time.sleep(2)
else:
    raise SystemExit("Database did not become ready")
PY
fi

if [[ "${RUN_MIGRATIONS:-0}" == "1" ]]; then
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput || true
fi

exec "$@"
