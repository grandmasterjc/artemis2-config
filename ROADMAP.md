# Artemis Tracker — Roadmap

This file is read by the dashboard renderer. Edit items below to update the dashboard roadmap section. Keep the four section headers exactly as they appear.

Status legend:
- in_progress — actively being worked on this week
- upcoming — scheduled, not started
- blocked — waiting on external dependency
- completed — shipped, kept here for the last 30 days

Format per item:
- `- title :: short note`

## in_progress

- App Store 2.3.1 (Crew + minor fixes) :: metadata ready, awaiting submission
- Dashboard 2.0 rebuild :: this rebuild, KPIs + roadmap + social

## upcoming

- App Store Connect API integration :: downloads, ratings, reviews into dashboard
- Bluesky/Mastodon social metrics :: followers, posts, engagement
- Android paywall parity :: pricing tiers + Play Billing
- Play Console listing refresh :: screenshots + description
- Web landing page :: marketing site for newsletter signup

## blocked

- Threads publishing :: Meta developer verification not completed
- Instagram publishing :: needs Business/Creator account linked to Facebook page

## completed

- GitHub Actions cron migration :: all daily jobs moved off ephemeral sandbox
- Artemis III crew announcement bundle :: article + push + Kit + social on June 9
- Bresnik EVA portrait update :: new image deployed via remote crew JSON
- Remote banner system :: banners/active.json drives in-app top banner
- Artemis III LEO docking spacer article :: published May 20
- Moon Base construction-begins article :: published May 27
- Artemis II heat shield verdict article :: published May 13
- Crew schema fix :: Artemis3CrewMember fields align with iOS app
- Android review prompt parity :: sentiment sheet + in-app review on Android
- Dashboard refresh credentials moved to GitHub Secrets :: durable across sandbox resets
