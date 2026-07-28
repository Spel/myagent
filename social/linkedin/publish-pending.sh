#!/bin/bash
# Auto-publish pending LinkedIn posts for Catherine Miliutenko (UID: 547748231)
# Runs every 5 minutes, checks for posts due within next 5 minutes

TELEGRAM_USER_ID=547748231
PENDING_DIR="/data/workspace/social/linkedin/$TELEGRAM_USER_ID/pending"
SCRIPT="/data/workspace/skills/linkedin-publish/li-post.sh"

cd "$PENDING_DIR" || exit 0

NOW=$(date +%s)

for file in *.md; do
  [ -f "$file" ] || continue
  [ "$file" = ".gitkeep" ] && continue
  
  # Extract scheduled time from filename: YYYY-MM-DD-HHMM.md
  # Parse: 2026-07-28-0500 -> 2026-07-28 05:00
  BASENAME=$(echo "$file" | sed 's/\.md$//')
  DATE_PART=$(echo "$BASENAME" | cut -d'-' -f1-3)
  TIME_PART=$(echo "$BASENAME" | cut -d'-' -f4)
  HOUR=$(echo "$TIME_PART" | cut -c1-2)
  MIN=$(echo "$TIME_PART" | cut -c3-4)
  
  FILETIME=$(date -d "${DATE_PART} ${HOUR}:${MIN}:00" +%s 2>/dev/null) || continue
  
  # Check if within next 5 minutes (or past due but within last 24h)
  DIFF=$((FILETIME - NOW))
  if [ $DIFF -le 300 ] && [ $DIFF -gt -86400 ]; then
    POST_TEXT=$(cat "$file")
    export TELEGRAM_USER_ID
    $SCRIPT "$TELEGRAM_USER_ID" text "$POST_TEXT"
    
    # Move to published
    mkdir -p "$PENDING_DIR/../published"
    mv "$file" "$PENDING_DIR/../published/$(date +%Y-%m-%d)-$(basename "$file")"
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Published: $file" >> "$PENDING_DIR/../publish-log.txt"
  fi
done
