# Artemis Tracker — Strategy

Owner: Joachim Gresslien (Orbital Momentum AS)
Last updated: 2026-06-13

## North Star

**Artemis Mission Tracker shall be the definitive app for following NASA's Artemis program.**

A user who wants to know what is happening with Artemis — crew, hardware, schedule, lander progress, mission events — should open this app first and find what they need without going to NASA, Spaceflight Now, or social media.

## The installed base

Roughly 52,000 lifetime installs across platforms:
- iOS: ~50,000 installs (long-tenured listing, App Store visibility built up)
- Android: ~2,000 installs (launched later, still building)

That installed base is the asset the rest of the strategy is built on. Most of it is dormant — only ~130 of those people open the app on a given day. Waking up a larger share of that base, and keeping them coming back, is the primary work.

New acquisition still matters, and it will accelerate on its own around real events. Artemis III in 2027 and the first Moon Base I mission in late 2026 will drive search traffic; the planned Artemis IV landing will be the largest acquisition window this product ever sees. The job is to be ready for those windows — not to manufacture them.

## App Store position

A searchable advantage: a search for "Artemis" in the iOS App Store currently returns Artemis Mission Tracker before NASA's own app. That position is a moat as long as we defend it.

The levers that protect and extend it:
- Keyword set tuned for crew names, hardware names, mission identifiers (already in 2.3.1 metadata)
- Rating average kept at 4.6+ so the algorithm continues to favor the listing
- Steady release cadence (App Store rewards apps that ship, even minor updates)
- Screenshots and promotional text refreshed at each mission milestone

This position will be contested most aggressively in the months leading up to Artemis IV. Competing apps from NASA, news outlets, and opportunistic launches will appear. The defense is reputation built up before the landing window, not panic updates during it.

## Primary KPI — 500 DAU by August 31, 2026

Daily Active Users is the metric that proves the app is the place people go when news breaks. 500 DAU is the target by the end of August 2026 — roughly two and a half months from today.

Baseline (2026-06-13): 130 DAU (latest day), 5201 28-day active users.

The path from 130 to 500 comes from waking up the installed base, not from acquiring 370 new users. Acquisition is a secondary lever; activation and retention are the primary ones.

## The conversion funnel that actually matters

The push-notification opt-in rate is the single most important lever, because notifications are how the app turns a one-time installer into a returning user, and then into a paying subscriber.

Push subscription was added late in the app's life, so adoption is well below the installed base. The funnel we are optimizing:

```
Installs (52k)  →  Push opted-in (?)  →  DAU (130)  →  Artemis Plus subscribers (?)
```

The strategic objective is to widen each arrow.

## Monetization goal

**Long-term target: 10% of the installed base on Artemis Plus** (monthly or annual subscription).

At 52,000 installs that is 5,200 paying subscribers — well above where we are today and well above the August DAU target. This is not an August goal; it is the direction. The August work is to prove the funnel can move, by:

- Getting push opt-in rate up across the installed base
- Getting push open rate up (quality, not just opt-in)
- Surfacing Artemis Plus more cleanly in the app (onboarding + paywall design)
- Keeping churn as low as possible — every cancelled subscription is a unit of installed-base trust we did not earn

Churn is the silent killer of this business. A 10% subscription rate at 20% monthly churn is worse than a 5% rate at 4% churn. The dashboard must show churn alongside acquisition.

## Supporting goals (Aug 31, 2026)

These are the levers that move DAU and the subscription funnel. Each has a current value and a target.

| Metric                        | Current  | Aug 31 target | Why it matters                                       |
| ----------------------------- | -------- | ------------- | ---------------------------------------------------- |
| DAU (latest day)              | 130      | 500           | North Star                                           |
| 28-day active users           | 5201     | 12000         | Retention floor — proves people come back            |
| Push opt-in rate (iOS)        | TBD      | 35%           | Top of the conversion funnel                         |
| Push open rate (30d)          | TBD      | 25%+          | Engagement quality, not vanity                       |
| Artemis Plus subscribers      | TBD      | 250           | Step toward the 10%-of-installed-base direction      |
| Monthly churn (Plus)          | TBD      | <6%           | Compounds against everything else                    |
| Kit newsletter subscribers    | 32       | 250           | Owned audience that survives App Store algorithm     |
| New installs / 30d            | TBD      | 3000          | Top of funnel for new acquisition                    |
| App Store rating (avg)        | TBD      | 4.6+          | Algorithm ranking + conversion on listing            |
| 4★+ reviews (count)           | TBD      | 100           | Social proof                                         |
| Bluesky followers             | TBD      | 750           | Space-community discovery channel                    |
| Mastodon (spacey.space)       | TBD      | 300           | Federated reach to space enthusiasts                 |

Threads and Instagram are blocked on Meta developer verification and Business/Creator account linking. They are not on the August target sheet until those are unblocked.

## Editorial cadence

- Wednesday: deep-dive briefing (Artemis Plus subscribers, occasional free)
- Sunday: Week Ahead briefing (free, all subscribers)
- Breaking news: push + Bluesky/Mastodon when Artemis-related news warrants it

Tone: nøkternt, factual, closer to Spaceflight Now than to clickbait aggregators. No exclamation points, no emoji, no dramaturgical framing.

## What this strategy is NOT

- Not a pure acquisition plan. Acquisition matters and will spike around Artemis III, Moon Base I, and Artemis IV — but the day-to-day work is activation and retention of the 52k already installed.
- Not a launch-event-driven plan. The app must be useful between events (training, hardware progress, OIG reports), not only on launch days.
- Not a "feature parity with NASA" plan. The differentiator is curation and timing: one trustworthy push when something real happens, not a firehose.
- Not a wait-for-the-landing plan. By the time Artemis IV lands, App Store rank and reputation will already be locked in by the apps that shipped consistently in the months before.

## Review cadence

This document is reviewed on the first Sunday of every month against the dashboard. Targets adjust if reality deviates by more than 25% in either direction.
