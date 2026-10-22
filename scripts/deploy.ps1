# Trigger EasyPanel redeploy (reads EASYPANEL_DEPLOY_WEBHOOK from .env)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
python scripts/deploy.py
exit $LASTEXITCODE
