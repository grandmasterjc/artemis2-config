# api.artemistracker.app — web unlock worker

`web-unlock.js` is the Cloudflare Worker that lets Artemis Plus buyers read
premium articles on artemistracker.app. See the header comment in the file
for the full flow.

## Deploying (one-time, ~5 minutes in the Cloudflare dashboard)

The existing api.artemistracker.app worker (feedback + newsletter) is not in
this repo, so deploy this as a **separate worker** scoped to its own routes —
Cloudflare routes are path-specific, so the two coexist on the same hostname.

1. Cloudflare dashboard → Workers & Pages → **Create worker**, name it
   `artemis-web-unlock`, paste the contents of `web-unlock.js`, Deploy.
2. Worker → Settings → **Variables and Secrets** — add two secrets:
   - `RC_SECRET_KEY` — RevenueCat secret API key
     (RevenueCat dashboard → Project → API keys → Secret key, `sk_...`)
   - `UNLOCK_SIGNING_SECRET` — any long random string
     (`openssl rand -hex 32`)
3. Worker → Settings → **Domains & Routes → Add route** (zone artemistracker.app):
   - `api.artemistracker.app/web-unlock*`
   - `api.artemistracker.app/web-verify*`

## Testing

- Non-subscriber / bad ID:
  `https://api.artemistracker.app/web-unlock?uid=nosuchuser`
  → should redirect to `https://artemistracker.app/unlock#t=denied`
- From the app: profile/settings → "Read premium on the web" (added in app
  version 2.4.x) → browser should land on artemistracker.app showing
  "Web access unlocked".

## Notes

- Entitlement checked: `artemis_pro` (same as the apps).
- Tokens live 30 days (`TOKEN_TTL_DAYS`), then the user taps the app button
  again. Shortening the TTL forces more frequent re-checks against
  RevenueCat (i.e. faster revocation after a cancelled subscription).
- The website only *renders* premium bodies after `/web-verify` says the
  token is valid. The raw markdown remains publicly fetchable from this
  repo; moving premium bodies behind the worker is the eventual hard fix.
