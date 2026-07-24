#!/usr/bin/env python3
"""Post free-form text to Threads (optionally with a reply under it).

Used by threads-text-post.yml for hand-written posts that don't come from
an article draft. Text comes from env vars to avoid shell-quoting issues:

  POST_TEXT   required, max 500 chars (Threads limit)
  REPLY_TEXT  optional, max 500 chars; posted as a reply to the main post

Reuses the container/publish helpers (incl. the 5xx retry) from
social_publish.py.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from social_publish import (  # noqa: E402
    load_threads,
    threads_create_container,
    threads_publish,
    threads_permalink,
)


def main():
    text = os.environ.get("POST_TEXT", "").strip()
    reply = os.environ.get("REPLY_TEXT", "").strip()
    if not text:
        print("POST_TEXT is required", file=sys.stderr)
        sys.exit(2)
    for name, value in (("POST_TEXT", text), ("REPLY_TEXT", reply)):
        if len(value) > 500:
            print(f"{name} is {len(value)} chars (Threads limit is 500)", file=sys.stderr)
            sys.exit(2)

    cfg = load_threads()
    user_id = cfg["user_id"]
    token = cfg["access_token"]

    head_container = threads_create_container(user_id, token, text=text, media_type="TEXT")
    time.sleep(5)
    head_id = threads_publish(user_id, token, head_container)

    if reply:
        reply_container = threads_create_container(
            user_id, token, text=reply, media_type="TEXT", reply_to_id=head_id
        )
        time.sleep(2)
        threads_publish(user_id, token, reply_container)

    permalink = threads_permalink(token, head_id) or f"threads:{head_id}"
    print(permalink)


if __name__ == "__main__":
    main()
