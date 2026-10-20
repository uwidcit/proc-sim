#!/bin/sh
set -eu

echo "Ensuring database schema…"
python - <<'PY'
from App.database import create_db
from wsgi import app

with app.app_context():
    create_db()
print("schema ready")
PY

exec "$@"
