# GitHub Secrets — Required for Workflows

All cron jobs run as GitHub Actions workflows. Credentials must be set as repository
Secrets at:

https://github.com/grandmasterjc/artemis2-config/settings/secrets/actions

## Required Secrets

| Secret | Used by | Format |
|---|---|---|
| `BLUESKY_HANDLE` | bluesky-daily-history, weekly-article-publish | `artemistracker.app` |
| `BLUESKY_PASSWORD` | bluesky-daily-history, weekly-article-publish | App password (4 dash-separated groups) |
| `MASTODON_INSTANCE` | weekly-article-publish | `spacey.space` |
| `MASTODON_ACCESS_TOKEN` | weekly-article-publish | Long access token from spacey.space → Preferences → Development |
| `KIT_API_KEY` | dashboard-refresh, weekly-article-publish | `kit_xxxxxxxxxxxxx` |
| `GOOGLE_APPLICATION_CREDENTIALS_JSON` | dashboard-refresh | Entire JSON contents (paste raw, including outer `{...}`) — must include `analytics.readonly` scope |
| `GOOGLE_ANALYTICS_PROPERTY_ID` | dashboard-refresh | `531732958` |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | weekly-article-publish | Entire JSON contents of artemis-tracker-665d8 service account |
| `THREADS_ACCESS_TOKEN` | threads-token-refresh | Optional. Long-lived Threads API token |
| `APP_STORE_CONNECT_KEY_ID` | dashboard-refresh | App Store Connect API key ID (e.g. `UQ6P8VG963`). Generate at https://appstoreconnect.apple.com/access/integrations/api with Finance role. |
| `APP_STORE_CONNECT_ISSUER_ID` | dashboard-refresh | Issuer UUID from the same page (shared across all keys). |
| `APP_STORE_CONNECT_PRIVATE_KEY` | dashboard-refresh | Full PEM contents of the `.p8` file (paste raw, including `-----BEGIN PRIVATE KEY-----` and `-----END PRIVATE KEY-----`). |
| `APP_STORE_CONNECT_VENDOR_NUMBER` | dashboard-refresh | Apple vendor number from App Store Connect → Payments and Financial Reports (e.g. `85037504`). |
| `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` | dashboard-refresh | Full JSON contents of the `play-console-reporting` service account key. The service account must be invited to Play Console with global "View app information and download bulk reports" + "View financial data" permissions. |
| `GOOGLE_PLAY_REPORTS_BUCKET` | dashboard-refresh | Cloud Storage bucket ID from Play Console → Download reports → Financial (e.g. `pubsite_prod_6157935083484095024`, without `gs://`). |
| `GOOGLE_PLAY_PACKAGE` | dashboard-refresh | Android package name (e.g. `no.bitfactory.artemisii.tracker`). Defaults to this if unset. |

## Step-by-step: Adding a secret

1. Go to https://github.com/grandmasterjc/artemis2-config/settings/secrets/actions
2. Click "New repository secret"
3. Name: exactly as in the table above (case sensitive)
4. Value: paste the secret
5. Click "Add secret"

## Format examples

### BLUESKY_PASSWORD
```
k4vm-bqlu-efil-hjlh
```

### MASTODON_INSTANCE
```
spacey.space
```
(no `https://`, no trailing slash)

### GOOGLE_APPLICATION_CREDENTIALS_JSON
Paste the entire JSON file contents starting with `{` and ending with `}`. No quotes around it.

The service account needs:
- Role: `Viewer` on the GA4 property (Admin > Property access > Add user)
- Service account email format: `xxx@project.iam.gserviceaccount.com`

### FIREBASE_SERVICE_ACCOUNT_JSON
Same format as Google: entire JSON contents. Get from Firebase Console → Project Settings → Service accounts → Generate new private key.

## Workflow trigger times (UTC)

| Workflow | Cron | UTC time | CEST time |
|---|---|---|---|
| Dashboard refresh | `0 5 * * *` | 05:00 daily | 07:00 |
| Bluesky daily history | `0 5 * * *` | 05:00 daily | 07:00 |
| Threads token refresh | `0 7 1 * *` | 07:00 on 1st of month | 09:00 |
| Weekly article publish | manual (`workflow_dispatch`) | — | — |

## Manual triggers

To run a workflow manually:

1. Go to https://github.com/grandmasterjc/artemis2-config/actions
2. Pick the workflow
3. Click "Run workflow" (right side)
4. For weekly-article-publish: enter the `article_id` (kebab-case, must match `drafts/{id}/`)

## Weekly publish workflow

Because article drafting needs AI + web search, the draft step still runs in Perplexity:

1. Wednesday morning, Perplexity generates draft and commits it to `drafts/{article_id}/article_draft.md` + `drafts/{article_id}/hero.jpg`
2. You review the draft (notification from Perplexity)
3. At 18:30 CEST (or whenever you're ready), trigger weekly-article-publish workflow manually with the article_id
4. Workflow: copies assets → updates manifest → FCM push → schedules Kit newsletter → posts to Bluesky + Mastodon

## Threads token refresh

Threads tokens last 60 days. The workflow runs monthly to refresh. **Important:** the workflow cannot write back to GitHub Secrets. It only logs whether the refresh succeeded. To rotate:

1. Workflow runs on the 1st, refreshes the token
2. New token is visible in the workflow logs (last 6 chars only)
3. Get the full new token from your Threads API user token generator if needed
4. Manually update `THREADS_ACCESS_TOKEN` secret

(In practice, Threads is currently disabled in the publish flow, so this is precautionary.)
