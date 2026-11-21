#!/usr/bin/env python3
"""Test the TOPIC path to ONE device, and how fast a new sign-up takes effect.

Article alerts go to a topic, not to a device. This signs the one device
up for a private, random test topic (server side), sends message A to
that topic at once and message B a minute later, then removes the
sign-up. No other device is in the topic, so nobody else is notified.

If only B arrives, a fresh sign-up needs time before topic messages
reach the device. If both arrive, it takes effect at once.

The push ID is read from the event file and never printed.
"""
import json
import os
import secrets
import sys
import time
from datetime import datetime, timezone

import google.auth.transport.requests
import requests
from google.oauth2 import service_account

PROJECT_ID = "artemis-tracker-665d8"
SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]


def now():
    return datetime.now(timezone.utc).strftime("%H:%M:%S UTC")


def main():
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as f:
        token = ((json.load(f).get("inputs") or {}).get("token") or "").strip()
    if not token:
        print("No push ID given. Nothing sent.")
        sys.exit(1)
    print(f"::add-mask::{token}")

    creds = service_account.Credentials.from_service_account_info(
        json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT_JSON"]), scopes=SCOPES)
    creds.refresh(google.auth.transport.requests.Request())
    auth = {"Authorization": f"Bearer {creds.token}"}
    iid = {**auth, "access_token_auth": "true"}

    topic = "diag-" + secrets.token_hex(4)
    print(f"private test topic: {topic}")

    r = requests.post(
        f"https://iid.googleapis.com/iid/v1/{token}/rel/topics/{topic}",
        headers=iid, timeout=30)
    print(f"{now()}  sign-up: HTTP {r.status_code} {r.text.replace(token, '<push id>')[:300]}")
    if r.status_code != 200:
        sys.exit(2)

    def send(label, body):
        m = {"message": {
            "topic": topic,
            "notification": {"title": f"Artemis test {label}", "body": body},
            "apns": {"payload": {"aps": {"sound": "default"}}},
        }}
        r = requests.post(
            f"https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send",
            headers={**auth, "Content-Type": "application/json"}, json=m, timeout=30)
        print(f"{now()}  message {label}: HTTP {r.status_code} {r.text[:200].strip()}")

    send("A", "Sent right after the sign-up.")
    time.sleep(60)
    send("B", "Sent one minute after the sign-up.")

    time.sleep(5)
    r = requests.post(
        "https://iid.googleapis.com/iid/v1:batchRemove",
        headers={**iid, "Content-Type": "application/json"},
        json={"to": f"/topics/{topic}", "registration_tokens": [token]}, timeout=30)
    print(f"{now()}  sign-up removed: HTTP {r.status_code}")


if __name__ == "__main__":
    main()
