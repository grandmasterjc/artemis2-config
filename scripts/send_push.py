#!/usr/bin/env python3
"""Send an FCM v1 push notification to the 'all' topic.

Usage:
    python3 scripts/send_push.py "TITLE" "BODY" "ARTICLE_ID" "TOPIC"

Auto-detects the Firebase service account JSON in /home/user/workspace/
because the filename suffix rotates whenever the key is regenerated.

Logs every push to state/push_history.csv (committed to repo so the
push-backfill cron has historical context).
"""
import csv
import glob
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import google.auth.transport.requests
    from google.oauth2 import service_account
    import requests
except ImportError as e:
    print(f"Missing dependency: {e}. pip install google-auth requests", file=sys.stderr)
    sys.exit(1)

PROJECT_ID = "artemis-tracker-665d8"
FCM_URL = f"https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send"
SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = REPO_ROOT / "state"
PUSH_HISTORY = STATE_DIR / "push_history.csv"
WORKSPACE = Path("/home/user/workspace")


def find_service_account():
    matches = sorted(glob.glob(str(WORKSPACE / "artemis-tracker-*-firebase-adminsdk-*.json")))
    if not matches:
        raise FileNotFoundError(
            "No Firebase service account JSON found in /home/user/workspace/. "
            "Re-upload from Firebase Console → Project Settings → Service accounts."
        )
    return matches[0]


def get_access_token(sa_path):
    creds = service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def send(title, body, article_id, topic="all"):
    sa_path = find_service_account()
    token = get_access_token(sa_path)
    message = {
        "message": {
            "topic": topic,
            "notification": {"title": title, "body": body},
            "data": {"article_id": article_id, "type": "article"},
            "apns": {"payload": {"aps": {"sound": "default", "badge": 1}}},
            "android": {"priority": "high", "notification": {"sound": "default"}},
        }
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.post(FCM_URL, headers=headers, json=message, timeout=30)
    r.raise_for_status()
    return r.json()["name"]


def log_push(title, body, article_id, topic, message_id):
    STATE_DIR.mkdir(exist_ok=True)
    new = not PUSH_HISTORY.exists()
    with PUSH_HISTORY.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp_utc", "title", "body", "article_id", "topic", "message_id"])
        w.writerow([datetime.now(timezone.utc).isoformat(), title, body, article_id, topic, message_id])


def main():
    if len(sys.argv) < 5:
        print("Usage: send_push.py TITLE BODY ARTICLE_ID TOPIC", file=sys.stderr)
        sys.exit(2)
    title, body, article_id, topic = sys.argv[1:5]
    message_id = send(title, body, article_id, topic)
    log_push(title, body, article_id, topic, message_id)
    print(f"Message ID: {message_id}")


if __name__ == "__main__":
    main()
