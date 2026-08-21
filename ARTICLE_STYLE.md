# Artemis Briefing: Article Style Spec

Spec for generating long-form articles for the Artemis Briefing newsletter and app. Written to be consumed by Claude Code: reference it from `CLAUDE.md` or include it directly in the generation prompt. Rules marked MUST are hard requirements; SHOULD rules may be broken with good reason.

## 1. Voice

Write like a staff writer at Space.com: a human science journalist producing a news feature. Knowledgeable, factual, engaged but never breathless. The reader should feel informed by a reporter, not persuaded by an essayist. Explanatory journalism, not opinion writing. When the article makes an argument, route it through evidence and attribution rather than rhetoric.

## 2. Structure (in this order)

1. **Headline**: H1, sentence case, a concrete claim rather than a teaser. Good: "Starship won't fly astronauts home from the moon, and it was never supposed to." Bad: "The Starship myth everyone keeps repeating."
2. **Dek**: 1–2 italic sentences under the headline stating the stakes.
3. **Lede**: opens on a news hook (a recent flight, report, or announcement).
4. **Nut graf**: within the first 3–4 paragraphs, state why this matters and what the article will show, with at least one named source.
5. **CTA 1** (see §6).
6. **Body**: 4–6 sections under H2 subheads.
7. **A forward-looking section** near the end: concrete upcoming milestones. The section is required; the wording of its heading is not, and SHOULD vary between articles ("Five milestones to watch", "Dates already on the calendar"). Reusing the literal heading "What to watch" every week is a house tic worth breaking.
8. **Conclusion**: circles back to the lede in 1–2 paragraphs. No aphorism, no grand final line.
9. **CTA 2 and CTA 3** (see §6).

Subheads MUST be descriptive of the section's content ("How the Artemis landing plan actually works"), never punchlines or mini-theses ("Nobody was ever going to ride it home"). They MUST also vary in grammatical form across the article; see the subhead rule in §5.

## 3. Language

- American English spelling (center, traveled, canceled).
- Lowercase "moon"; Arabic numerals for missions: Artemis 3, not Artemis III.
- Give measurements in both systems on first mention: "115 feet (35 meters)."
- Expand acronyms on first use with the acronym in parentheses: "Office of Inspector General (OIG)."
- Contractions are allowed and encouraged in moderation (it's, won't, doesn't).
- Numerals for 10 and above; spell out one through nine except in measurements, percentages, and counts paired with units.

## 4. Facts and attribution

- Every non-obvious claim MUST be attributed to a named source (NASA OIG, GAO, a SpaceX statement, a specific report) or be common knowledge in the field. No free-floating "critics say" beyond framing the debate itself.
- NEVER fabricate quotes. Direct quotes only if verbatim from provided source material; otherwise paraphrase with attribution.
- Phrase time-sensitive facts so they survive publication delay. Good: "has slipped by more than a year from its original March 2025 target and has yet to fly." Bad: "is scheduled for March 2026" (goes stale, may already be false at publish time).
- Before finalizing, check every date against the publication date. A "planned" event whose date has passed MUST be re-verified or rephrased.
- Distinguish plans from achievements. "SpaceX aims to" ≠ "SpaceX will."

## 5. Anti-tells (hard rules)

These patterns read as machine-generated. Caps are per article.

- MUST NOT use aphoristic one-line closers ("Each one converts an argument into data.").
- MUST NOT use "It's not X. It's Y." / "The interesting part isn't A. It's B." constructions.
- MUST NOT include meta-commentary that sorts the piece into parts ("the argument comes apart into three pieces").
- Max 1 sentence-fragment run for effect ("Too heavy, too complicated, too risky."), acceptable only when voicing someone else's argument.
- Max 2 tricolons (three parallel items in a row) in the whole article.
- MUST NOT use em dashes (—) anywhere in the headline, dek or body. Rewrite
  with a comma, a colon, parentheses or a separate sentence. The only
  exception is a proper name that contains one, such as the App Store title
  "Liftoff — Rocket & Space Launch".
- Subheads MUST vary in grammatical form. At most ONE H2 per article may
  open with an interrogative stem (What, Why, How, Where); the rest must be
  concrete noun phrases or plain declaratives. A stack of "What X actually
  says / Why Y still matters / What to watch" is one of the strongest
  machine-written tells in this format, and it survives every other check in
  this spec because each subhead is individually fine. Judge the list as a
  list, not line by line.
  - Good, from published editions: "Five engines where thirteen should have
    been", "The Ship that lived to float", "The Artemis line item", "The
    rocket equation is why the plan looks like this", "Two landers, one
    broken pad".
  - Bad, from a rejected draft: "What the memorandum actually orders", "What
    NASA's schedule actually says", "Why a transportation policy still
    matters", "What has to happen for 2028 to hold", "What to watch".
  - A subhead MUST NOT restate its own section's opening sentence. If the
    first line reads "Three things have to go right," the subhead is not
    "Three things that have to go right."
- Vary rhythm: mix long explanatory sentences with short ones; paragraphs of 1–4 sentences; no two consecutive paragraphs opening with the same word.
- Avoid stock AI vocabulary: delve, landscape, testament to, boasts, crucial (max once), "it's worth noting," "in conclusion," "at the end of the day."

Reference pair from a published edit:

- Before: "SpaceX did not find a way around that. It designed around it."
- After: "SpaceX didn't find a way around that. Instead, the company designed the mission so the problem lands somewhere else: HLS doesn't launch with full tanks."

## 6. CTAs (exact copy and placement)

Three CTAs per article, nowhere else, wording fixed except links:

**CTA 1**: after the nut graf, before the first H2, on its own line in bold:

> **Get the next briefing in your inbox. [Subscribe free →](URL)**

**CTA 2**: final section, first closing paragraph:

> If you want to follow the flights that answer these questions as they happen, that is what our companion app Liftoff is built for. Live countdowns, real-time status and one-tap access to the official webcasts for every launch worldwide, free on the App Store: [Liftoff — Rocket & Space Launch](URL).

The first sentence of CTA 2 MAY be adapted to the article's topic; the rest is fixed.

**CTA 3**: last paragraph of the article:

> Want more than the weekly briefing? The free email edition adds a short "Week Ahead" every Sunday, launch windows and milestones to watch, exclusive to email. [Subscribe to the Artemis Briefing →](URL)

## 7. Length and formatting

- 900–1,300 words excluding CTAs.
- Markdown. H1 for the headline only, H2 for subheads, no deeper nesting.
- Body is prose. No bullet lists unless the content is genuinely enumerable (e.g. a checklist); milestone lists SHOULD be written as prose ("in roughly this order: A, B, C and D").
- No tables, no bold mid-sentence for emphasis.

## 8. Pre-publish checklist

Run before output is considered done:

- [ ] Every date checked against today's date; no stale "upcoming" events
- [ ] Every non-obvious claim attributed; zero fabricated quotes
- [ ] All three CTAs present, correct copy, correct placement, no extras
- [ ] Subheads descriptive, not punchlines
- [ ] Subheads read as a list: ≤1 interrogative stem, forms varied, none restating its own opening line
- [ ] Anti-tell caps respected (§5): fragments ≤1, tricolons ≤2, zero em dashes
- [ ] Banned-vocabulary scan clean
- [ ] Units doubled, acronyms expanded, American spelling
- [ ] Word count within 900–1,300

---

## Appendix: how this spec maps onto this repo

Repo-specific plumbing. The spec above is the authority on writing; this
appendix only explains where each piece physically goes.

- The **H1 headline** and the **italic dek** are not written into the body.
  They go in the draft's YAML frontmatter as `title:` and `subtitle:`. The app
  and the website render them above the body. Any value containing `:` must be
  double-quoted.
- Frontmatter also carries `id`, `date`, `mission`, `premium`, `hero_image`,
  `push_title` and `push_body`. Push copy is not covered by the spec; keep it
  to one line each and consistent with the headline and dek.
- **CTA 1** is bold on its own line per §6. In this repo it is conventionally
  wrapped in `---` divider lines above and below, which is how the newsletter
  template renders it as a separated block. Keep the dividers.
- The live article body at `updates/articles/{id}.md` carries **no
  frontmatter**. GitHub Pages runs Jekyll, which converts any file that has
  frontmatter into HTML and makes the `.md` URL the apps fetch return 404.
  Never create or update that file by copying the draft; `weekly_publish.py`
  writes it correctly, and manual edits must touch body prose only.
- Editing an already-published article means updating three places or the app
  will show a mismatch: the draft, `updates/articles/{id}.md`, and the
  `title` / `subtitle` / `summary` fields of that article's entry in
  `updates/manifest.json`.
- Images are outside the spec's scope and governed by `WEEKLY_REVIEW.md`:
  hero 1200×675 sourced at 1920px or better, distinct from the last ten
  articles, relevant to the story's state, and swapped only under a new
  filename so client caches pick it up.
