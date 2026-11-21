#!/usr/bin/env python3
"""Send one test notification to ONE device, and show what Firebase knows
about that device.

The device's push ID (FCM token) comes from the workflow_dispatch input
"token". It is read from the event file, never from the command line or
the environment, and it is never printed, so it stays out of the log.

Steps:
  1. Ask Firebase which app, platform and topics the push ID belongs to.
  2. Send a test notification to that push ID only.
Firebase reports errors for a single device (unlike a topic send), so a
failure here names the cause.
"""
import json
import os
import sys

import google.auth.transport.requests
import requests
from google.oauth2 import service_account

PROJECT_ID = "artemis-tracker-665d8"
SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]


def read_token():
    path = os.environ.get("GITHUB_EVENT_PATH")
    if not path:
        return ""
    with open(path, encoding="utf-8") as f:
        event = json.load(f)
    return ((event.get("inputs") or {}).get("token") or "").strip()


def main():
    token = read_token()
    if not token:
        print("No push ID given. Nothing sent.")
        sys.exit(1)
    # Mask it in case any library echoes it.
    print(f"::add-mask::{token}")
    print(f"Push ID ends in ...{token[-6:]} ({len(token)} characters)")

    sa_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        print("FIREBASE_SERVICE_ACCOUNT_JSON missing", file=sys.stderr)
        sys.exit(1)
    creds = service_account.Credentials.from_service_account_info(
        json.loads(sa_json), scopes=SCOPES)
    creds.refresh(google.auth.transport.requests.Request())
    auth = {"Authorization": f"Bearer {creds.token}"}

    # 1) What does Firebase know about this push ID?
    print("\n== 1. Firebase's record of this device")
    r = requests.get(
        f"https://iid.googleapis.com/iid/info/{token}",
        params={"details": "true"},
        headers={**auth, "access_token_auth": "true"},
        timeout=30,
    )
    if r.status_code == 200:
        info = r.json()
        print(f"app:         {info.get('application')}")
        print(f"platform:    {info.get('platform')}")
        print(f"app version: {info.get('applicationVersion')}")
        topics = ((info.get("rel") or {}).get("topics") or {})
        if topics:
            for name in sorted(topics):
                print(f"topic:       {name} (since {topics[name].get('addDate')})")
        else:
            print("topics:      NONE. This device is not signed up for any topic.")
        print(f"signed up for 'all': {'YES' if 'all' in topics else 'NO'}")
    else:
        print(f"lookup failed: HTTP {r.status_code}")
        print(r.text.replace(token, "<push id>")[:1500])

    # 2) Send to this device only.
    print("\n== 2. Test notification to this device only")
    message = {
        "message": {
            "token": token,
            "notification": {
                "title": "Artemis test",
                "body": "Test notification sent to this device only.",
            },
            "apns": {"payload": {"aps": {"sound": "default"}}},
        }
    }
    r = requests.post(
        f"https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send",
        headers={**auth, "Content-Type": "application/json"},
        json=message,
        timeout=30,
    )
    if r.status_code == 200:
        print("Firebase accepted the message and passed it to Apple.")
        print(f"message id: {r.json().get('name')}")
    else:
        print(f"SEND FAILED: HTTP {r.status_code}")
        print(r.text.replace(token, "<push id>")[:3000])
        sys.exit(2)


if __name__ == "__main__":
    main()
