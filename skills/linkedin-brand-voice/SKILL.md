---
name: linkedin-brand-voice
description: Manage LinkedIn brand voice profiles and draft posts in the user's voice. Onboards new users, drafts posts from briefs, checks style before publish.
user-invocable: true
metadata: {"openclaw":{"requires":{"env":["LINKEDIN_CLIENT_ID"]}}}
triggers:
  - "set up my linkedin voice"
  - "linkedin brand voice"
  - "update my linkedin profile voice"
  - "draft linkedin post"
  - "write linkedin post"
  - "write a post for linkedin"
  - "create linkedin post"
  - "generate linkedin post"
  - "linkedin post from bullets"
  - "turn this into a linkedin post"
  - "make this a linkedin post"
  - "post idea for linkedin"
  - "linkedin hashtags"
  - "suggest hashtags for linkedin"
  - "check my linkedin voice"
  - "style check linkedin post"
---

# LinkedIn Brand Voice Skill

> ⚠️ MANDATORY RULES:
> 1. **Always check for an existing profile before onboarding.** Never run the interview twice.
> 2. **Profile file path:** `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/profile.md` — read and write using the **file `read`/`write` tools**, NOT `get_page`/`put_page`.
> 3. **Never publish.** This skill drafts and checks. Actual posting is done by `linkedin-publish`.
> 4. **DO NOT narrate steps.** Show results directly.
> 5. **NEVER write a post draft to `/tmp` or any file.** Output drafts directly in the reply message.

---

## Step 1 — Load profile

Read the file at `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/profile.md` using the file `read` tool.

- **File found** → profile loaded → go to the appropriate flow below
- **File not found (ENOENT) or empty** → go to **Onboarding Interview**

---

## Onboarding Interview (first-time only)

Ask all 8 questions in ONE message. Do not drip them one at a time.

```
To help you post in your own voice, I need to understand you a bit first.
Answer however you like — a few words per question is fine.

1. **Who is your target audience?** (e.g. "B2B SaaS founders", "junior developers", "HR professionals")
2. **Who are your ideal buyers / personas?** For each type: role, company size, industry, and their main pain point.
   (e.g. "CTO at 100+ person tech company — needs to ship AI faster without vendor lock-in")
3. **What's your main LinkedIn goal?** (build thought leadership / get clients / grow my network / share knowledge / other)
4. **What 3 topics do you post about most?**
5. **How would you describe your communication style?** (e.g. "direct and practical", "storytelling", "technical deep-dives", "motivational", "casual and humorous")
6. **What do you dislike seeing in LinkedIn posts?** (e.g. "vague humble-brags", "excessive emojis", "too long", "salesy CTAs")
7. **Any hashtags you always include?** (list them, or say "none")
8. **Are you promoting a specific company or product, or is this a personal brand?**
   - Personal brand only: say "personal brand"
   - Company/product: give the name, a one-line description, and 2-3 key differentiators.
   (e.g. "UBOS - AI Agent Orchestration Platform, open-source, no vendor lock-in, 100+ LLMs")
```

**STOP. Wait for answers.**

Once the user replies → go to **Write Profile Page**.

---

## Write Profile Page

After onboarding answers, write the profile using the file `write` tool:
- **path:** `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/profile.md`
- **content:** the formatted profile below

```markdown
# LinkedIn Brand Voice — <DISPLAY_NAME or "User">

**Owner:** <TELEGRAM_USER_ID>
**Last updated:** <YYYY-MM-DD>

## Identity & Goals

- **Target audience:** <from Q1>
- **Primary goal:** <from Q3>

## Buyer Personas

*(Who specifically should feel spoken to by every post)*

- **Persona 1:** <role> at <company type/size> — Pain: <main struggle>
- **Persona 2:** <role> at <company type/size> — Pain: <main struggle>
*(add more as needed)*

## Content Pillars

1. <topic 1 from Q4>
2. <topic 2 from Q4>
3. <topic 3 from Q4>

## Voice & Tone

- **Style:** <from Q5>
- **Avoid:** <from Q6>

## Company / Product Context

*(Skip this section entirely if personal brand only)*
- **Company:** <from Q8 — name, or omit section>
- **What it does:** <from Q8 — one-line description>
- **Key differentiators:** <from Q8>

## Hashtag Strategy

- Always use: <from Q7, or "(none set)">
- Topic-specific: *(add as you go)*

## Post Production Rules

*(These rules apply to EVERY post drafted from this profile — non-negotiable)*

### Length & Structure
- Target: 900–1,300 characters (hard min 800, max 1,400)
- Max 14 lines total
- 1–2 short sentences per line
- Structure: 1–3 hook lines → 6–10 body lines → 1–2 CTA lines

### Hook rules
- Must create a pattern interrupt — choose ONE: contrarian statement, direct challenge, or consequence reveal
- Use Unicode bold sans (e.g. 𝗵𝗲𝗿𝗲’𝘀 𝙷𝙩𝙺) for the hook line ONLY
- No Markdown, no asterisks (*), no underscores (_)

### Body rules
- Include ONE comment trigger: a direct question, A vs B choice, or unfinished thought
- Introduce contrast: old belief vs reality, OR comfort now vs pain later
- Include ONE save-worthy insight: a rule, checklist, or named pattern
- Use "you" and "your" frequently
- ALL CAPS for 1–2 key words maximum per post
- Speak to the buyer persona pain points — make them feel understood

### CTA rules
- Must be a question, not a command
- No direct selling, no "book a call", no "reach out to us"
- Prefer: "What’s your experience with X?" / "Are you doing this?" / "What would you add?"

### Hashtag rules
- 3–6 hashtags ONLY, placed at the END of the post
- Never inside sentences
- Prefer industry/role/topic-specific; avoid generic (#success, #motivation)

### Formatting rules
- NO Markdown of any kind (no *, _, #heading)
- Unicode Mathematical Alphanumeric Symbols for emphasis ONLY on hooks or single key phrases, never full paragraphs
  - Bold sans: 𝗴𝗲𝗹𝗹𝗼 𝗹𝗶𝗸𝗲 𝗴𝗲𝗹𝗹
  - Italic sans: 𝘨𝘦𝘭𝘭𝘰 𝘭𝘪𝘬𝘦 𝘨𝘦𝘭𝘭
- Emojis: 0–3 per post maximum

### News framing (when post is based on an article or announcement)
- Reframe using ONE angle: "What this means for you" / "Why this is underestimated" / "The mistake most people will make" / "The second-order effect nobody mentions"
- Never neutral reporting — always add perspective, judgment, or implication
- If engagement potential feels weak after drafting, rewrite the hook and CTA once before finalizing

## Post Style Guide

- Length: 900–1,300 characters
- Format: *(calibrate from feedback)*
- CTA style: question-based

## History

- **<YYYY-MM-DD>** | Profile created via onboarding
```

After writing: reply `✅ Brand voice profile saved. Now I can draft posts in your voice — just send me your idea or bullet points.`

---

## Draft Post (main flow)

**Trigger:** user sends a brief, bullets, idea, article link, or rough text and asks to turn it into a LinkedIn post.

### Step 1 — Load profile (if not already loaded)

Read `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/profile.md` with the file `read` tool.  
If missing (ENOENT) → run **Onboarding Interview** first, then come back here.

### Step 2 — Draft

Apply the **Post Production Rules** from the profile in strict order:

**Before writing, identify:**
- Which **Content Pillar** the brief fits
- Which **Buyer Persona** to speak to (pick the one most relevant to the topic)
- Whether this is a **news post** (article/announcement) or an **original insight post**
- Whether the profile has a **Company / Product Context** section — if yes and the brief relates to it, weave it naturally (never as a hard sell); if personal brand only, keep posts in first-person voice with no product references unless user explicitly asks

**Hook (lines 1–3):**
- Pattern interrupt — ONE of: contrarian statement, direct challenge, consequence reveal
- Unicode bold sans for hook line only (e.g. 𝗵𝗲𝗿𝗲’𝘀 𝗵𝗼𝘄 𝗶𝘁 𝗴𝗼𝗲𝘀)
- No Markdown, no asterisks, no underscores

**Body (lines 4–12):**
- ONE comment trigger (direct question, A vs B, or unfinished thought)
- Contrast: old belief vs reality, OR short-term comfort vs long-term cost
- ONE save-worthy insight (a rule, checklist, or named pattern the reader will screenshot)
- "you" and "your" throughout
- ALL CAPS on 1–2 key words max
- Speak directly to the buyer persona’s pain

**CTA (lines 13–14):**
- A question, never a command
- No selling language unless user explicitly asks for it

**If news post:** pick ONE framing angle from profile’s News Framing rules. Never summarize neutrally.

**After drafting:** if engagement potential feels weak — hook is generic or CTA is passive — rewrite hook and CTA once before showing the result.

Output the draft directly in the reply — no files, no variables:

````
Here’s your draft:

```
<DRAFTED POST TEXT>
```

**Characters:** <count>/1,400
**Pillar:** <which pillar>
**Persona:** <which buyer persona>
**Hashtags used:** <list>

Want me to adjust the tone, length, or anything else — or publish this now?
````

If the user says "publish" or "post it" → hand off to `linkedin-publish` skill by replying:  
`Sending to LinkedIn now…` and then triggering the publish flow with the drafted text.

---

## Suggest Hashtags

**Trigger:** user asks for hashtag suggestions for a given topic or post.

1. Read `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/profile.md` with the file `read` tool
2. Read **Hashtag Strategy** section
3. Look at **Content Pillars** — identify which pillar the topic fits
4. Suggest:
   - Always-use hashtags from profile
   - 3–5 topic-specific hashtags based on the content and pillar
   - Format: `#Tag` — one per line with brief note on reach/intent

Reply format:
```
Hashtags for this post:

**Always include:**
#Tag1 #Tag2

**Topic-specific:**
#Tag3 — (reason)
#Tag4 — (reason)
#Tag5 — (reason)
```

Then offer to update the profile's topic-specific list if user likes them.

---

## Style Gate (called before publishing)

**Trigger:** invoked by `linkedin-publish` skill when a post draft is ready, or when user explicitly asks "check this post".

1. Read `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/profile.md` with the file `read` tool
2. If file not found (ENOENT) → skip gate, let publish proceed (no voice profile means no gate)
3. Check the draft against:

| Check | Pass condition |
|-------|----------------|
| Tone match | Matches **Style** field in profile |
| Avoid list | None of the **Avoid** patterns present |
| Content pillar | Fits at least one pillar (or is explicitly off-pillar by user choice) |
| Buyer persona | Speaks to at least one defined persona |
| Hook pattern | Creates a pattern interrupt (contrarian / challenge / consequence) |
| Comment trigger | ONE question, A vs B, or unfinished thought present |
| Hashtags | 3–6 at end, none inside sentences |
| Formatting | No Markdown (*/_), Unicode emphasis on hook only |
| Length | 800–1,400 characters |

4. If all pass → reply `✅ Style check passed.` and let publish proceed
5. If any fail → reply:
   ```
   ⚠️ Style check flagged:
   - <issue 1>
   - <issue 2>

   Adjust and re-send, or reply *publish anyway* to override.
   ```
   **STOP.** Wait for user to edit or override.

---

## Update Profile

**Trigger:** user says "update my voice", "change my hashtags", "I want shorter posts", etc.

1. Read `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/profile.md` with the file `read` tool
2. Apply the specific change (patch only the relevant section — do not rewrite the whole page)
3. Add a history entry: `- **<YYYY-MM-DD>** | <what changed>`
4. Write back with the file `write` tool to the same path
5. Confirm: `✅ Profile updated: <what changed>`

---

## Profile Completeness Check

**Trigger:** user asks "how complete is my profile?", "what's missing from my voice profile?", or after onboarding/update.  
Also run automatically after writing a new profile — append the score to the confirmation reply.

### Scoring (10 fields, 10 points each)

Read `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/profile.md` and check each field:

| Field | Passes if |
|-------|-----------|
| Target audience | Present and not `(not set)` |
| Primary goal | Present and not `(not set)` |
| Buyer Personas | At least 1 persona defined |
| Content Pillars | At least 2 pillars listed |
| Voice & Tone — Style | Present and not `(not set)` |
| Voice & Tone — Avoid | Present and not `(not set)` |
| Hashtag Strategy | At least one hashtag or explicit "none" |
| Company/Product Context | Present OR explicitly marked "personal brand" |
| Post Production Rules | Section exists |
| History | At least 1 entry |

### Reply format

```
**Profile completeness: <score>/100**

Complete:
- Target audience ✅
- Content pillars ✅
...

Missing or incomplete:
- Buyer Personas ❌ — add at least one persona with role, company size, and pain point
- Company/Product Context ❌ — tell me if this is personal brand or add company details
...

<score >= 80: "Your profile is solid. Ready to draft great posts.">
<score 50-79: "A few gaps — fill them for better-targeted posts.">
<score < 50: "Profile is thin — let's fill in the gaps now. Which would you like to tackle first?">
```

---

## Error Reference

| Situation | Action |
|-----------|--------|
| Profile page not found | Run Onboarding Interview |
| User skips a question | Use `(not set)` as placeholder; offer to fill later |
| Draft rejected by user | Ask which part to change; redraft that section only |
| Style gate overridden | Log override in profile history entry |
