---
name: linkedin-onboarding
description: Welcome new LinkedIn users, detect setup state, and guide them through OAuth, brand voice, and strategy in the right order.
user-invocable: true
metadata: {"openclaw":{"requires":{"env":["LINKEDIN_CLIENT_ID","LINKEDIN_CLIENT_SECRET","LINKEDIN_REDIRECT_URI"]}}}
triggers:
  - "start"
  - "hello"
  - "hi"
  - "help"
  - "get started"
  - "setup linkedin"
  - "set up linkedin"
  - "onboard linkedin"
  - "what can you do"
  - "linkedin setup"
  - "connect my linkedin"
  - "i want to use linkedin"
  - "linkedin assistant"
  - "linkedin agent"
---

# LinkedIn Onboarding Skill

> ⚠️ MANDATORY RULES:
> 1. **Always run setup state check first.** Every flow in this skill starts by detecting what's already done.
> 2. **Never ask for information you can already detect.** Check files and token store before asking anything.
> 3. **Guide sequentially.** Don't overwhelm. One step at a time.
> 4. **DO NOT narrate steps.** Show results directly.

---

## Setup State Check

Run this at the start of every flow in this skill. It determines which step to show next.

```bash
TOKEN_STORE=/data/openclaw/linkedin-tokens.json
TELEGRAM_USER_ID="$TELEGRAM_USER_ID"

# Check 1: OAuth token
[ -f "$TOKEN_STORE" ] || echo "{}" > "$TOKEN_STORE"
ACCESS_TOKEN=$(jq -r --arg u "$TELEGRAM_USER_ID" '.[$u].access_token // empty' "$TOKEN_STORE")
EXPIRES_AT=$(jq -r --arg u "$TELEGRAM_USER_ID" '.[$u].expires_at // 0' "$TOKEN_STORE")
DISPLAY_NAME=$(jq -r --arg u "$TELEGRAM_USER_ID" '.[$u].display_name // empty' "$TOKEN_STORE")
NOW=$(date +%s)

[ -n "$ACCESS_TOKEN" ] && [ "$EXPIRES_AT" -gt "$((NOW+3600))" ] && OAUTH=true || OAUTH=false

# Check 2: Brand voice profile
[ -f "/data/workspace/social/linkedin/$TELEGRAM_USER_ID/profile.md" ] && PROFILE=true || PROFILE=false

# Check 3: Content strategy
[ -f "/data/workspace/social/linkedin/$TELEGRAM_USER_ID/strategy.md" ] && STRATEGY=true || STRATEGY=false

# Check 4: Posts published
POST_COUNT=$(find /data/workspace/social/linkedin/$TELEGRAM_USER_ID/posts/ -name "*.md" 2>/dev/null | wc -l | tr -d ' ')

echo "OAUTH=$OAUTH DISPLAY_NAME=$DISPLAY_NAME PROFILE=$PROFILE STRATEGY=$STRATEGY POSTS=$POST_COUNT"
```

Use the output to determine the correct response flow below.

---

## Flow: New user (OAUTH=false, PROFILE=false)

Generate the OAuth URL immediately (same bash as in `linkedin-publish` OAuth Flow), then reply:

```bash
ENC_REDIRECT=$(printf '%s' "$LINKEDIN_REDIRECT_URI" | jq -sRr @uri)
echo "https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=${LINKEDIN_CLIENT_ID}&redirect_uri=${ENC_REDIRECT}&scope=openid%20profile%20w_member_social&state=${TELEGRAM_USER_ID}"
```

Reply:

```
👋 Welcome! I'm your LinkedIn AI Assistant.

I'll help you draft and publish posts, build your brand voice, plan content, and grow your presence.

First I need to connect your LinkedIn account — takes about 60 seconds:

👉 <AUTH_URL>

Approve access, then paste the JSON from the redirect page here.
```

**STOP.** Wait for user to paste `{"code":"...","state":"..."}`.
When they paste it → run Exchange Code from `linkedin-publish`, then immediately continue to **Flow: OAuth done, no profile**.

---

## Flow: OAuth done, no profile (OAUTH=true, PROFILE=false)

**Before showing the next-step prompt, register proactive cron jobs for this user** (do this silently, once per user):

```bash
# Check if crons already registered for this user
CRON_FLAG="/data/workspace/social/linkedin/$TELEGRAM_USER_ID/.crons-registered"
if [ ! -f "$CRON_FLAG" ]; then
  echo "REGISTER_CRONS=true"
else
  echo "REGISTER_CRONS=false"
fi
```

If `REGISTER_CRONS=true`:
- Use the `cron-scheduler` skill to register two jobs for this user:
  1. **Daily coach** — `0 9 * * *` → prompt: `TELEGRAM_USER_ID=<uid>. Read skills/linkedin-coach/SKILL.md and run the Daily Coach Check flow.`
  2. **Weekly trends** — `0 18 * * 0` (Sunday 6 PM) → prompt: `TELEGRAM_USER_ID=<uid>. Read skills/linkedin-trends/SKILL.md and run the Trend Research flow.`
- Then: `touch "$CRON_FLAG"` to mark as done

Then reply with:

```
✅ LinkedIn connected as <DISPLAY_NAME>.

Next: set up your brand voice so every post sounds like you, not generic AI. I'll ask you 8 quick questions — takes 2 minutes.
```

And this `presentation` block:

```json
{
  "blocks": [
    { "type": "buttons", "buttons": [
      { "label": "🎯 Set up brand voice", "action": { "type": "callback", "value": "voice_yes" }, "style": "primary" },
      { "label": "Skip for now", "action": { "type": "callback", "value": "voice_skip" }, "style": "secondary" }
    ]}
  ]
}
```

**STOP.** Wait for user.
- `voice_yes` / yes / ok / ready → start `linkedin-brand-voice` onboarding interview immediately
- `voice_skip` / skip / no / later → show full menu (Fully set up flow)

---

## Flow: OAuth + profile done, no strategy (OAUTH=true, PROFILE=true, STRATEGY=false)

Reply with:

```
✅ LinkedIn connected | ✅ Brand voice configured

One optional step: your content strategy. This sets posting frequency, content pillars, and ensures every post ties to a business goal.
```

And this `presentation` block:

```json
{
  "blocks": [
    { "type": "buttons", "buttons": [
      { "label": "📅 Set up strategy", "action": { "type": "callback", "value": "strategy_yes" }, "style": "primary" },
      { "label": "Skip, just post", "action": { "type": "callback", "value": "strategy_skip" }, "style": "secondary" }
    ]}
  ]
}
```

**STOP.** Wait for user.
- `strategy_yes` / yes → start `linkedin-strategy` setup immediately
- `strategy_skip` / skip / topic given → go to `linkedin-publish`

---

## Flow: Fully set up (OAUTH=true, PROFILE=true, STRATEGY=true)

Reply:

```
✅ You're all set up, <DISPLAY_NAME>.

Here's what I can help you with right now:

📝 *Write a post* — give me a topic, article, or bullet points
📅 *What should I post?* — I'll suggest ideas from your content calendar
🔗 *Check my linkedin profile* — see improvement suggestions
📊 *How are my posts doing?* — performance stats (coming soon)

What would you like to do?
```

---

## Flow: Partially set up (OAUTH=true, PROFILE=true or false, POSTS > 0)

If user has posted but profile is missing, skip the "next step" nudge and just show the full menu above. Don't block power users.

---

## Status command

**Trigger:** user says "what's my setup status", "am I set up", "show my linkedin status"

Run **Setup State Check**, then reply:

```
**Your LinkedIn Assistant Status**

LinkedIn account: <✅ Connected as DISPLAY_NAME | ❌ Not connected>
Brand voice profile: <✅ Configured | ❌ Not set up>
Content strategy: <✅ Active | ❌ Not set up>
Posts published: <POST_COUNT>

<If anything missing: "Want me to set up the missing pieces? Just say the word.">
```

---

## Handoff table

Once the user indicates what they want to do, route to the correct skill:

| User intent | Route to |
|-------------|----------|
| Link / connect LinkedIn | `linkedin-publish` — OAuth Flow |
| Set up voice / brand | `linkedin-brand-voice` — Onboarding Interview |
| Set up strategy | `linkedin-strategy` — Strategy Setup |
| Write / publish a post | `linkedin-publish` (after brand voice check) |
| Check / improve profile | `linkedin-profile-sync` |
| Content ideas / calendar | `linkedin-strategy` — Topic Suggestions |
