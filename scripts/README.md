# scripts/

Permanent home for all Artemis Tracker cron scripts. Each cron clones this repo first and runs scripts from here instead of relying on the ephemeral Perplexity workspace.

## Pattern for every cron

```bash
cd /tmp && rm -rf artemis_config_cleanup
git clone https://github.com/grandmasterjc/artemis2-config.git artemis_config_cleanup
cd /tmp/artemis_config_cleanup
python3 scripts/<script_name>.py
```

Credentials still live in `/home/user/workspace/` (see `../SECRETS.md`). The scripts read them from there.

## Scripts

| Script | Cron | What it does |
| --- | --- | --- |
| `send_push.py` | (called by publish) | Sends FCM v1 push to the `all` topic. Auto-detects Firebase service account in workspace. |
| `kit_template.py` | (lib, imported) | Builds HTML newsletter for Kit broadcasts. |
| `social_publish.py` | (called by publish) | Posts thread to Bluesky + Mastodon. |
| `bluesky_daily_history.py` | 1d711657 | Posts "on this day in spaceflight" if entry exists for today. |
| `bluesky_news_post.py` | 0e1dc7e4 | Posts a curated news commentary 4×/week. |
| `week_ahead_generator.py` | e263fe17 | Builds the Sunday Week Ahead newsletter draft. |
| `dashboard_data.py` + `dashboard_render.py` | 7306836a | Builds the public dashboard HTML. |
| `push_backfill_run.py` | 8aa23237 | Backfills GA4 stats into `state/push_history.csv`. |

## State

State files (CSVs, JSONs that the scripts read/write) live in `../state/`. They ARE committed so each cron run has the latest counts and history.

Things that are NOT in state and never should be:
- Secrets (see SECRETS.md)
- Article drafts (those live in updates/articles/)
- Hero images (those live in updates/images/)
