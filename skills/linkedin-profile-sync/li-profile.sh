#!/bin/bash
# LinkedIn profile sync helper — reads the user's live LinkedIn profile via API
# Usage: li-profile.sh <telegram_user_id>
# Output on success:
#   DISPLAY_NAME: <name>
#   HEADLINE: <headline>
#   ABOUT: <about text>
#   FOLLOWERS: <count>
#   PROFILE_URL: https://www.linkedin.com/in/<vanityName>
# Output on error:
#   NO_TOKEN
#   TOKEN_EXPIRED
#   ERROR <code>: <body>

set -e

TELEGRAM_USER_ID="$1"
TOKEN_STORE="${LINKEDIN_TOKEN_STORE:-/data/openclaw/linkedin-tokens.json}"

[ -f "$TOKEN_STORE" ] || { echo "NO_TOKEN"; exit 2; }

ACCESS_TOKEN=$(jq -r --arg u "$TELEGRAM_USER_ID" '.[$u].access_token // empty' "$TOKEN_STORE")
EXPIRES_AT=$(jq -r --arg u "$TELEGRAM_USER_ID" '.[$u].expires_at // 0' "$TOKEN_STORE")
NOW=$(date +%s)

if [ -z "$ACCESS_TOKEN" ]; then
  echo "NO_TOKEN"
  exit 2
fi

if [ "$EXPIRES_AT" -lt "$((NOW + 3600))" ]; then
  echo "TOKEN_EXPIRED"
  exit 3
fi

# ── fetch userinfo (openid scope — always available) ─────────────────────────
USERINFO=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://api.linkedin.com/v2/userinfo")

DISPLAY_NAME=$(echo "$USERINFO" | jq -r '.name // empty')
PROFILE_PIC=$(echo "$USERINFO" | jq -r '.picture // empty')

if [ -z "$DISPLAY_NAME" ]; then
  echo "ERROR fetch: $USERINFO"
  exit 1
fi

echo "DISPLAY_NAME: $DISPLAY_NAME"
echo "PROFILE_PIC: $PROFILE_PIC"

# ── fetch full profile (headline, about, vanityName) ─────────────────────────
PROFILE=$(curl -s \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  "https://api.linkedin.com/v2/me?projection=(id,localizedFirstName,localizedLastName,localizedHeadline,localizedSummary,vanityName,profilePicture(displayImage~:playableStreams))")

HEADLINE=$(echo "$PROFILE" | jq -r '.localizedHeadline // "(not set)"')
ABOUT=$(echo "$PROFILE" | jq -r '.localizedSummary // "(not set)"')
VANITY=$(echo "$PROFILE" | jq -r '.vanityName // empty')

echo "HEADLINE: $HEADLINE"
echo "ABOUT: $ABOUT"
[ -n "$VANITY" ] && echo "PROFILE_URL: https://www.linkedin.com/in/$VANITY"

# ── fetch follower count ──────────────────────────────────────────────────────
# Uses networkSizes endpoint — available with r_member_social scope
# Falls back gracefully if scope not granted
NETWORK=$(curl -s \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  "https://api.linkedin.com/v2/networkSizes/urn:li:person:$(echo "$PROFILE" | jq -r '.id')?edgeType=CompanyFollowedByMember" 2>/dev/null)

FOLLOWERS=$(echo "$NETWORK" | jq -r '.firstDegreeSize // empty' 2>/dev/null)
[ -n "$FOLLOWERS" ] && echo "FOLLOWERS: $FOLLOWERS" || echo "FOLLOWERS: (scope r_member_social not granted)"
