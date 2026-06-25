---
name: linkedin-publish
description: Publish text or image posts to LinkedIn on behalf of multiple Telegram users. Handles per-user OAuth linking automatically.
user-invocable: true
metadata: {"openclaw":{"requires":{"env":["LINKEDIN_CLIENT_ID","LINKEDIN_CLIENT_SECRET","LINKEDIN_REDIRECT_URI"]}}}
triggers:
  - "publish to linkedin"
  - "post to linkedin"
  - "share on linkedin"
  - "linkedin article"
  - "publish article to linkedin"
  - "post article on linkedin"
  - "linkedin post"
  - "share article linkedin"
  - "cross-post to linkedin"
  - "connect linkedin"
  - "link linkedin account"
  - "linkedin post with image"
  - "post image to linkedin"
  - "share image on linkedin"
---

# LinkedIn Publish Skill

> ⚠️ READ THIS FIRST — MANDATORY RULES:
> 1. **NEVER write scripts to /tmp or anywhere else.** The helper already exists.
> 2. **NEVER use grep/cut/sed/cat/read-tool to get the access token.** The helper handles it.
> 3. **NEVER create a new bash script for LinkedIn.** Use ONLY `{baseDir}/li-post.sh`.
> 4. **NEVER analyze or describe an attached image.** Pass its path directly to li-post.sh.
> 5. **DO NOT narrate steps.** Run the command, show the result.

---

## Step 1 — Check token status (ONE bash command)

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

- `NO_TOKEN` → go to **OAuth Flow**
- `EXPIRED` → go to **Refresh Token**
- `OK` → go to **Publish**

---

## OAuth Flow (NO_TOKEN only)

Generate auth URL and send to user. Stop and wait for them to paste the callback JSON.

```bash
ENC_REDIRECT=$(printf '%s' "$LINKEDIN_REDIRECT_URI" | jq -sRr @uri)
echo "https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=${LINKEDIN_CLIENT_ID}&redirect_uri=${ENC_REDIRECT}&scope=openid%20profile%20w_member_social&state=${TELEGRAM_USER_ID}"
```

Reply:
```
To publish on LinkedIn I need your authorisation first.

👉 <AUTH_URL>

After approving, paste the JSON from the redirect page here.
```

**STOP. Wait for user to paste `{"code":"...","state":"..."}`.**

When they paste it → run **Exchange Code**, then immediately run **Publish**.

### Exchange Code

Extract the `code` value from the JSON the user pasted. Verify `state` matches `$TELEGRAM_USER_ID`. Then run ONE command:

```bash
{baseDir}/li-auth.sh exchange "$TELEGRAM_USER_ID" "<CODE_FROM_USER_MESSAGE>"
```

Output:
- `LINKED: <name>` → success, proceed to Publish
- `ERROR: <msg>` → show error, offer to retry

Reply `✅ LinkedIn account linked: <DISPLAY_NAME>` then immediately run **Publish**.

---

## Refresh Token (EXPIRED only)

```bash
{baseDir}/li-auth.sh refresh "$TELEGRAM_USER_ID"
```

Output:
- `REFRESHED` → go to **Publish**
- `REFRESH_FAILED: ...` → go to **OAuth Flow**

---

## Publish

### Step 0 — Style gate (optional, fast)

If a `linkedin-brand-voice` profile exists for this user, invoke the **Style Gate** from that skill before posting:
- Read `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/profile.md` with the file `read` tool
- If file found → run the style gate check from `linkedin-brand-voice` SKILL.md
- If file not found (ENOENT) → skip silently and continue

### Step 1 — Check for image

Before calling `li-post.sh`, check whether the user provided an image:

- **Image present** (Telegram photo or URL in message) → use **Image post** below
- **No image provided** → ask the user first:
  ```
  Would you like to add an image to this post? 📸 Send one now, or reply *no* to post as text.
  ```
  **STOP. Wait for user response.**
  - User sends an image → use **Image post**
  - User replies "no" / "skip" / confirms text only → use **Text post**

### Text post

```bash
{baseDir}/li-post.sh "$TELEGRAM_USER_ID" text "<POST_BODY_PLAIN_TEXT>"
```

### Image post

**Telegram photos sent to the bot are already saved locally.**  
Their path is always: `/data/openclaw/media/inbound/<uuid>.jpg`  
The UUID is visible in the image URL shown in the chat context (e.g. `...media/inbound/b8f3bfc6-....jpg`).  
**Use this path directly. Do NOT try to download, vision-analyze, or describe the image.**

```bash
IMAGE_PATH="/data/openclaw/media/inbound/<uuid>.jpg"
{baseDir}/li-post.sh "$TELEGRAM_USER_ID" image "$IMAGE_PATH" "<POST_BODY_PLAIN_TEXT>"
```

If the image comes from a URL (not Telegram), download first:
```bash
curl -sL "<IMAGE_URL>" -o /tmp/li_img
{baseDir}/li-post.sh "$TELEGRAM_USER_ID" image /tmp/li_img "<POST_BODY_PLAIN_TEXT>"
```

### Reading output

| Output starts with | Meaning |
|--------------------|---------|
| `OK:` | Success — extract URL and reply to user |
| `NO_TOKEN` | Go to OAuth Flow |
| `TOKEN_EXPIRED` | Go to Refresh Token |
| `ERROR <code>:` | Report code and body verbatim |

### Reply on success

```
✅ Published to LinkedIn (as <DISPLAY_NAME from li-post.sh output>):
→ <URL from OK: line>

Characters: <CHARS>
```

### Save post record (MANDATORY after every successful publish)

After replying to the user, write a post record to the brain. **Do not skip this step.**

- **Path:** `/data/workspace/social/linkedin/<TELEGRAM_USER_ID>/posts/<YYYY-MM-DD>-<slug>.md`
  - `slug` = first 5 words of post body, lowercased, spaces replaced with hyphens, non-alphanumeric stripped
  - Example: `2026-06-25-google-openrl-changes-everything-for.md`
- **Tool:** file `write`

```markdown
# <First line of post body>

**Published:** <YYYY-MM-DDTHH:MM:SSZ>
**LinkedIn URL:** <URL from OK: line>
**Post URN:** <URN extracted from URL — e.g. urn:li:share:7475893724938395648>
**Format:** <text | image>
**Characters:** <CHARS>
**Pillar:** <pillar if known from brand-voice draft, else "(unknown)">
**Image:** <image path if image post, else "(none)">

## Post Body

<full post text>

## Performance

*(populated later by linkedin-analytics)*

- **Impressions:** —
- **Reactions:** —
- **Comments:** —
- **Shares:** —
- **Last checked:** —
```

---

## Error Reference

| HTTP | Cause | Fix |
|------|-------|-----|
| 401 | Token invalid | Refresh, then re-auth if still 401 |
| 403 | Missing scope | Re-auth |
| 422 | Bad payload | Check li-post.sh output for details |
| 429 | Rate limited | Wait, retry later |
