#!/usr/bin/env python3
"""Trigger an EasyPanel redeploy via the deploy webhook in .env."""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def main() -> int:
    load_dotenv(ROOT / ".env")
    url = os.environ.get("EASYPANEL_DEPLOY_WEBHOOK", "").strip()
    if not url:
        print(
            "EASYPANEL_DEPLOY_WEBHOOK is not set.\n"
            "Add it to .env (see .env.example) or export it in your shell.",
            file=sys.stderr,
        )
        return 1

    print(f"Triggering deploy…\n{url}")
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8", errors="replace").strip()
            print(f"HTTP {resp.status}: {body or '(empty)'}")
            return 0 if 200 <= resp.status < 300 else 1
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace").strip()
        print(f"HTTP {exc.code}: {body or exc.reason}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Request failed: {exc.reason}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
