"""
Credential loader for Artemis Tracker scripts.

Reads credentials from environment variables (GitHub Actions, production) or
falls back to local JSON files under /home/user/workspace (legacy/dev).

Env-vars expected in GitHub Actions:
- BLUESKY_HANDLE, BLUESKY_PASSWORD
- MASTODON_INSTANCE, MASTODON_ACCESS_TOKEN
- KIT_API_KEY
- THREADS_ACCESS_TOKEN, THREADS_USER_ID
- FIREBASE_SERVICE_ACCOUNT_JSON (the entire JSON contents, as a string)
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Optional

WORKSPACE = Path(os.environ.get("ARTEMIS_WORKSPACE", "/home/user/workspace"))


def _try_env_json(*keys: str) -> Optional[dict]:
    """Build a dict from individual env-vars if all keys are set."""
    values = {k.lower(): os.environ.get(k) for k in keys}
    if all(values.values()):
        return values
    return None


def load_bluesky() -> dict:
    """Returns {handle, password}."""
    handle = os.environ.get("BLUESKY_HANDLE")
    password = os.environ.get("BLUESKY_PASSWORD")
    if handle and password:
        return {"handle": handle, "password": password}
    path = WORKSPACE / "bluesky_config.json"
    if path.exists():
        return json.loads(path.read_text())
    raise RuntimeError("Bluesky credentials missing (set BLUESKY_HANDLE+BLUESKY_PASSWORD env vars or place bluesky_config.json in workspace)")


def load_mastodon() -> dict:
    """Returns {instance, access_token}."""
    instance = os.environ.get("MASTODON_INSTANCE")
    token = os.environ.get("MASTODON_ACCESS_TOKEN")
    if instance and token:
        return {"instance": instance, "access_token": token}
    path = WORKSPACE / "mastodon_config.json"
    if path.exists():
        return json.loads(path.read_text())
    raise RuntimeError("Mastodon credentials missing")


def load_kit() -> dict:
    """Returns {api_key}."""
    api_key = os.environ.get("KIT_API_KEY")
    if api_key:
        return {"api_key": api_key}
    path = WORKSPACE / "kit_config.json"
    if path.exists():
        return json.loads(path.read_text())
    raise RuntimeError("Kit credentials missing")


def load_threads() -> dict:
    """Returns {access_token, user_id}."""
    token = os.environ.get("THREADS_ACCESS_TOKEN")
    user_id = os.environ.get("THREADS_USER_ID")
    if token and user_id:
        return {"access_token": token, "user_id": user_id}
    path = WORKSPACE / "threads_config.json"
    if path.exists():
        return json.loads(path.read_text())
    raise RuntimeError("Threads credentials missing")


def get_firebase_service_account_path() -> Path:
    """
    Returns a path to a Firebase service account JSON file.

    In GitHub Actions: writes the FIREBASE_SERVICE_ACCOUNT_JSON env contents
    to a temp file and returns that path.

    Locally: searches workspace for artemis-tracker-665d8-firebase-adminsdk-*.json
    """
    sa_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if sa_json:
        # Validate it parses
        json.loads(sa_json)
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, prefix="firebase_sa_"
        )
        tmp.write(sa_json)
        tmp.close()
        return Path(tmp.name)
    # Local fallback
    matches = sorted(WORKSPACE.glob("artemis-tracker-665d8-firebase-adminsdk-*.json"))
    if matches:
        return matches[-1]
    raise RuntimeError(
        "Firebase service account missing. "
        "Set FIREBASE_SERVICE_ACCOUNT_JSON env var (entire JSON contents as a string) "
        "or place artemis-tracker-665d8-firebase-adminsdk-*.json in workspace."
    )
