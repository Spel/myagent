---
name: linkedin-daily-brief
description: Morning brief: researches today's news, drafts 2-3 ready-to-publish posts in user's brand voice. User taps Publish → auto-posts.
user-invocable: true
metadata: {"openclaw":{"requires":{"env":["LINKEDIN_CLIENT_ID"]}}}
triggers:
  - "morning brief"
  - "daily brief"
  - "give me posts for today"
  - "what should i post today"
  - "ready posts"
  - "draft posts for me"
  - "what's happening in my industry"
  - "brief me"
  - "show me today's posts"
---

# LinkedIn Daily Brief Skill

> ⚠️ MANDATORY RULES:
> 1. **Draft COMPLETE posts — not angles or ideas.** Every draft must be publish-ready in the user's voice.
> 2. **Approve = immediate publish.** When the user taps ✅ Publish, call `li-post.sh` right away. No extra confirmation.
> 3. **Per-user isolation.** All data keyed by `$TELEGRAM_USER_ID`.
> 4. **Source everything.** Every draft must have a real, recent (≤48h) source URL.
> 5. **DO NOT narrate steps.** Show results directly.
> 6. **Max 3 drafts per day.** Quality over quantity.

---

## When this runs

- **Daily cron** (8 AM user timezone) — fires before the coach check at 9 AM
- **User manually asks** — "give me posts for today", "morning brief", etc.

---

## Flow A: Generate Morning Brief (cron or manual trigger)

### Step 1 — Load user context (ONE bash block)

```bash
UID="${TELEGRAM_USER_ID}"
BASE="/data/workspace/social/linkedin/$UID"
TOKEN_STORE=/data/openclaw/linkedin-tokens.json
TODAY=$(date +%Y-%m-%d)
PENDING_DIR="$BASE/pending"

# OAuth check
ACCESS_TOKEN=$(jq -r --arg u "$UID" '.[$u].access_token // empty' "$TOKEN_STORE" 2>/dev/null)
DISPLAY_NAME=$(jq -r --arg u "$UID" '.[$u].display_name // "there"' "$TOKEN_STORE" 2>/dev/null)

# Check if brief already sent today
BRIEF_FLAG="$PENDING_DIR/.brief-sent-$TODAY"
[ -f "$BRIEF_FLAG" ] && echo "ALREADY_SENT=true" || echo "ALREADY_SENT=false"

# Load brand voice pillars and tone
PILLARS=""
TONE=""
if [ -f "$BASE/profile.md" ]; then
  PILLARS=$(grep -A 10 "Content Pillars\|pillars:" "$BASE/profile.md" | head -12)
  TONE=$(grep -A 5 "Tone\|Voice\|Style" "$BASE/profile.md" | head -6)
fi

# Load posting frequency context
CADENCE=""
if [ -f "$BASE/strategy.md" ]; then
  CADENCE=$(grep -i "cadence\|frequency\|per week\|posts/week" "$BASE/strategy.md" | head -1)
fi

# Check posts already published today
POSTS_TODAY=$(find "$BASE/posts/" -name "${TODAY}-*.md" 2>/dev/null | wc -l | tr -d ' ')

mkdir -p "$PENDING_DIR"

echo "UID=$UID"
echo "NAME=$DISPLAY_NAME"
echo "TODAY=$TODAY"
echo "POSTS_TODAY=$POSTS_TODAY"
echo "PILLARS_BLOCK=$PILLARS"
echo "TONE_BLOCK=$TONE"
```

**If no token / not connected:** Skip silently (cron) or route to onboarding (manual).
**If `ALREADY_SENT=true` and manual trigger:** Proceed — user is explicitly asking for a refresh.
**If `ALREADY_SENT=true` and cron trigger:** Skip silently.

### Step 2 — Research today's news per pillar

Use the user's content pillars to run targeted web searches. Find news published in the **last 48 hours**.

For each pillar (pick the 2-3 most relevant):
```
search: "<pillar topic> news today 2026" OR "<pillar topic> latest" site:techcrunch.com OR site:hbr.org OR site:venturebeat.com OR site:forbes.com
```

Also run one broad signal search:
```
search: "linkedin viral post today <user's industry>"
```

**Quality bar:** Only use a story if:
- Published within 48 hours (verify the date)
- Directly relevant to at least one pillar
- Has a clear opinion angle (not just "X company did Y")
- Has a real URL you can cite

Discard anything older, vague, or already covered in the user's recent posts.

**Target: 2-3 strong stories. Stop after finding 3 — don't over-research.**

### Step 3 — Draft each post in the user's brand voice

For each story, write a complete LinkedIn post using ALL of these rules:

**Post structure (Gary Vee framework from user's profile):**
1. **Hook** (line 1): Bold claim, surprising stat, or provocative question. ≤12 words. No "I" opener.
2. **Body** (lines 2-7): 3-5 punchy paragraphs, 1-2 sentences each. No fluff. Insight > information.
3. **CTA** (last line): One direct question or call to action. Not "thoughts?" — be specific.
4. **Hashtags** (after CTA): 3-5 from user's profile hashtag list.

**Voice rules:**
- Mirror the user's tone from `profile.md`
- Write as if the user is speaking, not an AI summarising
- Take a clear position — "X matters because Y" not "X is interesting"
- Make it actionable: reader should learn something or want to do something

**Length:** 150-250 words. Never shorter than 100 words or longer than 300.

### Step 4 — Save drafts as pending files

For each draft (n = 1, 2, 3):

```bash
UID="${TELEGRAM_USER_ID}"
TODAY=$(date +%Y-%m-%d)
PENDING_DIR="/data/workspace/social/linkedin/$UID/pending"
mkdir -p "$PENDING_DIR"

# Save draft n (repeat for each)
cat > "$PENDING_DIR/${TODAY}-draft-<n>.md" << 'DRAFT_EOF'
---
date: <TODAY>
n: <n>
pillar: <pillar name>
source: <source URL>
source_date: <source publication date>
status: pending
---

<FULL POST TEXT — exactly what will be published>
DRAFT_EOF

echo "SAVED: $PENDING_DIR/${TODAY}-draft-<n>.md"
```

Mark brief as sent:
```bash
touch "/data/workspace/social/linkedin/$UID/pending/.brief-sent-$(date +%Y-%m-%d)"
```

### Step 5 — Send drafts to user via Telegram

Send a brief intro, then send each draft as a separate message with its own buttons.

**Intro message:**
```
Good morning, <NAME>! ☀️

Here are <N> posts ready to publish today — all based on fresh news from your industry. Tap ✅ to publish any immediately.
```

**For each draft, send this message:**
```
📝 Post <n>/<total> — <pillar name>

<FULL POST TEXT>

━━━━━━━━━━━
Source: <source title> (<source URL>)
```

With buttons:
```json
{
  "action": "send",
  "message": "📝 Post <n>/<total> — <pillar name>\n\n<FULL POST TEXT>\n\n━━━━━━━━━━━\nSource: <source title> (<source URL>)",
  "presentation": {
    "blocks": [
      { "type": "buttons", "buttons": [
        { "label": "✅ Publish now", "action": { "type": "callback", "value": "brief_approve_<TODAY>-<n>" }, "style": "success" },
        { "label": "✏️ Edit first",  "action": { "type": "callback", "value": "brief_edit_<TODAY>-<n>" } },
        { "label": "⏭️ Skip",        "action": { "type": "callback", "value": "brief_skip_<TODAY>-<n>" }, "style": "secondary" }
      ]}
    ]
  }
}
```

> Replace `<TODAY>` with the actual date (e.g. `2026-07-02`) and `<n>` with the draft number.
> The callback value must be exact — it's used to load the right draft file.

---

## Flow B: Callback — Approve & Publish (`brief_approve_<date>-<n>`)

When the incoming message matches `brief_approve_YYYY-MM-DD-<n>`:

### Step 1 — Parse callback and load draft

```bash
CALLBACK="$1"  # e.g. brief_approve_2026-07-02-1
# Extract date and n from callback
DATE_N=$(echo "$CALLBACK" | sed 's/brief_approve_//')
# DATE_N is now e.g. "2026-07-02-1"
# Split: last segment after final dash is n, rest is date
N="${DATE_N##*-}"
DATE="${DATE_N%-*}"

UID="${TELEGRAM_USER_ID}"
DRAFT_FILE="/data/workspace/social/linkedin/$UID/pending/${DATE}-draft-${N}.md"

if [ ! -f "$DRAFT_FILE" ]; then
  echo "DRAFT_NOT_FOUND"
  exit 1
fi

# Extract post text (everything after the frontmatter ---)
POST_TEXT=$(awk '/^---/{count++; next} count==2{print}' "$DRAFT_FILE")
echo "POST_TEXT_START"
echo "$POST_TEXT"
echo "POST_TEXT_END"
```

**If `DRAFT_NOT_FOUND`:** Reply "I can't find that draft — it may have already been published or expired. Use /linkedin-publish to post manually."

### Step 2 — Publish immediately

```bash
{baseDir of linkedin-publish}/li-post.sh "$TELEGRAM_USER_ID" "<POST_TEXT_EXTRACTED>"
```

Use the `li-post.sh` helper from `linkedin-publish` skill. Path: `{skills dir}/linkedin-publish/li-post.sh`.

On success (`OK: <post_url>`):
1. Move draft to published:
```bash
DATE_N=$(echo "$CALLBACK" | sed 's/brief_approve_//')
N="${DATE_N##*-}"
DATE="${DATE_N%-*}"
SLUG="brief-$(date +%Y-%m-%d)-${N}"
UID="${TELEGRAM_USER_ID}"
mkdir -p "/data/workspace/social/linkedin/$UID/posts"
mv "/data/workspace/social/linkedin/$UID/pending/${DATE}-draft-${N}.md" \
   "/data/workspace/social/linkedin/$UID/posts/${SLUG}.md"
# Update status in file
sed -i 's/^status: pending/status: published/' "/data/workspace/social/linkedin/$UID/posts/${SLUG}.md"
```
2. Reply with confirmation:
```
✅ Published!

<POST_URL>

Great work showing up today, <NAME>. That's how brands are built.
```

On failure: Show the error and offer to retry manually via `/linkedin-publish`.

### Step 3 — Check remaining drafts

```bash
UID="${TELEGRAM_USER_ID}"
DATE=$(date +%Y-%m-%d)
REMAINING=$(ls "/data/workspace/social/linkedin/$UID/pending/${DATE}-draft-"*.md 2>/dev/null | wc -l | tr -d ' ')
echo "REMAINING=$REMAINING"
```

If `REMAINING > 0`: "You have <N> more drafts from this morning. Check your earlier messages to publish them."

---

## Flow C: Callback — Edit Draft (`brief_edit_<date>-<n>`)

When the incoming message matches `brief_edit_YYYY-MM-DD-<n>`:

### Step 1 — Load draft

```bash
CALLBACK="$1"
DATE_N=$(echo "$CALLBACK" | sed 's/brief_edit_//')
N="${DATE_N##*-}"
DATE="${DATE_N%-*}"
UID="${TELEGRAM_USER_ID}"
DRAFT_FILE="/data/workspace/social/linkedin/$UID/pending/${DATE}-draft-${N}.md"
POST_TEXT=$(awk '/^---/{count++; next} count==2{print}' "$DRAFT_FILE")
echo "$POST_TEXT"
```

### Step 2 — Show draft and ask for edits

Send the draft text with:
```
Here's draft <n>:

<POST TEXT>

━━━━━━━━━━━
What should I change? Tell me (e.g. "make it shorter", "add a stat", "change the tone to more casual", "rewrite the hook") and I'll update it.
```

Hand off to `linkedin-brand-voice` for the rewrite, then re-present with ✅ Publish / ✏️ Edit again / ⏭️ Skip buttons using the **same callback values** so approval still works.

After rewriting, **overwrite the draft file** with the updated text so ✅ Publish picks up the new version.

---

## Flow D: Callback — Skip Draft (`brief_skip_<date>-<n>`)

When the incoming message matches `brief_skip_YYYY-MM-DD-<n>`:

```bash
CALLBACK="$1"
DATE_N=$(echo "$CALLBACK" | sed 's/brief_skip_//')
N="${DATE_N##*-}"
DATE="${DATE_N%-*}"
UID="${TELEGRAM_USER_ID}"
DRAFT_FILE="/data/workspace/social/linkedin/$UID/pending/${DATE}-draft-${N}.md"
[ -f "$DRAFT_FILE" ] && sed -i 's/^status: pending/status: skipped/' "$DRAFT_FILE"
```

Reply:
```
Got it, skipped. 👍
```

No further action. Don't offer alternatives unless the user asks.

---

## Flow E: All-Users Cron Run

When cron fires without a specific `TELEGRAM_USER_ID`:

```bash
TOKEN_STORE=/data/openclaw/linkedin-tokens.json
[ -f "$TOKEN_STORE" ] || exit 0
jq -r 'to_entries[] | select(.value.access_token != null and .value.access_token != "") | .key' "$TOKEN_STORE"
```

For each user ID returned, run **Flow A** above with that user's `TELEGRAM_USER_ID`.
Skip users with no profile.md (not yet set up).

---

## Brief quality rules (always apply)

- **No generic takes.** "AI is changing everything" is noise. "Here's the specific thing AI changed this week that affects [persona]" is signal.
- **Be opinionated.** A post without a point of view is forgettable.
- **Real sources only.** Never cite a URL you haven't verified. Never fabricate publication dates.
- **One idea per post.** Don't cram 3 insights into one post. Each draft = one clear idea.
- **Short paragraphs.** LinkedIn renders single-line-break paragraphs. Write accordingly.
