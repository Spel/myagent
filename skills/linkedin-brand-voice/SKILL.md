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

Ask all 6 questions in ONE message. Do not drip them one at a time.

```
To help you post in your own voice, I need to understand you a bit first.
Answer however you like — a few words per question is fine.

1. **Who is your target audience?** (e.g. "B2B SaaS founders", "junior developers", "HR professionals")
2. **What's your main LinkedIn goal?** (build thought leadership / get clients / grow my network / share knowledge / other)
3. **What 3 topics do you post about most?**
4. **How would you describe your communication style?** (e.g. "direct and practical", "storytelling", "technical deep-dives", "motivational", "casual and humorous")
5. **What do you dislike seeing in LinkedIn posts?** (e.g. "vague humble-brags", "excessive emojis", "too long", "salesy CTAs")
6. **Any hashtags you always include?** (list them, or say "none")
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
- **Primary goal:** <from Q2>

## Content Pillars

1. <topic 1 from Q3>
2. <topic 2 from Q3>
3. <topic 3 from Q3>

## Voice & Tone

- **Style:** <from Q4>
- **Avoid:** <from Q5>

## Hashtag Strategy

- Always use: <from Q6, or "(none set)">
- Topic-specific: *(add as you go)*

## Post Style Guide

- Length: *(calibrate from first drafts)*
- Format: *(calibrate from feedback)*
- CTA style: *(calibrate from feedback)*

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

Write a post that strictly follows the loaded profile:
- Match the **style** and **tone** fields
- Include the **always-use hashtags** at the end
- Stay within 1,300 characters unless the user asks for long-form (max 3,000)
- Avoid everything listed under **Avoid**
- Cover one of the **Content Pillars** if the brief fits

Format the draft in a code block so the user can copy it cleanly. **Output the draft directly in the reply — do NOT write it to any file first.**

````
Here's your draft:

```
<DRAFTED POST TEXT>
```

**Characters:** <count>/1,400
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
| Hashtags | Always-use hashtags are present |
| Length | Within user's preferred range |

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

## Error Reference

| Situation | Action |
|-----------|--------|
| Profile page not found | Run Onboarding Interview |
| User skips a question | Use `(not set)` as placeholder; offer to fill later |
| Draft rejected by user | Ask which part to change; redraft that section only |
| Style gate overridden | Log override in profile history entry |
