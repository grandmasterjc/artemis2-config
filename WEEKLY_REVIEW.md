# Weekly draft review (Wednesdays)

The Wednesday cron (`4c5bb4d0`) generates a fresh weekly-article draft in
`drafts/{article_id}/` (an `article_draft.md` plus a `hero.jpg`) and commits it
to `main`. This document is the checklist an agent session runs each Wednesday
to read that draft and decide whether it is worth publishing as-is, editing, or
replacing with a fresher angle. Nothing here publishes anything — the review
ends with a recommendation and waits for the owner's decision.

## Procedure

1. Pull the latest `main` of `grandmasterjc/artemis2-config`.
2. Find the newest draft: the folder in `drafts/` dated today, or the most
   recent draft whose `id` is not already in `state/publish_history.txt`.
   Ignore `drafts/week-ahead/`.
3. Read the draft in full.
4. Check it against both the rule compliance list and the editorial judgment
   list below.
5. Report a concise assessment to the owner (in Norwegian): any rule issues,
   whether the angle is genuinely current for this week, and a clear
   recommendation — publish as-is, edit (list the specific edits), or write a
   fresher angle (propose one or two). Do NOT publish, push, or send anything.

## Rule compliance (mechanical)

- 800–1200 words in the body (Wednesday article), excluding frontmatter.
- 4–8 `##` headings.
- First 4 paragraphs are a free hook; ends with a "what to watch next" or
  "where this leaves us" section.
- Required inline CTA after paragraph 3:
  `Get the next briefing in your inbox. [Subscribe free →](https://artemis-briefing.kit.com)`
  (paraphrase acceptable; keep the link and the "Subscribe" phrasing).
- Required footer CTA linking to `https://artemis-briefing.kit.com` with
  "Subscribe" phrasing, framed as the free email edition.
- No markdown tables (use bullet lists).
- No italic markers (`*text*` / `_text_`) anywhere; no bold inside quotes.
- Quotes: plain text with quotation marks; the owner prefers no inline source
  citations like "(NASA, date)" in the body — attribute in prose or omit.
- At most one inline image, mid-article (never at the top), with at least one
  text paragraph between the image and the next `## heading`. It must use a full
  absolute URL beginning `https://grandmasterjc.github.io/artemis2-config/updates/images/`
  and reference a file that already exists in `updates/images/`.
- Hero via frontmatter `hero_image: hero.jpg`, 1200×675.
- Frontmatter: any value containing `:` is double-quoted; `push_title` quoted.

## Editorial judgment

- Currency: run a few web searches for this week's Artemis / Moon / launch
  news. Is the draft's angle genuinely current, or has the cron reused an old
  or stale hook? The owner has rejected stale angles before — flag it.
- Originality and value: does it say something concrete and non-obvious, or is
  it a generic recap? Prefer curiosity via concrete facts.
- Accuracy: are the key claims verifiable against primary sources? Read the
  sources where possible rather than trusting search snippets.
- Tone: nøkternt, no clickbait, no exclamation points, no emoji.
- Liftoff cross-promo: the owner promotes the companion app "Liftoff — Rocket &
  Space Launch" (App Store id6776392285) with a direct download link near the
  end. Include the current offer if one is running.

## Publishing (only after the owner approves)

Two-phase, so the article is verified visible before anyone is notified:

1. Bring the approved draft onto current `main` (add only the draft folder;
   never overwrite the cron/dashboard history).
2. Run `weekly-article-publish.yml` with `phase=prepare` (makes it live on
   GitHub Pages, no push).
3. Verify the manifest entry, body `.md`, hero and inline image are all live
   (HTTP 200), then let the owner check it in the app.
4. On the owner's go-ahead, run the same workflow with `phase=announce`
   (FCM push + Kit newsletter + Bluesky/Mastodon/Threads).

Communication: Norwegian for owner comms, English for content. For yes/no
questions, answer yes/no.
