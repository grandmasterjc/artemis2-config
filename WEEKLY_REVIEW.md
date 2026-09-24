# Weekly article (Wednesdays)

The Wednesday routine researches, writes and commits the week's article draft
to `drafts/{article_id}/`, then presents it to the owner and waits. Nothing
here publishes anything. An earlier design had a separate cron generating the
draft for a reviewer to check; that cron is gone, and the routine now does
both jobs.

Writing rules are in `ARTICLE_STYLE.md`. This file covers angle selection,
images, publishing procedure and editing after publication.

## Procedure

1. Pull the latest `main` of `grandmasterjc/artemis2-config`. Read
   `ARTICLE_STYLE.md` in full before writing anything.
2. Check `state/publish_history.txt` and `drafts/` so you neither repeat a
   recent angle nor duplicate a draft someone already wrote this week. If a
   draft for this week already exists, review it instead of writing a new
   one, and say so.
3. Pick the topic from `FEATURE_IDEAS.md`: the highest-ranked idea with
   status `open`, following that file's rules. Research it with web searches,
   applying the editorial judgment list below, and verify key claims against
   primary sources. After writing, mark the idea `used` in the same commit.
4. Write `drafts/{article_id}/article_draft.md` plus a `hero.jpg`, following
   the spec and the image rules here. Run the spec's §8 pre-publish
   checklist against your own draft.
5. Commit and push the draft to `main`. Pushing a draft folder does not
   publish anything; only `weekly-article-publish.yml` does.
6. VERIFY the push actually landed on `main`, then report to the owner in
   Norwegian: the topic and why you picked it, a link to the draft
   on GitHub, the verification result, anything you were unsure about, and a
   question asking whether to publish. Do NOT run the publish workflow.
   The GitHub link to the article MUST appear in every report to the owner:
   the final chat reply and any notification alike. Never leave it out of
   either.

If any step fails, say so to the owner immediately and explain what broke.
Never end a run silently.

### Verify delivery, do not assume it

A routine-fired session's environment can be configured with an outcome
branch. When it is, an ordinary `git push` may go to that branch instead of
`main`, and nothing fails: the run is green, the commit exists, a draft pull
request may even be opened, and the draft is still nowhere the workflow or
the owner will find it.

This happened on Wednesday 2 September 2026. The routine fired at 07:15 UTC,
ran for 13 minutes, reported SUCCEEDED, and wrote a good article. It went to
`claude/eloquent-hawking-lwld4y` as draft PR #3. The owner spent a week
believing no article had been written.

After pushing, run:

    git fetch origin main
    git cat-file -e origin/main:drafts/{article_id}/article_draft.md && echo ON_MAIN

If that does not print `ON_MAIN`, the draft is NOT delivered. Say so to the
owner in plain words, and give the branch name and pull request link so the
draft can be brought over. Never report success because the commands exited
zero. A green run is not a delivered draft.

The same rule has bitten this project three other ways: a Kit broadcast
without `send_at` is silently saved as a draft and never sends; an empty
`state/spaceflight_history.json` logged 41 clean "skipped" runs; and Threads
posts lost to HTTP 500s were recorded as complete. Check the artifact, not
the exit code.

## Rule compliance (mechanical)

Writing rules live in `ARTICLE_STYLE.md`, which is the authority on voice,
structure, language, attribution, anti-tells, CTA copy and length. Read it
before reviewing a draft and run its §8 pre-publish checklist. Where this
file and the spec disagree, the spec wins. Its appendix explains how the
headline and dek map onto the draft's frontmatter.

Rules the spec does not cover, still enforced here:

- At most one inline image, mid-article (never at the top), with at least one
  text paragraph between the image and the next `## heading`. It must use a full
  absolute URL beginning `https://grandmasterjc.github.io/artemis2-config/updates/images/`
  and reference a file that already exists in `updates/images/`.
- Hero via frontmatter `hero_image: hero.jpg`, 1200×675, high quality
  (source at 1920px+ and downscale; never upscale a small image).
- Every article gets a DISTINCT hero: never reuse an image used as hero in
  any of the last ~10 articles (check `updates/images/` and recent
  manifest entries), even when covering the same running story. The owner
  flagged the same pad photo appearing three times in a row. Prefer fresh
  imagery from the actual event (SpaceX/NASA photos, webcast stills);
  vary the visual angle between installments of a story. The image must
  also MATCH the story's state — no liftoff photos on pre-launch pieces.
- Swapping an already-published image: always publish under a NEW
  filename (e.g. `{id}-v2.jpg`) and update the manifest's `hero_image` —
  replacing bytes at the same URL leaves app clients showing their
  cached copy of the old image indefinitely.
- Frontmatter: any value containing `:` is double-quoted; `push_title` quoted.

## Editorial judgment

- Format: the Wednesday article is an explanatory feature, written so it
  could run in a popular-science magazine such as Illustrert Vitenskap. It
  answers a question many readers already have (how does it work, why is it
  done this way, what happens to the body, how far along is it) with concrete
  numbers and clear explanation. The owner decided on 2026-09-23 to move away
  from news angles and critical framing: do not force a topic into "is
  NASA/SpaceX late or failing", and do not pick a story because it is
  contested. Where risks or delays are part of the answer, explain them
  evenly, as part of how the thing works.
- Timeliness is optional. A current event (a launch, a test, a new study) can
  open the article or move a lower idea up the list, but the article still
  answers the question rather than reporting the event. Run a few web
  searches for current news so nothing in the piece is out of date.
- Originality and value: does it teach the reader something concrete and
  non-obvious, or is it a generic recap? Prefer curiosity via concrete facts,
  numbers a reader can picture, and how-it-works explanation.
- Accuracy: are the key claims verifiable against primary sources? Read the
  sources where possible rather than trusting search snippets.
- Tone: nøkternt, no clickbait, no exclamation points, no emoji.
- Liftoff cross-promo: the owner promotes the companion app "Liftoff — Rocket &
  Space Launch" (App Store id6776392285) with a direct download link near the
  end. Include the current offer if one is running.

## Publishing (only after the owner approves)

Two-phase, so the article is verified visible before anyone is notified:

1. Make sure the approved draft is on current `main` (add only the draft
   folder; never overwrite the dashboard or log history).
2. Run `weekly-article-publish.yml` with `phase=prepare` (makes it live on
   GitHub Pages, no push).
3. Verify the manifest entry, body `.md`, hero and inline image are all live
   (HTTP 200), then let the owner check it in the app.
4. On the owner's go-ahead, run the same workflow with `phase=announce`
   (FCM push + Kit newsletter + Bluesky/Mastodon/Threads).

After publishing, add at least one new idea to `FEATURE_IDEAS.md`, in the
same format as the existing entries and placed where it belongs in the
ranking, so the bank grows as fast as it is used. A good source is a
question the published article raised but did not answer. Mention the new
idea in the report to the owner.

Also after publishing: check how the previous week's social posts performed and
append learnings to `SOCIAL_PLAYBOOK.md` (metrics how-to at the bottom of
that file). Threads must be read manually by the owner — ask for the numbers.

## Editing an article after publication

The live body at `updates/articles/{id}.md` must never be produced by
copying the draft. It carries no frontmatter, because GitHub Pages runs
Jekyll and any file with frontmatter is converted to HTML, which makes the
`.md` URL the apps fetch return 404. This took an article offline for about
20 minutes on 2026-07-28.

An edit to a published article means three files, or the app shows a
mismatch: the draft, `updates/articles/{id}.md` (body prose only), and the
`title` / `subtitle` / `summary` fields for that article in
`updates/manifest.json`.

Verification after any publish or edit MUST check content, not just the
HTTP status code. Fetch the article URL and grep for a phrase that only
exists in the new text. A 404 page can return quickly enough to look like
a healthy response in a status-only check.

Push notifications, social posts and a scheduled Kit newsletter cannot be
recalled once announce has run. Finish text edits during the prepare phase.

Communication: Norwegian for owner comms, English for content. For yes/no
questions, answer yes/no.
