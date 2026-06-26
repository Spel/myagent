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
> 6. **ONE PUBLISH PER REQUEST.** Call `li-post.sh` exactly once per confirmed
>    request. The instant you get an `OK:` line, the post is LIVE and this flow
>    is DONE — report the URL and STOP. Never call `li-post.sh` again to "retry",
>    "improve the image", or "use the real image". Each call creates a brand-new
>    LinkedIn post; LinkedIn has no edit-with-media API. If you couldn't get the
>    image you wanted, do NOT silently post without it — ask the user first
>    (see **Single-publish guard** below).

---

## Single-publish guard (READ BEFORE EVERY PUBLISH)

Publishing is irreversible and creates a permanent post. To avoid the
duplicate-post problem:

- **Resolve the image BEFORE the single `li-post.sh` call.** Do all image
  retrieval/generation first. Only call `li-post.sh` once everything is ready.
- **If the intended image is not available** (generation failed, file not found,
  retrieval failed) → STOP and ask: *"I couldn't get the image ready. Post as
  text-only, or hold off so we can fix the image?"* Never auto-fallback to a
  text-only or substitute post.
- **After `OK:`** the request is complete. If the user then wants a different
  image or wording, that is a NEW request: confirm explicitly and warn it will
  create a SECOND post (the first won't be replaced).
- **Never publish the same body more than once** in a single conversation
  without the user explicitly asking for a second post.

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

### Step 1 — Confirm publish with buttons

Before calling `li-post.sh`, always show the draft and ask for confirmation using
inline buttons. **Put the draft text in the top-level `message` field** — text
inside `presentation.blocks` is NOT shown on Telegram and the send will fail
empty. Buttons go in `presentation`:

```json
{
  "action": "send",
  "message": "<DRAFT POST TEXT>\n\nReady to publish?",
  "presentation": {
    "blocks": [
      { "type": "buttons", "buttons": [
        { "label": "✅ Publish", "action": { "type": "callback", "value": "publish_yes" }, "style": "success" },
        { "label": "✏️ Edit", "action": { "type": "callback", "value": "publish_edit" } },
        { "label": "❌ Cancel", "action": { "type": "callback", "value": "publish_no" }, "style": "danger" }
      ]}
    ]
  }
}
```

**STOP. Wait for user to tap a button or reply.**

- `publish_yes` / user says "publish" / "yes" / "go" → proceed to **Step 2**
- `publish_edit` / user says "edit" / "change" / gives feedback → revise draft, show buttons again
- `publish_no` / user says "no" / "cancel" → reply "Cancelled." and stop

### Step 2 — Check for image

After the user confirms publish, check whether they provided an image:

- **Image present** (Telegram photo or URL in message) → use **Image post** below
- **No image provided** → ask with buttons (body text in `message`, buttons in
  `presentation`):

```json
{
  "action": "send",
  "message": "Add an image to this post?",
  "presentation": {
    "blocks": [
      { "type": "buttons", "buttons": [
        { "label": "📸 Send image", "action": { "type": "callback", "value": "img_send" } },
        { "label": "No image", "action": { "type": "callback", "value": "img_skip" }, "style": "secondary" }
      ]}
    ]
  }
}
```

  **STOP. Wait for user response.**
  - User sends an image or taps "Send image" → use **Image post**
  - User taps "No image" or replies "no" / "skip" → use **Text post**

### Text post

```bash
{baseDir}/li-post.sh "$TELEGRAM_USER_ID" text "<POST_BODY_PLAIN_TEXT>"
```

### Image post

There are three sources of images. Resolve to a LOCAL FILE PATH first, then make
the single `li-post.sh image` call.

**A) Image was just generated by the `image-gen` skill (LinkedIn mode).**
The skill already saved the file to
`/data/workspace/social/linkedin/$TELEGRAM_USER_ID/images/<slug>.png` and
returned that path. Use it directly — do NOT regenerate, re-download, or look
for it elsewhere.

```bash
IMAGE_PATH="/data/workspace/social/linkedin/$TELEGRAM_USER_ID/images/<slug>.png"
{baseDir}/li-post.sh "$TELEGRAM_USER_ID" image "$IMAGE_PATH" "<POST_BODY_PLAIN_TEXT>"
```

**B) User sent a photo to the bot in Telegram.**
Telegram photos are NOT automatically on disk in this deployment. Retrieve the
file via the Telegram Bot API using the photo's `file_id` (visible in the
message context), then save it under the user's images dir:

```bash
mkdir -p "/data/workspace/social/linkedin/$TELEGRAM_USER_ID/images"
FILE_ID="<file_id from the photo in chat context>"
FILE_PATH=$(curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getFile?file_id=${FILE_ID}" | jq -r '.result.file_path')
IMAGE_PATH="/data/workspace/social/linkedin/$TELEGRAM_USER_ID/images/upload-$(date +%s).jpg"
curl -sL "https://api.telegram.org/file/bot${TELEGRAM_BOT_TOKEN}/${FILE_PATH}" -o "$IMAGE_PATH"
{baseDir}/li-post.sh "$TELEGRAM_USER_ID" image "$IMAGE_PATH" "<POST_BODY_PLAIN_TEXT>"
```

If `getFile` returns `"ok": false` / 404, the `file_id` is stale — ask the user
to resend the photo. Do NOT fall back to posting without the image.

**C) Image comes from a URL.** Download first:
```bash
mkdir -p "/data/workspace/social/linkedin/$TELEGRAM_USER_ID/images"
IMAGE_PATH="/data/workspace/social/linkedin/$TELEGRAM_USER_ID/images/url-$(date +%s).jpg"
curl -sL "<IMAGE_URL>" -o "$IMAGE_PATH"
{baseDir}/li-post.sh "$TELEGRAM_USER_ID" image "$IMAGE_PATH" "<POST_BODY_PLAIN_TEXT>"
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
