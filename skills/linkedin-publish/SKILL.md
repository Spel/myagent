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
python3 -c "
import urllib.parse, os
p = {'response_type':'code','client_id':os.environ['LINKEDIN_CLIENT_ID'],
     'redirect_uri':os.environ['LINKEDIN_REDIRECT_URI'],
     'scope':'openid profile w_member_social','state':os.environ['TELEGRAM_USER_ID']}
print('https://www.linkedin.com/oauth/v2/authorization?'+urllib.parse.urlencode(p))
"
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

```bash
CODE="<parsed from user message>"
# Verify state matches TELEGRAM_USER_ID before proceeding

RESP=$(curl -s -X POST "https://www.linkedin.com/oauth/v2/accessToken" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=authorization_code" \
  --data-urlencode "code=$CODE" \
  --data-urlencode "redirect_uri=$LINKEDIN_REDIRECT_URI" \
  --data-urlencode "client_id=$LINKEDIN_CLIENT_ID" \
  --data-urlencode "client_secret=$LINKEDIN_CLIENT_SECRET")

ACCESS_TOKEN=$(echo "$RESP" | jq -r '.access_token')
REFRESH_TOKEN=$(echo "$RESP" | jq -r '.refresh_token // empty')
EXPIRES_AT=$(($(date +%s) + $(echo "$RESP" | jq -r '.expires_in')))

PROFILE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "https://api.linkedin.com/v2/userinfo")
LINKEDIN_URN="urn:li:person:$(echo "$PROFILE" | jq -r '.sub')"
DISPLAY_NAME=$(echo "$PROFILE" | jq -r '.name')

TOKEN_STORE=/data/openclaw/linkedin-tokens.json
jq --arg u "$TELEGRAM_USER_ID" --arg t "$ACCESS_TOKEN" --arg r "$REFRESH_TOKEN" \
   --argjson e "$EXPIRES_AT" --arg urn "$LINKEDIN_URN" --arg n "$DISPLAY_NAME" \
   --arg l "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
   '.[$u]={"access_token":$t,"refresh_token":$r,"expires_at":$e,"linkedin_urn":$urn,"display_name":$n,"linked_at":$l}' \
   "$TOKEN_STORE" > /tmp/.li_tmp && mv /tmp/.li_tmp "$TOKEN_STORE"

echo "LINKED: $DISPLAY_NAME"
```

Reply `✅ LinkedIn account linked: <DISPLAY_NAME>` then immediately run **Publish**.

---

## Refresh Token (EXPIRED only)

```bash
TOKEN_STORE=/data/openclaw/linkedin-tokens.json
REFRESH_TOKEN=$(jq -r --arg u "$TELEGRAM_USER_ID" '.[$u].refresh_token' "$TOKEN_STORE")
RESP=$(curl -s -X POST "https://www.linkedin.com/oauth/v2/accessToken" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=refresh_token" \
  --data-urlencode "refresh_token=$REFRESH_TOKEN" \
  --data-urlencode "client_id=$LINKEDIN_CLIENT_ID" \
  --data-urlencode "client_secret=$LINKEDIN_CLIENT_SECRET")
NEW_TOKEN=$(echo "$RESP" | jq -r '.access_token')
NEW_EXPIRES=$(($(date +%s) + $(echo "$RESP" | jq -r '.expires_in')))
NEW_REFRESH=$(echo "$RESP" | jq -r '.refresh_token // empty')
[ -z "$NEW_TOKEN" ] && echo "REFRESH_FAILED" && exit 1
jq --arg u "$TELEGRAM_USER_ID" --arg t "$NEW_TOKEN" --argjson e "$NEW_EXPIRES" \
   --arg r "${NEW_REFRESH:-$REFRESH_TOKEN}" \
   '.[$u] |= . + {"access_token":$t,"expires_at":$e,"refresh_token":$r}' \
   "$TOKEN_STORE" > /tmp/.li_tmp && mv /tmp/.li_tmp "$TOKEN_STORE"
echo "REFRESHED"
```

If `REFRESH_FAILED` → go to **OAuth Flow**.  
If `REFRESHED` → go to **Publish**.

---

## Publish

### Step 0 — Style gate (optional, fast)

If a `linkedin-brand-voice` profile exists for this user, invoke the **Style Gate** from that skill before posting:
- Run `get_page social/linkedin/<TELEGRAM_USER_ID>/profile`
- If page found → run the style gate check from `linkedin-brand-voice` SKILL.md
- If page not found → skip silently and continue

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

Characters: <CHARS>/3000
```

---

## Error Reference

| HTTP | Cause | Fix |
|------|-------|-----|
| 401 | Token invalid | Refresh, then re-auth if still 401 |
| 403 | Missing scope | Re-auth |
| 422 | Bad payload | Check li-post.sh output for details |
| 429 | Rate limited | Wait, retry later |
