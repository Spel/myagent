---
name: linkedin-trends
description: Weekly trend research. Finds trending topics in user's industry/pillars via web search and adds content proposals to their calendar.
user-invocable: true
metadata: {"openclaw":{"requires":{"env":["LINKEDIN_CLIENT_ID"]}}}
triggers:
  - "find trending topics"
  - "what's trending in my industry"
  - "linkedin trend research"
  - "find content ideas from trends"
  - "research trends for linkedin"
  - "what's hot right now"
  - "industry news for my linkedin"
---

# LinkedIn Trends Skill

> ⚠️ MANDATORY RULES:
> 1. **Write proposals, not posts.** This skill researches and proposes. Drafting uses `linkedin-brand-voice`.
> 2. **Stay grounded in user's pillars.** Only surface trends relevant to their content pillars and industry. No random noise.
> 3. **Every proposal must include an angle.** Not "AI is growing" — but "What this means for [persona]" or "The mistake most people will make."
> 4. **Cite sources.** Every trend proposal includes a source URL.
> 5. **DO NOT narrate steps.** Show results directly.

---

## When this runs

- **Weekly cron** (Sunday 6 PM or Monday 7 AM) — researches trends for all connected users
- **User manually asks** — "what's trending in my industry?", "find content ideas from trends"

---

## Flow: Trend Research for One User

### Step 1 — Load user pillars and industry context

Read the brand voice profile:

```bash
UID="${TELEGRAM_USER_ID}"
PROFILE="/data/workspace/social/linkedin/$UID/profile.md"

if [ ! -f "$PROFILE" ]; then
  echo "NO_PROFILE"
  exit 0
fi

# Extract pillars and company context
grep -A 20 "Content Pillars\|Company.*Context\|Industry\|Key messages" "$PROFILE" | head -30
```

If `NO_PROFILE` → skip silently (cron) or ask user to set up brand voice first (manual).

### Step 2 — Research trends per pillar

For each content pillar, run a focused web search. Use the `web_fetch` tool or `search` to find:
- News published in the last 7 days
- Trending discussions relevant to the pillar
- Industry reports, viral LinkedIn posts, notable opinion pieces

**Search query pattern for each pillar:**
```
"<pillar topic> trends 2026" OR "<pillar topic> latest news" site:linkedin.com OR site:techcrunch.com OR site:hbr.org OR site:venturebeat.com
```

If the user has company/product context (e.g. UBOS, AI agents), also search:
```
"<competitor or adjacent tech> news this week"
```

**Target: 2-3 strong trend signals per pillar. Discard anything older than 14 days.**

### Step 3 — Convert each trend to a content proposal

For each trend found, create a proposal using this format:

```markdown
### [Trend title — one punchy line]
**Source:** <URL>
**Published:** <date>
**Pillar:** <matching pillar>
**Angle:** <one of: "What this means for you" / "The mistake most people will make" / "The second-order effect nobody mentions" / "Why this is underestimated" / "Contrarian take">
**Post hook draft:** <one-line hook in user's Gary Vee style>
**Persona:** <which buyer persona this speaks to>
**Status:** Proposed 🔎
```

### Step 4 — Write proposals to content calendar

Append proposals to `/data/workspace/social/linkedin/<UID>/content-calendar.md`.

Add a section header if it doesn't exist:
```markdown
## Trend Proposals — <YYYY-MM-DD>
```

Then append each proposal block.

### Step 5 — Notify user

Send a Telegram message:

```
🔎 Found <N> trending topics for your LinkedIn this week, <NAME>.

Here's what's hot in your space:

• <Trend 1 title> → <Angle>
• <Trend 2 title> → <Angle>
• <Trend 3 title> → <Angle>

All added to your content calendar. Want to write any of these now?
```

With buttons:
```json
{
  "blocks": [
    { "type": "buttons", "buttons": [
      { "label": "✍️ Write the top one now", "action": { "type": "callback", "value": "trends_write_top" }, "style": "primary" },
      { "label": "📅 See full calendar", "action": { "type": "callback", "value": "trends_see_calendar" } },
      { "label": "Later", "action": { "type": "callback", "value": "trends_later" }, "style": "secondary" }
    ]}
  ]
}
```

### Step 6 — Handle button callbacks

- `trends_write_top` → take the first proposal, pass the topic + angle + hook draft to `linkedin-brand-voice` draft flow immediately
- `trends_see_calendar` → read and display the content calendar (upcoming planned + new proposals)
- `trends_later` → "Got it — ideas are saved in your calendar whenever you're ready."

---

## Flow: All-Users Weekly Cron Run

When cron fires without a specific user:

```bash
TOKEN_STORE=/data/openclaw/linkedin-tokens.json
[ -f "$TOKEN_STORE" ] || exit 0
jq -r 'to_entries[] | select(.value.access_token != null and .value.access_token != "") | .key' "$TOKEN_STORE"
```

For each user returned:
1. Run the **Trend Research for One User** flow above
2. Send each user their personalized trend proposals via Telegram DM

---

## Research quality rules

- **Recency first.** Trends older than 2 weeks are not trends — they're history.
- **Specificity beats breadth.** "AI agents in healthcare" beats "AI is growing". Match to the user's actual pillar.
- **Angle is mandatory.** A raw news link is not a content proposal. The angle is what makes it postable.
- **Hook draft included.** Give the user a starting line so the barrier to writing is near zero.
- **3-5 proposals max per run.** Quality over quantity. 10 proposals nobody uses is noise. 3 great ones get written.
