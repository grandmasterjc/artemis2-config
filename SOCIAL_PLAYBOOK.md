# Social posting — learnings log

Working notes on what performs across channels, so future posting sessions
build on data instead of starting over. Update after each review of post
performance. Metrics for Bluesky/Mastodon are public APIs; Threads numbers
must be read manually in the app (no public API).

## Snapshot 2026-07-16

Six weekly-article posts published since June 9.

| Channel | Followers | Engagement across all posts | Notes |
| --- | --- | --- | --- |
| Threads | n/a (manual) | Best channel by far. Peak so far: 3,000 views / 50 likes / 35 comments on the July 28 debate post | Publishing has worked since July 1, so STRATEGY.md listing it as Meta-blocked is outdated |
| Bluesky | 8 | 0 likes, 0 reposts | The "2 replies" on every post are the bot's own thread (link + first paragraph) |
| Mastodon (spacey.space) | 1 | 1 favourite total | Effectively no audience yet |

## Best post so far: 2026-07-28, the crewed-Starship debate

Threads, measured 8 hours after posting: **3,000 views, 50 likes, 35 comments,
2 reposts.** By a wide margin the best result the account has had. Worth
studying rather than admiring, because most of it is reproducible.

Post text was the article's headline and dek verbatim, hero image attached,
first reply carrying the article's opening line, article link in the second
reply.

### Why it worked

1. **It entered an argument instead of reporting an event.** Every previous
   post announced something that had happened. This one took a position in a
   dispute the audience was already having. People comment to disagree, far
   more than they comment to acknowledge news.
2. **The source material was a comment thread.** The article came from an
   actual argument the owner found under someone else's post. That means the
   audience for it was already assembled and already worked up. This is a
   repeatable research method, not a lucky find.
3. **The headline states a contested claim, not a summary.** "Too heavy, too
   complicated, too risky: the case against a crewed Starship" reads as a
   position someone can push back on. Whose position it is stays slightly
   open, which pulls people in to correct it.
4. **The dek asks a direct question.** "Can Starship really carry people?" A
   question invites an answer, and an answer is a comment.
5. **The post does not resolve the argument.** The correction lives in the
   article. Anyone who wants to settle it in the feed has to write something.
6. **Timing.** Posted while Starship attention was still high after Flight 13.

### The recipe

- Mine comment sections, forums and replies for what people are actually
  arguing about in the Artemis and Starship space. Look for a claim that is
  confidently repeated and partly wrong.
- Write the article as a straight fact-check of that claim, with the
  correction earned through evidence rather than asserted in the first line.
- Headline the contested claim. Do not headline the verdict.
- Put a direct question in the dek.
- Let the post text be headline plus dek, with the plainest statement of the
  argument as the first reply.
- Post while the underlying news is still warm.

### Follow-up 2026-08-03: the engagement did not convert

The caveat below turned out to be the whole story. Subscriber counts from the
dashboard log, comparing the days before and after each publication:

| Publication | Newsletter | Artemis+ | Total |
| --- | --- | --- | --- |
| Jul 15, heat shield article | +0 | +1 | +1 |
| Jul 17, pad abort | +1 | +2 | +3 |
| Jul 23 to 25, Flight 13 coverage | +2 | +1 | +3 |
| **Jul 28, the debate post (3,000 views)** | **+0** | **+0** | **+0** |

The post with by far the most reach produced no measurable signups. The
straight news coverage, with a fraction of the engagement, converted every
time.

Read this as a signal, not a law. The numbers are tiny, one day is missing
from the series (Jul 24), and subscriptions cannot be attributed to a
specific source with the instrumentation that exists. But the pattern is
consistent across three news posts and one debate post, and it points at
something plausible: an argument attracts people who want to argue, while a
launch report attracts people who want to be told when the next one is.

What this does not mean is that the format was a mistake. Reach compounds,
followers gained today convert later, and the account needs an audience
before it can convert one. It does mean the format should not replace news
coverage, and that claiming it "works" on comment count alone was premature.

### What we cannot measure, and should fix

There is no analytics on artemistracker.app at all. No GA4 tag, no beacon,
nothing. So the question "how many actually read the article" has no answer
and will not have one until something is installed. Cloudflare Web Analytics
is the obvious candidate: free, cookie-less, no consent banner needed, and
the domain is already on Cloudflare for the unlock worker.

Social posts link to `artemistracker.app/u/{id}` with no source parameter, so
even with analytics the channels could not be told apart. Adding `?ref=threads`
and so on to the links in `social_publish.py` costs nothing and should happen
at the same time.

`state/subscribers_history.csv` in the repo has been frozen since 2026-06-17,
even though `dashboard_refresh` logs a fresh row every morning. The daily
numbers used in the table above had to be scraped back out of
`state/dashboard_refresh_log.txt`. The refresh writes the row somewhere the
commit step does not pick up. Worth fixing, because the log is not a database.

### Honest caveat

Comment volume on a debate post is partly people arguing without reading. It
is real reach and real algorithmic lift, but it is not proof of readership.
The conversion signal to watch is app installs and newsletter signups in the
days after, not the comment count. Check both before concluding this format
converts as well as it engages.

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
