---
name: linkedin-profile-sync
description: Sync and improve the user's live LinkedIn profile. Reads headline, about, follower count and surfaces actionable improvement suggestions.
user-invocable: true
metadata: {"openclaw":{"requires":{"env":["LINKEDIN_CLIENT_ID","LINKEDIN_CLIENT_SECRET","LINKEDIN_REDIRECT_URI"]}}}
triggers:
  - "sync my linkedin profile"
  - "check my linkedin profile"
  - "improve my linkedin profile"
  - "linkedin profile suggestions"
  - "linkedin headline"
  - "update linkedin about"
  - "how many followers do i have on linkedin"
  - "linkedin profile review"
  - "profile completeness linkedin"
  - "my linkedin stats"
---

# LinkedIn Profile Sync Skill

> ⚠️ MANDATORY RULES:
> 1. **NEVER write scripts to /tmp.** Use ONLY `{baseDir}/li-profile.sh`.
> 2. **Profile file path:** `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/profile.md` — file `read`/`write` tools only.
> 3. **DO NOT narrate steps.** Show results directly.

---

## Step 1 — Check token

```bash
TOKEN_STORE=/data/openclaw/linkedin-tokens.json
[ -f "$TOKEN_STORE" ] || echo "{}" > "$TOKEN_STORE"
ACCESS_TOKEN=$(jq -r --arg u "$TELEGRAM_USER_ID" '.[$u].access_token // empty' "$TOKEN_STORE")
EXPIRES_AT=$(jq -r --arg u "$TELEGRAM_USER_ID" '.[$u].expires_at // 0' "$TOKEN_STORE")
NOW=$(date +%s)
if [ -z "$ACCESS_TOKEN" ]; then echo "STATUS: NO_TOKEN"
elif [ "$EXPIRES_AT" -lt "$((NOW+3600))" ]; then echo "STATUS: EXPIRED"
else echo "STATUS: OK"
fi
```

- `NO_TOKEN` / `EXPIRED` → tell user to link/refresh via `linkedin-publish` first
- `OK` → continue

---

## Step 2 — Fetch live profile

```bash
{baseDir}/li-profile.sh "$TELEGRAM_USER_ID"
```

Parse output fields: `DISPLAY_NAME`, `HEADLINE`, `ABOUT`, `PROFILE_URL`, `FOLLOWERS`, `PROFILE_PIC`.

On `NO_TOKEN` or `TOKEN_EXPIRED` → redirect to `linkedin-publish` for auth.  
On `ERROR` → report the code and body verbatim.

---

## Step 3 — Load brand voice profile

Read `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/profile.md` with the file `read` tool.  
Use the **Identity & Goals**, **Content Pillars**, and **Voice & Tone** sections as the reference for suggestions.  
If profile missing → note it; suggestions will be generic.

---

## Step 4 — Surface improvement suggestions

Compare the live LinkedIn data against the brand voice profile and produce actionable suggestions.

### Headline check

| Situation | Suggestion |
|-----------|-----------|
| Empty or "(not set)" | Write one: format `<Role> at <Company> — <Value prop in 5 words>` |
| Doesn't mention role or company | Add them |
| Generic ("Looking for opportunities", "CEO") | Rewrite to include specific value proposition |
| Not aligned with Content Pillars | Suggest rewording to reflect pillars |

Target: under 220 characters, keyword-rich, specific.

### About section check

| Situation | Suggestion |
|-----------|-----------|
| Empty or "(not set)" | Offer to draft one from brand voice profile |
| Under 200 characters | Too short — LinkedIn rewards 1,000–1,500 char About sections |
| No CTA at the end | Add a soft CTA (invite DMs, mention website, ask a question) |
| Corporate/passive tone | Rewrite hook sentence in Gary Vee style if profile specifies it |

### Follower count

Just report it. Add context:
- Under 500: "Still building — consistency in posting is the fastest growth lever."
- 500–5,000: "Good foundation. Engagement rate matters more than follower count at this stage."
- Over 5,000: "Strong audience. Focus on nurturing top engagers."

### Reply format

```
**LinkedIn Profile Sync — <DISPLAY_NAME>**
🔗 <PROFILE_URL>
👥 Followers: <FOLLOWERS>

**Headline:** "<HEADLINE>"
<suggestion or "Looks good ✅">

**About section:** <length> characters
<suggestion or "Looks good ✅">

**Brand voice alignment:**
<note on whether headline/about match the voice profile tone and pillars, or "No voice profile found — set one up with linkedin-brand-voice">

---
Want me to draft an improved headline or about section?
```

---

## Step 5 — Draft improvements (on request)

If user says "draft a better headline" or "write my about section":

### Headline draft

Use brand voice profile fields:
- Role = derived from Identity & Goals
- Value prop = derived from Content Pillars and Company context
- Tone = Voice & Tone Style field
- Max 220 characters

Format: `<Role> helping <target audience> <achieve outcome> | <1-2 content pillar keywords>`

### About section draft

Structure (1,000–1,500 characters):
1. **Hook line** — bold, pattern interrupt (Gary Vee style if profile specifies)
2. **Who you help** — specific target audience and their pain (from Buyer Personas)
3. **What you do** — company/role + key differentiators (from Company Context)
4. **Proof** — 1-2 concrete results or credentials
5. **Content topics** — "I post about: X, Y, Z" (Content Pillars)
6. **CTA** — soft, question-based

Output both headline and about drafts directly in the reply — no files.

---

## Log sync to brain

After fetching, append a sync record to `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/profile.md` under History:

```
- **<YYYY-MM-DD>** | Profile sync: headline="<HEADLINE>", followers=<FOLLOWERS>
```

Use the file `read` then `write` tool — patch only the History section, do not rewrite the whole file.

---

## Error Reference

| Output | Action |
|--------|--------|
| `NO_TOKEN` | Ask user to link LinkedIn via `linkedin-publish` |
| `TOKEN_EXPIRED` | Ask user to refresh via `linkedin-publish` |
| `ERROR 403` | Missing scope — `r_member_social` may be needed for follower data |
| `ERROR 401` | Token invalid — re-auth |
| `FOLLOWERS: (scope r_member_social not granted)` | Report without followers; all other fields still usable |
