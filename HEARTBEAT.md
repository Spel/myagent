# Heartbeat Tasks

Run 2-3 of these per session (rotate, don't run all every time).

## LinkedIn Coach Check (run every session for owner)

Check if the owner (TELEGRAM_USER_ID=264468965) is on track with their LinkedIn posting cadence.
Read `skills/linkedin-coach/SKILL.md` and run the Daily Coach Check flow for user 264468965.
If they're behind: proactively send them a nudge in this chat (no separate DM needed — we're already talking).
If they're on track: brief acknowledgement only, don't interrupt.

## Trend Research Freshness (run once per week max)

Check `/data/workspace/social/linkedin/264468965/content-calendar.md` — look at the date of the last "Trend Proposals" section.
If it's older than 7 days (or missing): note it here so next heartbeat can trigger `linkedin-trends` for a refresh.
Do NOT run the full trend research during heartbeat — that's a background cron task. Just flag it.

## State file

Track last checks in `/data/workspace/memory/heartbeat-state.json`:
```json
{
  "lastChecks": {
    "linkedin_coach": 0,
    "linkedin_trends_flagged": 0
  }
}
```
