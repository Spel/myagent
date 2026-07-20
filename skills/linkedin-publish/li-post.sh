#!/bin/bash
# LinkedIn post helper — called by the linkedin-publish skill
# Usage:
#   Text post:   li-post.sh <telegram_user_id> text "<post body>"
#   Image post:  li-post.sh <telegram_user_id> image "<image_path>" "<post body>"
set -e

# Accept UID from arg OR from env var (env takes precedence so export works as fallback)
TELEGRAM_USER_ID="${1:-$TELEGRAM_USER_ID}"
if [ -z "$TELEGRAM_USER_ID" ]; then
  echo "NO_TOKEN: TELEGRAM_USER_ID is required (pass as arg 1 or export it)"
  exit 2
fi
MODE="$2"            # "text" or "image"
TOKEN_STORE="${LINKEDIN_TOKEN_STORE:-/data/openclaw/linkedin-tokens.json}"

[ -f "$TOKEN_STORE" ] || { echo '{}' > "$TOKEN_STORE"; }

# ── read token ────────────────────────────────────────────────────────────────
ACCESS_TOKEN=$(jq -r --arg u "$TELEGRAM_USER_ID" '.[$u].access_token // empty' "$TOKEN_STORE")
EXPIRES_AT=$(jq -r --arg u "$TELEGRAM_USER_ID" '.[$u].expires_at // 0' "$TOKEN_STORE")
LINKEDIN_URN=$(jq -r --arg u "$TELEGRAM_USER_ID" '.[$u].linkedin_urn // empty' "$TOKEN_STORE")
DISPLAY_NAME=$(jq -r --arg u "$TELEGRAM_USER_ID" '.[$u].display_name // empty' "$TOKEN_STORE")
NOW=$(date +%s)

if [ -z "$ACCESS_TOKEN" ]; then
  echo "NO_TOKEN: No LinkedIn account linked for Telegram user $TELEGRAM_USER_ID"
  exit 2
fi

if [ "$EXPIRES_AT" -lt "$((NOW + 3600))" ]; then
  echo "TOKEN_EXPIRED: Token expires at $EXPIRES_AT (now $NOW). Refresh or re-auth needed."
  exit 3
fi

# ── text post ─────────────────────────────────────────────────────────────────
if [ "$MODE" = "text" ]; then
  POST_BODY="$3"

  RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "https://api.linkedin.com/v2/ugcPosts" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -H "X-Restli-Protocol-Version: 2.0.0" \
    -d "{
      \"author\": \"$LINKEDIN_URN\",
      \"lifecycleState\": \"PUBLISHED\",
      \"specificContent\": {
        \"com.linkedin.ugc.ShareContent\": {
          \"shareCommentary\": {\"text\": $(echo "$POST_BODY" | jq -Rs .)},
          \"shareMediaCategory\": \"NONE\"
        }
      },
      \"visibility\": {\"com.linkedin.ugc.MemberNetworkVisibility\": \"PUBLIC\"}
    }")

  HTTP_CODE=$(echo "$RESPONSE" | tail -1)
  BODY=$(echo "$RESPONSE" | head -1)
  POST_URN=$(echo "$BODY" | jq -r '.id // empty')

  if [ "$HTTP_CODE" = "201" ]; then
    echo "OK: https://www.linkedin.com/feed/update/$POST_URN/"
    echo "DISPLAY_NAME: $DISPLAY_NAME"
    echo "CHARS: ${#POST_BODY}"
  else
    echo "ERROR $HTTP_CODE: $BODY"
    exit 1
  fi

# ── image post ────────────────────────────────────────────────────────────────
elif [ "$MODE" = "image" ]; then
  IMAGE_PATH="$3"
  POST_BODY="$4"

  if [ ! -f "$IMAGE_PATH" ]; then
    echo "ERROR: Image file not found: $IMAGE_PATH"
    exit 1
  fi

  # D1 — register upload
  REGISTER=$(curl -s -X POST \
    "https://api.linkedin.com/v2/assets?action=registerUpload" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -H "X-Restli-Protocol-Version: 2.0.0" \
    -d "{\"registerUploadRequest\":{\"recipes\":[\"urn:li:digitalmediaRecipe:feedshare-image\"],\"owner\":\"$LINKEDIN_URN\",\"serviceRelationships\":[{\"relationshipType\":\"OWNER\",\"identifier\":\"urn:li:userGeneratedContent\"}]}}")

  UPLOAD_URL=$(echo "$REGISTER" | jq -r '.value.uploadMechanism["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"].uploadUrl')
  ASSET_URN=$(echo "$REGISTER" | jq -r '.value.asset')

  if [ -z "$UPLOAD_URL" ] || [ "$UPLOAD_URL" = "null" ]; then
    echo "REGISTER_ERROR: $REGISTER"
    exit 1
  fi

  # D2 — upload binary
  UPLOAD_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$UPLOAD_URL" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/octet-stream" \
    -H "media-type-family: STILLIMAGE" \
    --upload-file "$IMAGE_PATH")

  if [ "$UPLOAD_CODE" != "201" ]; then
    echo "UPLOAD_ERROR: HTTP $UPLOAD_CODE"
    exit 1
  fi

  # D3 — create post
  RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "https://api.linkedin.com/v2/ugcPosts" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -H "X-Restli-Protocol-Version: 2.0.0" \
    -d "{
      \"author\": \"$LINKEDIN_URN\",
      \"lifecycleState\": \"PUBLISHED\",
      \"specificContent\": {
        \"com.linkedin.ugc.ShareContent\": {
          \"shareCommentary\": {\"text\": $(echo "$POST_BODY" | jq -Rs .)},
          \"shareMediaCategory\": \"IMAGE\",
          \"media\": [{\"status\": \"READY\", \"media\": \"$ASSET_URN\"}]
        }
      },
      \"visibility\": {\"com.linkedin.ugc.MemberNetworkVisibility\": \"PUBLIC\"}
    }")

  HTTP_CODE=$(echo "$RESPONSE" | tail -1)
  BODY=$(echo "$RESPONSE" | head -1)
  POST_URN=$(echo "$BODY" | jq -r '.id // empty')

  if [ "$HTTP_CODE" = "201" ]; then
    echo "OK: https://www.linkedin.com/feed/update/$POST_URN/"
    echo "DISPLAY_NAME: $DISPLAY_NAME"
    echo "CHARS: ${#POST_BODY}"
  else
    echo "ERROR $HTTP_CODE: $BODY"
    exit 1
  fi

else
  echo "Usage: li-post.sh <telegram_user_id> text|image [image_path] <post_body>"
  exit 1
fi
