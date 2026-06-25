---
name: linkedin-publish
version: 2.2.0
description: |
  Publish articles and posts to LinkedIn on behalf of multiple Telegram users.
  Each Telegram user is linked to their own LinkedIn OAuth token stored in
  /data/openclaw/linkedin-tokens.json. First-time users get an OAuth URL;
  after approving they paste the callback JSON back into the chat and the agent
  exchanges the code, saves the token, and publishes — all in one turn.
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

- One LinkedIn account per Telegram user; keyed by Telegram user ID
- Token store: `/data/openclaw/linkedin-tokens.json` (Docker volume — survives restarts)
- User pastes the callback JSON `{"code":"...","state":"..."}` back into the chat; agent exchanges it, saves the token, then publishes in the same turn
- No unnecessary pre-flight checks — act immediately based on token presence
- App credentials are in env vars: `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `LINKEDIN_REDIRECT_URI`

---

## Decision Tree — execute top-to-bottom, stop at first match

```
TOKEN_STORE=/data/openclaw/linkedin-tokens.json
[ -f "$TOKEN_STORE" ] || echo "{}" > "$TOKEN_STORE"

ACCESS_TOKEN=$(jq -r --arg u "$TELEGRAM_USER_ID" '.[$u].access_token // empty' "$TOKEN_STORE")
EXPIRES_AT=$(jq -r --arg u "$TELEGRAM_USER_ID" '.[$u].expires_at // 0' "$TOKEN_STORE")
NOW=$(date +%s)

if   [ -z "$ACCESS_TOKEN" ];              then → STEP A (send auth URL, stop)
elif [ "$EXPIRES_AT" -lt $((NOW+3600)) ]; then → STEP B (refresh token, then STEP C)
else                                           → STEP C (publish immediately)
fi
```

**A token is valid if `access_token` is a non-empty string and `expires_at > NOW`.  
Do NOT re-auth or call the token "corrupted" for any other reason.  
The only legitimate trigger for re-auth is receiving HTTP 401 from the LinkedIn API in STEP C.**

---

## STEP A — No token: send OAuth URL and stop

Generate the auth URL and send it. Then wait — when the user pastes back the callback JSON, detect it (contains `"code"` and `"state"` keys) and proceed to **STEP A2** to exchange the code.

```bash
python3 - <<'EOF'
import urllib.parse, os
params = {
    "response_type": "code",
    "client_id": os.environ["LINKEDIN_CLIENT_ID"],
    "redirect_uri": os.environ["LINKEDIN_REDIRECT_URI"],
    "scope": "openid profile w_member_social",
    "state": os.environ["TELEGRAM_USER_ID"],
}
print("https://www.linkedin.com/oauth/v2/authorization?" + urllib.parse.urlencode(params))
EOF
```

Reply exactly:
```
To publish on LinkedIn I need your authorisation first.

👉 <AUTH_URL>

After approving, paste the JSON from the redirect page here and I'll link your account and publish immediately.
```

**STOP and wait for the user to paste the callback JSON.**

---

## STEP A2 — User pasted callback JSON: exchange code and save token

Triggered when the user's message contains a JSON object with `code` and `state` fields.
Extract both fields, exchange the code, fetch the profile, save to token store, then **proceed to STEP C**.

```bash
# CODE and STATE are parsed from the user's pasted JSON
CODE="<parsed code>"
# Verify STATE matches the expected TELEGRAM_USER_ID; abort if not

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

# Fetch LinkedIn profile
PROFILE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "https://api.linkedin.com/v2/userinfo")
LINKEDIN_SUB=$(echo "$PROFILE" | jq -r '.sub')
LINKEDIN_URN="urn:li:person:$LINKEDIN_SUB"
DISPLAY_NAME=$(echo "$PROFILE" | jq -r '.name')

# Save to token store
jq --arg u "$TELEGRAM_USER_ID" \
   --arg t "$ACCESS_TOKEN" --arg r "$REFRESH_TOKEN" \
   --argjson e "$EXPIRES_AT" \
   --arg urn "$LINKEDIN_URN" --arg name "$DISPLAY_NAME" \
   --arg linked "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
   '.[$u] = {"access_token":$t,"refresh_token":$r,"expires_at":$e,"linkedin_urn":$urn,"display_name":$name,"linked_at":$linked}' \
   "$TOKEN_STORE" > /tmp/.li_tmp && mv /tmp/.li_tmp "$TOKEN_STORE"
```

If `ACCESS_TOKEN` is empty → reply with the error from `$RESP` and stop.

On success, reply `✅ LinkedIn account linked: <display_name>` then **immediately continue to STEP C** to publish (do not ask the user to repeat the request).

---

## STEP B — Token expired: refresh silently, then proceed to STEP C

```bash
REFRESH_TOKEN=$(jq -r --arg u "$TELEGRAM_USER_ID" '.[$u].refresh_token' "$TOKEN_STORE")

RESP=$(curl -s -X POST "https://www.linkedin.com/oauth/v2/accessToken" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=refresh_token" \
  --data-urlencode "refresh_token=$REFRESH_TOKEN" \
  --data-urlencode "client_id=$LINKEDIN_CLIENT_ID" \
  --data-urlencode "client_secret=$LINKEDIN_CLIENT_SECRET")

ACCESS_TOKEN=$(echo "$RESP" | jq -r '.access_token')
NEW_EXPIRES=$((NOW + $(echo "$RESP" | jq -r '.expires_in')))
NEW_REFRESH=$(echo "$RESP" | jq -r '.refresh_token // empty')

jq --arg u "$TELEGRAM_USER_ID" --arg t "$ACCESS_TOKEN" --argjson e "$NEW_EXPIRES" \
   --arg r "${NEW_REFRESH:-$REFRESH_TOKEN}" \
   '.[$u] |= . + {"access_token":$t,"expires_at":$e,"refresh_token":$r}' \
   "$TOKEN_STORE" > /tmp/.li_tmp && mv /tmp/.li_tmp "$TOKEN_STORE"
```

If `ACCESS_TOKEN` is empty after refresh → fall back to STEP A (token revoked, need re-auth).

---

## STEP C — Publish

**1. Prepare post body**

- Strip markdown to plain text
- Truncate to 3000 chars; if truncated append `\n\nRead more: <url>`
- Add 3–5 hashtags at the end if not already present

**2. Publish**

```bash
LINKEDIN_URN=$(jq -r --arg u "$TELEGRAM_USER_ID" '.[$u].linkedin_urn' "$TOKEN_STORE")
DISPLAY_NAME=$(jq -r --arg u "$TELEGRAM_USER_ID" '.[$u].display_name' "$TOKEN_STORE")

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "https://api.linkedin.com/v2/ugcPosts" \
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
    "visibility": { "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC" }
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -1)
POST_URN=$(echo "$BODY" | jq -r '.id // empty')
```

For a post with a URL, set `"shareMediaCategory": "ARTICLE"` and add:
```json
"media": [{"status":"READY","originalUrl":"<URL>","title":{"text":"<TITLE>"},"description":{"text":"<EXCERPT>"}}]
```

**3. Reply**

On HTTP 201:
```
✅ Published to LinkedIn (as <display_name>):
→ https://www.linkedin.com/feed/update/<POST_URN>/

Characters: <n>/3000
```

On error:
```
❌ LinkedIn publish failed (HTTP <HTTP_CODE>): <error detail from BODY>
```

---

## Error Reference

| HTTP | Cause | Action |
|------|-------|--------|
| 401 | Token invalid | Run STEP B refresh; if still 401 → STEP A |
| 403 | Missing `w_member_social` scope | STEP A with re-auth message |
| 422 | Bad payload | Check URN format and JSON structure |
| 429 | Rate limit (>100/day) | Tell user to retry later |

---

## Anti-Patterns

- **Never** narrate "let me check X" before acting — read the token store and act
- **Never** call a token "corrupted", "invalid", or "bad" unless the LinkedIn API returned HTTP 401
- **Never** re-auth unless: (a) no token exists, (b) `expires_at` is past, or (c) LinkedIn API returned HTTP 401
- **Never** require the user to repeat their publish request after pasting the callback — do STEP A2 + STEP C in one turn
- **Never** post raw markdown — strip to plain text first
- **Never** exceed 3000 chars in `shareCommentary.text`
- **Never** hardcode `client_id` or `client_secret` in messages or logs
- **Never** ignore a pasted `{"code":...,"state":...}` message — always treat it as a STEP A2 trigger

