"""Gunicorn config for EasyPanel / Render / Docker."""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"

# Sync workers are reliable across small VPS images; scale with WEB_CONCURRENCY.
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
threads = int(os.environ.get("WEB_THREADS", "4"))
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "gthread")

timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
graceful_timeout = 30
keepalive = 5

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
capture_output = True
preload_app = False

# Bid PDFs can be large; allow bigger request bodies via nginx/proxy separately.
limit_request_line = 8190
