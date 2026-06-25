---
name: linkedin-strategy
description: Manage LinkedIn content strategy, content calendar, and topic ideas. Helps user always know what to post and why, based on their goals.
user-invocable: true
metadata: {"openclaw":{"requires":{"env":["LINKEDIN_CLIENT_ID"]}}}
triggers:
  - "linkedin strategy"
  - "content strategy linkedin"
  - "set up my linkedin strategy"
  - "what should i post on linkedin"
  - "linkedin content calendar"
  - "plan my linkedin posts"
  - "add to content calendar"
  - "linkedin post ideas"
  - "suggest linkedin topics"
  - "what to post today"
  - "repurpose for linkedin"
  - "turn this into a linkedin post idea"
  - "linkedin posting schedule"
  - "content idea for linkedin"
  - "save idea for linkedin"
  - "content inbox linkedin"
---

# LinkedIn Strategy Skill

> ⚠️ MANDATORY RULES:
> 1. **Strategy file path:** `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/strategy.md` — read and write using the file `read`/`write` tools.
> 2. **Calendar file path:** `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/content-calendar.md` — same tools.
> 3. **Brand voice profile path:** `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/profile.md` — read-only from this skill; use `linkedin-brand-voice` to modify it.
> 4. **Never publish.** This skill plans and proposes. Actual drafting uses `linkedin-brand-voice`; posting uses `linkedin-publish`.
> 5. **DO NOT narrate steps.** Show results directly.

---

## Step 1 — Detect intent

Read which flow to run based on the user's message:

| User says | Flow |
|-----------|------|
| Set up strategy / first time | **Strategy Setup** |
| What should I post / suggest topics / post ideas | **Topic Suggestions** |
| Content calendar / plan posts / schedule | **Content Calendar** |
| Add to calendar / save idea / content inbox | **Add to Calendar** |
| Repurpose this / turn this into a post | **Repurpose** |

If ambiguous, default to **Topic Suggestions**.

---

## Strategy Setup (first time or explicit request)

### Step 1 — Check for existing strategy

Read `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/strategy.md`.

- **File found** → ask: "You already have a strategy. Do you want to review it, or start fresh?"
- **File not found (ENOENT)** → also read the brand voice profile at `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/profile.md` to pre-fill what's already known, then ask the strategy questions below.

### Step 2 — Strategy interview

Ask all questions in ONE message:

```
Let's set up your LinkedIn content strategy. I'll use your brand voice profile as a starting point.

1. **What's your primary business goal for LinkedIn this quarter?** (e.g. "generate 5 inbound leads/month", "get speaking invitations", "grow follower count to 5K", "build brand awareness")
2. **How often do you want to post?** (e.g. "3x/week", "daily", "once a week")
3. **Best days/times for you to post?** (e.g. "Mon/Wed/Fri mornings", "any day")
4. **Any topics you want to avoid?** (e.g. "politics", "competitor mentions", "personal life")
5. **Do you have any upcoming launches, events, or campaigns to plan around?** (list them or say "none")
6. **What are the 2–3 key messages you want every piece of content to reinforce?**
   These are the ideas you want your audience to associate with you — not slogans, but beliefs or positions.
   (e.g. "AI doesn't require a big team to implement", "Speed beats perfection in early-stage startups", "Enterprise software should feel like consumer software")
7. **Tell me about your target buyers / personas.**
   For each: job role, company size/type, industry, and the main pain point they face.
   (e.g. "CTO at 200+ person SaaS company — needs to reduce time-to-production for AI features")
```

**STOP. Wait for answers.**

### Step 3 — Write strategy file

After answers, write to `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/strategy.md`:

```markdown
# LinkedIn Content Strategy — <DISPLAY_NAME or "User">

**Owner:** <TELEGRAM_USER_ID>
**Last updated:** <YYYY-MM-DD>

## Business Goal

<from Q1>

## Posting Cadence

- **Frequency:** <from Q2>
- **Preferred schedule:** <from Q3>

## Content Pillars

*(Carried from brand voice profile — update via linkedin-brand-voice)*
1. <pillar 1>
2. <pillar 2>
3. <pillar 3>

## Key Messages

*(The beliefs and positions every post should reinforce — not slogans, but strategic angles)*
1. <from Q6 — message 1>
2. <from Q6 — message 2>
3. <from Q6 — message 3>

## Target Buyer Personas

*(Who you are writing for — each post should speak to at least one)*

- **Persona 1:** <role> at <company type/size>, <industry> — Pain: <main struggle>
- **Persona 2:** <role> at <company type/size>, <industry> — Pain: <main struggle>
- **Persona 3:** <role> at <company type/size>, <industry> — Pain: <main struggle>

## Topics to Avoid

<from Q4, or "(none set)">

## Upcoming Campaigns

<from Q5, or "(none planned)">

## Pillar Balance Target

Aim for roughly equal coverage across pillars over any 2-week window.
Example split for 3x/week: 2 posts per pillar per week.
Bias topic suggestions toward the persona with the most business-goal alignment.

## History

- **<YYYY-MM-DD>** | Strategy created
```

Reply: `✅ Content strategy saved. Want me to suggest topics for your calendar now?`

---

## Topic Suggestions

**Trigger:** user asks what to post, requests ideas, or asks about a specific pillar.

### Step 1 — Load context

Read both files in sequence:
1. `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/profile.md` — get Content Pillars
2. `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/strategy.md` — get business goal, upcoming campaigns, avoid list
3. `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/content-calendar.md` — check what's already planned (skip if file missing)

If profile not found → ask user to set up brand voice first via `linkedin-brand-voice`.

### Step 2 — Generate suggestions

Propose 3 post ideas — one per content pillar. For each:
- **Topic:** clear subject line
- **Angle:** the specific Gary Vee hook/framing (one of: contrarian take, personal story, framework/checklist, news reaction, challenge conventional thinking)
- **Key message reinforced:** which of the strategy’s Key Messages this post supports
- **Persona:** which buyer persona is the primary reader
- **Pillar:** which pillar it covers
- **Format:** text / text+image / text+link

Bias toward pillars with fewer recent posts in the calendar. If an upcoming campaign exists, include at least one post tied to it. Each suggestion should visibly reinforce one of the Key Messages.

Reply format:
```
Here are 3 post ideas for this week:

**1. <Topic>**
Angle: <hook type + 1-line premise>
Key message: <which message it reinforces>
Persona: <which persona it speaks to>
Pillar: <pillar name>
Format: <text / text+image>

**2. <Topic>**
...

**3. <Topic>**
...

Want me to add any of these to your calendar, draft one now, or suggest more?
```

---

## Content Calendar

**Trigger:** user asks to see the calendar, plan posts, or set up a posting schedule.

### View calendar

Read `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/content-calendar.md`.

- If file exists → display the **Upcoming** section (next 14 days)
- If file not found → offer to create it and suggest topics to populate it

### Create/initialize calendar

Write to `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/content-calendar.md`:

```markdown
# LinkedIn Content Calendar — <DISPLAY_NAME or "User">

**Owner:** <TELEGRAM_USER_ID>
**Last updated:** <YYYY-MM-DD>

## Upcoming

| Date | Pillar | Topic | Angle | Status |
|------|--------|-------|-------|--------|
| <date> | <pillar> | <topic> | <angle> | Idea |

## Published

| Date | Pillar | Topic | LinkedIn URL |
|------|--------|-------|-------------|

```

---

## Add to Calendar

**Trigger:** user says "add this to my calendar", "save this idea", "schedule a post", or forwards a link/note as a content idea.

### Step 1 — Parse the idea

Extract from user's message:
- **Topic** — what the post is about
- **Pillar** — which content pillar it fits (infer if not stated)
- **Date** — when to post (use "TBD" if not specified)
- **Source** — if user forwarded a URL/article, note it as inspiration

### Step 2 — Append to calendar

Read `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/content-calendar.md`.
If missing → create it first (see **Create/initialize calendar**).

Append a new row to the **Upcoming** table:

```
| <date or TBD> | <pillar> | <topic> | <angle or TBD> | Idea |
```

Write the updated file back.

Reply: `✅ Added to calendar: "<topic>" — <pillar> — <date or TBD>`

Then offer: "Want me to draft this now, or keep it for later?"

---

## Repurpose

**Trigger:** user sends a URL, article, brain page name, voice note transcript, or any raw content and asks to turn it into a LinkedIn post idea.

### Step 1 — Extract the core insight

If it's a URL → read the page content (web fetch).  
If it's a brain page name → read the file at the path given.  
If it's pasted text → use it directly.

Identify the single strongest insight, stat, or story from the content.

### Step 2 — Load brand voice

Read `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/profile.md`.  
Identify which **Content Pillar** the insight fits.

### Step 3 — Propose a post angle

Reply with ONE repurposed post angle — do not draft the full post here (that's `linkedin-brand-voice`):

```
Here's how I'd repurpose this for LinkedIn:

**Topic:** <clear subject>
**Pillar:** <pillar>
**Angle:** <Gary Vee hook type + 1-line premise>
**Key insight to lead with:** "<the strongest line or stat from the source>"

Want me to draft the full post now, or add this idea to your calendar?
```

If user says "draft it" → hand off to `linkedin-brand-voice` with the angle and key insight as the brief.

---

## Update Strategy

**Trigger:** user says "update my strategy", "change my posting frequency", "add a campaign", etc.

1. Read `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/strategy.md`
2. Apply the specific change to the relevant section only
3. Add a history entry: `- **<YYYY-MM-DD>** | <what changed>`
4. Write back to the same path
5. Confirm: `✅ Strategy updated: <what changed>`

---

## Error Reference

| Situation | Action |
|-----------|--------|
| Brand voice profile missing | Ask user to run `linkedin-brand-voice` setup first |
| Strategy file missing | Run Strategy Setup |
| Calendar file missing | Create it on first Add to Calendar or View Calendar |
| User skips a strategy question | Use `(not set)` as placeholder; offer to fill later |
