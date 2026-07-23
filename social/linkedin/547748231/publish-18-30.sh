#!/bin/bash
export TELEGRAM_USER_ID="547748231"
DRAFT="/data/workspace/social/linkedin/547748231/pending/2026-07-23-1830.md"
POST_BODY=$(cat "$DRAFT")
/data/workspace/skills/linkedin-publish/li-post.sh "$TELEGRAM_USER_ID" text "$POST_BODY"
