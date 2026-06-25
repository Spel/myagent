---
name: linkedin-publish
version: 2.0.0
description: |
  Publish articles and posts to LinkedIn on behalf of multiple users.
  Each Telegram user is linked to their own LinkedIn OAuth token. If no
  token exists for the requesting Telegram user, the skill generates a
  personalised OAuth authorisation URL and sends it via Telegram. After the
  user completes the OAuth flow the callback saves their tokens; subsequent
  publish requests use those tokens automatically.
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
mutating: true
---

# LinkedIn Publish Skill

## Contract

This skill guarantees:
- One LinkedIn account per Telegram user — tokens are stored and looked up by Telegram user ID
- First-time users receive an OAuth authorisation URL via Telegram; no manual token management needed
- Tokens are stored in `/data/openclaw/linkedin-tokens.json` (persisted via the Docker volume)
- Idempotency: duplicate-post check runs before every publish
- Returns a direct URL to the published post on success
- App credentials (`client_id`, `client_secret`) come from env vars — never hardcoded in the skill

---

## App Credentials (already in `.env`)

```
LINKEDIN_CLIENT_ID=773oa2pre7xcem
LINKEDIN_CLIENT_SECRET=IQRDBCjvk5vMMo8G
LINKEDIN_REDIRECT_URI=https://nodered-5234-671620977218781100000035.ubosaibotprod.ubos.tech/auth/linkedin/callback
```

The **token store** lives at `/data/openclaw/linkedin-tokens.json`.  
Schema (one entry per user):

```json
{
  "<telegram_user_id>": {
    "access_token": "...",
    "refresh_token": "...",
    "expires_at": 1234567890,
    "linkedin_urn": "urn:li:person:...",
    "display_name": "Jane Doe",
    "linked_at": "2026-06-25T12:00:00Z"
  }
}
```

---

## Phases

### Phase 0 — Identify the Requesting Telegram User

Read `telegram_user_id` from the message context (available as the sender's
Telegram ID). This is the key used for all token lookups.

### Phase 1 — Token Lookup

```bash
TOKEN_STORE=/data/openclaw/linkedin-tokens.json
TELEGRAM_USER_ID="<sender_id>"

# Initialize store if it doesn't exist yet
[ -f "$TOKEN_STORE" ] || echo "{}" > "$TOKEN_STORE"

# Check if token exists for this user
ACCESS_TOKEN=$(jq -r --arg uid "$TELEGRAM_USER_ID" '.[$uid].access_token // empty' "$TOKEN_STORE" 2>/dev/null)
EXPIRES_AT=$(jq -r --arg uid "$TELEGRAM_USER_ID" '.[$uid].expires_at // 0' "$TOKEN_STORE" 2>/dev/null)
NOW=$(date +%s)
```

- If `ACCESS_TOKEN` is empty → **go to Phase 2 (OAuth flow)**
- If `EXPIRES_AT` < `NOW + 3600` → **go to Phase 1b (token refresh)**
- Otherwise → **proceed to Phase 3 (publish)**

#### Phase 1b — Refresh Expired Token

```bash
REFRESH_TOKEN=$(jq -r --arg uid "$TELEGRAM_USER_ID" '.[$uid].refresh_token' "$TOKEN_STORE")

RESPONSE=$(curl -s -X POST "https://www.linkedin.com/oauth/v2/accessToken" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=${REFRESH_TOKEN}" \
  -d "client_id=${LINKEDIN_CLIENT_ID}" \
  -d "client_secret=${LINKEDIN_CLIENT_SECRET}")

NEW_TOKEN=$(echo "$RESPONSE" | jq -r '.access_token')
NEW_EXPIRES_IN=$(echo "$RESPONSE" | jq -r '.expires_in')
NEW_REFRESH=$(echo "$RESPONSE" | jq -r '.refresh_token // empty')
NEW_EXPIRES_AT=$((NOW + NEW_EXPIRES_IN))

# Update token store
jq --arg uid "$TELEGRAM_USER_ID" \
   --arg tok "$NEW_TOKEN" \
   --arg exp "$NEW_EXPIRES_AT" \
   --arg ref "${NEW_REFRESH:-$REFRESH_TOKEN}" \
   '.[$uid].access_token = $tok | .[$uid].expires_at = ($exp|tonumber) | .[$uid].refresh_token = $ref' \
   "$TOKEN_STORE" > /tmp/li_tokens_tmp.json && mv /tmp/li_tokens_tmp.json "$TOKEN_STORE"
```

### Phase 2 — First-Time OAuth: Send Auth URL to User

If no token exists for this Telegram user, generate the authorisation URL and
send it back via Telegram. Use the Telegram user ID as the `state` parameter
so the callback can match the authorisation to the right user.

```bash
SCOPE="openid%20profile%20w_member_social"
STATE="${TELEGRAM_USER_ID}"   # passed through OAuth round-trip; callback uses this to store tokens

AUTH_URL="https://www.linkedin.com/oauth/v2/authorization?\
response_type=code\
&client_id=${LINKEDIN_CLIENT_ID}\
&redirect_uri=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${LINKEDIN_REDIRECT_URI}'))")\
&scope=${SCOPE}\
&state=${STATE}"
```

Reply to the user in Telegram:

```
To publish on LinkedIn I need your authorisation.

Please click the link below, sign in with LinkedIn, and allow access:

👉 <AUTH_URL>

Once you've approved, come back here and repeat your publish request.
```

**Stop here.** Do not proceed to publish until the callback has saved the
token for this user.

#### OAuth Callback (handled by Node-RED at `LINKEDIN_REDIRECT_URI`)

The Node-RED flow receives `?code=...&state=<telegram_user_id>` and must:

1. Exchange the code for tokens:
```bash
curl -s -X POST "https://www.linkedin.com/oauth/v2/accessToken" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=<CODE>" \
  -d "redirect_uri=<LINKEDIN_REDIRECT_URI>" \
  -d "client_id=<LINKEDIN_CLIENT_ID>" \
  -d "client_secret=<LINKEDIN_CLIENT_SECRET>"
```

2. Fetch the user's LinkedIn profile URN and display name:
```bash
curl -s -H "Authorization: Bearer <ACCESS_TOKEN>" \
  "https://api.linkedin.com/v2/userinfo"
# Returns: { "sub": "<numeric_id>", "name": "Jane Doe", ... }
# URN = "urn:li:person:" + sub
```

3. Write to `/data/openclaw/linkedin-tokens.json` (append/update by `state` key):
```json
{
  "<telegram_user_id>": {
    "access_token": "...",
    "refresh_token": "...",
    "expires_at": <unix_timestamp>,
    "linkedin_urn": "urn:li:person:...",
    "display_name": "Jane Doe",
    "linked_at": "2026-06-25T12:00:00Z"
  }
}
```

4. Send a Telegram message to the user (using `TELEGRAM_BOT_TOKEN` and the `state` as chat ID):
```
✅ LinkedIn account linked: Jane Doe
You can now publish posts to LinkedIn. Repeat your last request.
```

---

### Phase 3 — Prepare Content

1. Read the source content (brain page, markdown file, or inline text).
2. Strip markdown syntax — LinkedIn feed posts render plain text only.
3. Determine post type:
   - **Short post** (≤ 3000 chars): `shareMediaCategory: NONE`
   - **Post with URL**: `shareMediaCategory: ARTICLE` + `originalUrl`
4. Trim to 3000 characters; append `\n\nRead more: <url>` if truncated.
5. Append 3–5 relevant hashtags.

### Phase 4 — Duplicate Check

```bash
LINKEDIN_URN=$(jq -r --arg uid "$TELEGRAM_USER_ID" '.[$uid].linkedin_urn' "$TOKEN_STORE")

curl -s \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  "https://api.linkedin.com/v2/ugcPosts?q=authors&authors=List($(python3 -c "import urllib.parse; print(urllib.parse.quote('$LINKEDIN_URN'))"))" \
  | jq -r '.elements[0].specificContent."com.linkedin.ugc.ShareContent".shareCommentary.text // ""' \
  | head -c 100
```

If the first 100 characters match the new post (published within the last 24 h), abort and notify user.

### Phase 5 — Publish

```bash
curl -s -X POST "https://api.linkedin.com/v2/ugcPosts" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -d '{
    "author": "'"$LINKEDIN_URN"'",
    "lifecycleState": "PUBLISHED",
    "specificContent": {
      "com.linkedin.ugc.ShareContent": {
        "shareCommentary": { "text": "<POST_BODY>" },
        "shareMediaCategory": "NONE"
      }
    },
    "visibility": {
      "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
    }
  }'
```

For a post with an article link, replace `shareMediaCategory` and add:
```json
"shareMediaCategory": "ARTICLE",
"media": [{
  "status": "READY",
  "originalUrl": "<ARTICLE_URL>",
  "title": { "text": "<TITLE>" },
  "description": { "text": "<EXCERPT>" }
}]
```

### Phase 6 — Confirm

Parse HTTP 201 response; extract `x-restli-id` header for the post URN.

```
Published to LinkedIn (as Jane Doe):
→ https://www.linkedin.com/feed/update/urn:li:ugcPost:<id>/

Characters: <n>/3000
Hashtags: #tag1 #tag2 #tag3
```

---

## Output Format

**Success:**
```
✅ Published to LinkedIn (as <display_name>):
→ https://www.linkedin.com/feed/update/<urn>/

Characters: <n>/3000
Hashtags: #tag1 #tag2
```

**Not yet linked:**
```
⚠️ No LinkedIn account linked for your Telegram user.
Please authorise via the link I've sent you, then retry.
```

**Error:**
```
❌ LinkedIn publish failed (HTTP <code>): <error_message>
```

---

## Error Reference

| HTTP | Meaning | Fix |
|------|---------|-----|
| 401 | Token expired or invalid | Trigger Phase 1b refresh; if that fails, re-run Phase 2 |
| 403 | Missing `w_member_social` scope | User must re-authorise with correct scopes |
| 422 | Malformed payload | Check JSON; verify author URN format |
| 429 | Rate limited (>100 posts/day) | Wait and retry |

---

## Anti-Patterns

- **Do not** store tokens anywhere except `/data/openclaw/linkedin-tokens.json`
- **Do not** share one token across multiple Telegram users
- **Do not** post raw markdown — strip to plain text first
- **Do not** exceed 3000 characters in `shareCommentary.text`
- **Do not** skip the duplicate check (Phase 4)
- **Do not** use the deprecated `/v2/shares` endpoint — use `/v2/ugcPosts`

### Phase 1 — Prepare Content

1. Read the source content (brain page, markdown file, or inline text provided by the user).
2. Determine post type:
   - **Short post** (≤ 3000 chars): plain `TEXT` share via `/ugcPosts`
   - **Article / long-form**: use LinkedIn Articles endpoint (`/articles`) or summarise + link back
   - **Post with URL**: extract URL, use `ARTICLE` share type with `originalUrl`
3. Strip markdown syntax for the LinkedIn body text (LinkedIn renders plain text only in feed posts).
4. Trim to 3000 characters max for feed posts; add a "Read more:" link if truncating.
5. Optionally generate 3–5 relevant hashtags from the content.

### Phase 2 — Duplicate Check

Before posting, search recent activity to avoid double-posting:

```bash
curl -s -H "Authorization: Bearer $LINKEDIN_ACCESS_TOKEN" \
  "https://api.linkedin.com/v2/ugcPosts?q=authors&authors=List($LINKEDIN_AUTHOR_URN)&count=5" \
  | jq '.elements[].specificContent.com.linkedin.ugc.ShareContent.shareCommentary.text' \
  | head -5
```

If the first 100 characters of the new post match an existing post from the last 24 hours, abort and report to the user.

### Phase 3 — Publish

#### Option A: Text / Link Post (most common)

```bash
curl -s -X POST "https://api.linkedin.com/v2/ugcPosts" \
  -H "Authorization: Bearer $LINKEDIN_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -d '{
    "author": "'"$LINKEDIN_AUTHOR_URN"'",
    "lifecycleState": "PUBLISHED",
    "specificContent": {
      "com.linkedin.ugc.ShareContent": {
        "shareCommentary": {
          "text": "<POST_BODY_WITH_HASHTAGS>"
        },
        "shareMediaCategory": "NONE"
      }
    },
    "visibility": {
      "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
    }
  }'
```

#### Option B: Post with Article Link

Replace `shareMediaCategory` and add a `media` array:

```json
"shareMediaCategory": "ARTICLE",
"media": [
  {
    "status": "READY",
    "originalUrl": "<ARTICLE_URL>",
    "title": { "text": "<ARTICLE_TITLE>" },
    "description": { "text": "<SHORT_EXCERPT>" }
  }
]
```

### Phase 4 — Confirm & Report

1. Parse the response: success returns HTTP 201 with header `x-restli-id` containing the post URN.
2. Construct the post URL:
   ```
   https://www.linkedin.com/feed/update/<post_urn>/
   ```
3. Report back to the user with the direct URL to the published post.
4. Optionally write a brain page at `social/linkedin/<slug>.md` recording the publish event.

---

## Output Format

On success, respond with:

```
Published to LinkedIn:
→ https://www.linkedin.com/feed/update/urn:li:ugcPost:<id>/

Title: <title or first line>
Characters: <n>/3000
Hashtags: #tag1 #tag2 #tag3
```

On failure, include the HTTP status code and full error response body for diagnosis.

---

## Error Reference

| HTTP | Meaning | Fix |
|------|---------|-----|
| 401 | Token expired or invalid | Re-run OAuth flow, update `LINKEDIN_ACCESS_TOKEN` |
| 403 | Missing `w_member_social` scope | Re-authorise app with correct scopes |
| 422 | Malformed payload | Check JSON structure; ensure `author` URN is correct |
| 429 | Rate limited | LinkedIn allows ~100 posts/day per member; wait and retry |

---

## Anti-Patterns

- **Do not** hardcode tokens in scripts — always read from env vars
- **Do not** post raw markdown — strip to plain text first
- **Do not** exceed 3000 characters in the `shareCommentary.text` field
- **Do not** post more than once per article — always run the duplicate check (Phase 2)
- **Do not** use the deprecated `/v2/shares` endpoint — use `/v2/ugcPosts`
