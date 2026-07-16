# Social posting — learnings log

Working notes on what performs across channels, so future posting sessions
build on data instead of starting over. Update after each review of post
performance. Metrics for Bluesky/Mastodon are public APIs; Threads numbers
must be read manually in the app (no public API).

## Snapshot 2026-07-16

Six weekly-article posts published since June 9.

| Channel | Followers | Engagement across all posts | Notes |
| --- | --- | --- | --- |
| Threads | n/a (manual) | Good — July 15 post got notably strong response (owner observation) | Best-performing channel despite STRATEGY.md listing it as blocked; it has been posting successfully since July 1 |
| Bluesky | 8 | 0 likes, 0 reposts | The "2 replies" on every post are the bot's own thread (link + first paragraph) |
| Mastodon (spacey.space) | 1 | 1 favourite total | Effectively no audience yet |

## What we learned

1. **Threads is the channel that works.** Real engagement, and it is not even
   on the strategy target sheet yet (listed as Meta-verification-blocked,
   which is outdated — publishing has worked since July 1). Treat it as the
   primary social channel and update STRATEGY.md targets accordingly.
2. **Every link posted before July 16 was dead.** All posts CTA'd to
   `https://artemistracker.app/u/{id}`, but the domain served nothing until
   the website went live on 2026-07-16. Five weeks of posts pointed nowhere.
   Those links now work retroactively. Post-website engagement is the first
   clean signal — do not judge the pre-July-16 link CTR as audience failure.
3. **Threads publishing is flaky.** June 24: HTTP 500 from
   `threads_publish` (no retry in script). July 8: no Threads permalink
   logged at all. 2 of 5 attempts since June 24 produced no post. A single
   retry with backoff in `scripts/social_publish.py` would likely have
   recovered both.
4. **Zero distribution mechanics on the fediverse/Bluesky.** Posts carry no
   hashtags (no facets on Bluesky, no tags on Mastodon). Mastodon discovery
   is almost entirely hashtag-driven, and Bluesky custom feeds pick up tags
   and keywords. With 8 and 1 followers, posts without tags reach nobody.
5. **Format is consistent and on-tone:** title + subtitle + hero image,
   link in first self-reply. Keep the nøkternt tone; the format itself is
   not the problem on the quiet channels — reach is.

## Recommended next actions (owner to approve)

- [ ] Add retry-with-backoff around the Threads publish call and fail the
      workflow step loudly when a channel silently produces no permalink.
- [ ] Add hashtags: Mastodon (`#Artemis #NASA #Moon #Spaceflight`) and
      Bluesky tag facets on the main post. Keep to 3–4, no hashtag walls.
- [ ] Update STRATEGY.md: Threads is unblocked and is the best-performing
      channel — give it a follower/engagement target on the August sheet.
- [ ] Bluesky/Mastodon audience building is a separate task from posting:
      follow the space community, reply where relevant, get the account
      into Bluesky space feeds. Posting alone will not grow 8 → 750.
- [ ] Check Threads metrics manually each Wednesday (views, likes, replies)
      and append a line to the snapshot table here — it is the only channel
      without an API we can read.

## How to re-run this check

- Bluesky metrics: `https://public.api.bsky.app/xrpc/app.bsky.feed.getPosts?uris=...`
  (URIs in `state/social_post_history.csv`); profile via `app.bsky.actor.getProfile`.
- Mastodon metrics: `https://spacey.space/api/v1/statuses/{id}`.
- Threads: open the posts in the Threads app (permalinks in the CSV).
