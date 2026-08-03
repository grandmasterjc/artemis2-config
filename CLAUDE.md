# artemis2-config

Content and delivery backend for Artemis Mission Tracker (iOS and Android)
and the Artemis Briefing newsletter. GitHub Pages serves this repo at
https://artemistracker.app, which is also the marketing site and the public
reader for articles.

## Writing articles

`ARTICLE_STYLE.md` is the authority on how articles are written: voice,
structure, language, attribution, anti-tells, CTA copy and length. Read it in
full before drafting or editing any article, and run its §8 pre-publish
checklist before calling a draft done. Its appendix covers repo plumbing,
including which parts of an article live in frontmatter rather than the body.

## Reviewing and publishing

`WEEKLY_REVIEW.md` covers the Wednesday draft review, image rules, the
two-phase publishing procedure, and what to do when editing an article that
is already live. Read it before running any publishing workflow.

Nothing is ever published or announced without the owner's explicit
go-ahead. Publishing is two-phase: `phase=prepare` makes the article live and
verifiable, `phase=announce` sends the push notification, newsletter and
social posts. Announce cannot be undone.

## Week Ahead (Sunday newsletter)

Written by the Sunday routine into `drafts/week-ahead/YYYY-MM-DD.md`.
Sending is triggered by the push itself, not by running a workflow, because
routine-fired sessions have neither the GitHub Actions tool nor the Kit
credentials.

A draft is sent only if its frontmatter carries `autosend: true` and its path
is not already in `state/week_ahead_sent.txt`. Without the flag it stays a
draft, which is the right default for anything written by hand or still in
progress. The workflow schedules the Kit broadcast for 18:00 CEST the same
day, leaving a window to intervene, and appends the path to the sent log.

`weekly-article-publish.yml` is unaffected. The Wednesday article still
publishes in two explicit phases and still requires the owner's go-ahead.

## Social

`SOCIAL_PLAYBOOK.md` holds channel performance notes and how to re-run the
metrics check. Threads is the best-performing channel and has no public
metrics API, so those numbers come from the owner.

## Communication

Norwegian for messages to the owner, English for all published content. For
yes/no questions, answer yes or no.
