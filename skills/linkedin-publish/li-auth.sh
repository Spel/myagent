#!/bin/bash
# LinkedIn OAuth helper — called by the linkedin-publish skill
# Usage:
#   li-auth.sh exchange <telegram_user_id> <auth_code>   — exchange auth code for token
#   li-auth.sh refresh  <telegram_user_id>               — refresh an expired token

set -euo pipefail

MODE="$1"
TELEGRAM_USER_ID="$2"
TOKEN_STORE="${LINKEDIN_TOKEN_STORE:-/data/openclaw/linkedin-tokens.json}"

[ -f "$TOKEN_STORE" ] || echo '{}' > "$TOKEN_STORE"

# ── exchange ───────────────────────────────────────────────────────────────────
if [ "$MODE" = "exchange" ]; then
  CODE="$3"

  RESP=$(curl -s -X POST "https://www.linkedin.com/oauth/v2/accessToken" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=authorization_code" \
    --data-urlencode "code=$CODE" \
    --data-urlencode "redirect_uri=$LINKEDIN_REDIRECT_URI" \
    --data-urlencode "client_id=$LINKEDIN_CLIENT_ID" \
    --data-urlencode "client_secret=$LINKEDIN_CLIENT_SECRET")

  ACCESS_TOKEN=$(echo "$RESP" | jq -r '.access_token // empty')
  REFRESH_TOKEN=$(echo "$RESP" | jq -r '.refresh_token // empty')
  EXPIRES_IN=$(echo "$RESP" | jq -r '.expires_in // 0')

  if [ -z "$ACCESS_TOKEN" ]; then
    ERR=$(echo "$RESP" | jq -r '.error_description // .error // "unknown error"')
    echo "ERROR: $ERR"
    exit 1
  fi

  NOW=$(date +%s)
  EXPIRES_AT=$(expr "$NOW" + "$EXPIRES_IN")

  PROFILE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "https://api.linkedin.com/v2/userinfo")
  LINKEDIN_URN="urn:li:person:$(echo "$PROFILE" | jq -r '.sub')"
  DISPLAY_NAME=$(echo "$PROFILE" | jq -r '.name')

  jq --arg u "$TELEGRAM_USER_ID" \
     --arg t "$ACCESS_TOKEN" \
     --arg r "$REFRESH_TOKEN" \
     --argjson e "$EXPIRES_AT" \
     --arg urn "$LINKEDIN_URN" \
     --arg n "$DISPLAY_NAME" \
     --arg l "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
     '.[$u]={"access_token":$t,"refresh_token":$r,"expires_at":$e,"linkedin_urn":$urn,"display_name":$n,"linked_at":$l}' \
     "$TOKEN_STORE" > /tmp/.li_auth_tmp && mv /tmp/.li_auth_tmp "$TOKEN_STORE"

  echo "LINKED: $DISPLAY_NAME"

# ── refresh ────────────────────────────────────────────────────────────────────
elif [ "$MODE" = "refresh" ]; then
  REFRESH_TOKEN=$(jq -r --arg u "$TELEGRAM_USER_ID" '.[$u].refresh_token // empty' "$TOKEN_STORE")

  if [ -z "$REFRESH_TOKEN" ]; then
    echo "REFRESH_FAILED: no refresh token stored"
    exit 1
  fi

  RESP=$(curl -s -X POST "https://www.linkedin.com/oauth/v2/accessToken" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=refresh_token" \
    --data-urlencode "refresh_token=$REFRESH_TOKEN" \
    --data-urlencode "client_id=$LINKEDIN_CLIENT_ID" \
    --data-urlencode "client_secret=$LINKEDIN_CLIENT_SECRET")

  NEW_TOKEN=$(echo "$RESP" | jq -r '.access_token // empty')
  EXPIRES_IN=$(echo "$RESP" | jq -r '.expires_in // 0')
  NEW_REFRESH=$(echo "$RESP" | jq -r '.refresh_token // empty')

  if [ -z "$NEW_TOKEN" ]; then
    echo "REFRESH_FAILED: $(echo "$RESP" | jq -r '.error_description // .error // "unknown"')"
    exit 1
  fi

  NOW=$(date +%s)
  NEW_EXPIRES=$(expr "$NOW" + "$EXPIRES_IN")
  FINAL_REFRESH="${NEW_REFRESH:-$REFRESH_TOKEN}"

  jq --arg u "$TELEGRAM_USER_ID" \
     --arg t "$NEW_TOKEN" \
     --argjson e "$NEW_EXPIRES" \
     --arg r "$FINAL_REFRESH" \
     '.[$u] |= . + {"access_token":$t,"expires_at":$e,"refresh_token":$r}' \
     "$TOKEN_STORE" > /tmp/.li_auth_tmp && mv /tmp/.li_auth_tmp "$TOKEN_STORE"

  echo "REFRESHED"

else
  echo "Usage: li-auth.sh exchange <telegram_user_id> <code>"
  echo "       li-auth.sh refresh  <telegram_user_id>"
  exit 1
fi
