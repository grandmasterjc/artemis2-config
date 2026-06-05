# Credentials & Secrets Restore Guide

The cron scripts in `scripts/` need several credentials that MUST NOT be committed to the repo. The Perplexity sandbox gets wiped between sessions, so credentials need to be re-uploaded to `/home/user/workspace/` at the start of any session where you want to run a cron manually, or when the sandbox is fresh.

For scheduled cron runs the credentials are expected to live in `/home/user/workspace/`. The scripts read them from there and never from the repo.

## Files the scripts expect in /home/user/workspace/

| File | Used by | How to regenerate |
| --- | --- | --- |
| `artemis-tracker-665d8-firebase-adminsdk-*.json` | `send_push.py` | Firebase Console → Project Settings → Service accounts → Generate new private key. The suffix rotates; `send_push.py` auto-detects via glob. |
| `kit_config.json` | publish + week ahead | Kit dashboard → Account → API. Contents: `{"api_key":"kit_...","base_url":"https://api.kit.com/v4"}` |
| `bluesky_config.json` | bluesky scripts | bsky.app → Settings → App passwords. Contents: `{"handle":"artemistracker.app","app_password":"xxxx-xxxx-xxxx-xxxx"}` |
| `mastodon_config.json` | social publish | spacey.space → Preferences → Development → New application. Contents: `{"base_url":"https://spacey.space","access_token":"..."}` |
| `threads_config.json` | threads (currently disabled) | developers.facebook.com → Artemis Tracker app → Threads API. |

## Quick check

```bash
ls /home/user/workspace/*.json /home/user/workspace/artemis-tracker-*-firebase-*.json 2>/dev/null
```

If you see all five files, you are good. If not, re-upload the missing ones.

## Long-term: GitHub Actions

The real fix is to move these crons out of the Perplexity sandbox entirely and into GitHub Actions with Secrets. That removes the wipe problem and makes the whole stack reproducible. Tracked as a follow-up.
