#!/bin/sh
set -eu

echo "Running database migrations…"
flask db upgrade
echo "schema ready"

exec "$@"
