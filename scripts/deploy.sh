#!/usr/bin/env bash
# Trigger EasyPanel redeploy (reads EASYPANEL_DEPLOY_WEBHOOK from .env)
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 scripts/deploy.py
