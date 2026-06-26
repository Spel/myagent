# User Approval Skill

Controls access to Ubraine. All new users require owner approval before the agent processes any of their messages.

## Overview

- **Approved list:** `/data/workspace/social/approved-users.json` — JSON array of approved Telegram user ID strings. Owner (264468965) is always present.
- **Pending list:** `/data/workspace/social/pending-users.json` — JSON array of `{id, name, requestedAt}` objects.

---

## Flow A: Unapproved User

Triggered by AGENTS.md access gate when `IS_APPROVED=false`.

### Step 1: Init files and check pending status

```bash
APPROVED=/data/workspace/social/approved-users.json
PENDING=/data/workspace/social/pending-users.json
mkdir -p /data/workspace/social
[ -f "$APPROVED" ] || echo '["264468965"]' > "$APPROVED"
[ -f "$PENDING" ] || echo '[]' > "$PENDING"
IS_PENDING=$(jq -r --arg uid "$TELEGRAM_USER_ID" 'map(select(.id == $uid)) | length > 0' "$PENDING")
echo "IS_PENDING=$IS_PENDING"
```

**If `IS_PENDING=true`:** Reply to user with exactly this message and stop:
> ⏳ Your access request is pending approval. I'll message you as soon as you're approved!

**If `IS_PENDING=false`:** continue to Step 2.

### Step 2: Add user to pending list

The agent must fill in `DISPLAY_NAME` from the current Telegram context (use first name + last name if available, or username, or "Unknown User").

```bash
PENDING=/data/workspace/social/pending-users.json
DISPLAY_NAME="<AGENT: fill from conversation context>"
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
jq --arg uid "$TELEGRAM_USER_ID" --arg name "$DISPLAY_NAME" --arg ts "$NOW" \
  '. += [{"id": $uid, "name": $name, "requestedAt": $ts}]' \
  "$PENDING" > /tmp/.pending_tmp && mv /tmp/.pending_tmp "$PENDING"
echo "ADDED_TO_PENDING=true"
```

### Step 3: Reply to the user

Send this exact static message to the user:
> 👋 Hi! I'm Ubraine 🧠 — a LinkedIn growth coach.
>
> Your access request has been submitted and the owner has been notified. I'll message you as soon as you're approved! 🚀

### Step 4: Notify owner via Telegram API

```bash
DISPLAY_NAME="<AGENT: same value as Step 2>"
PAYLOAD=$(jq -n \
  --arg uid "$TELEGRAM_USER_ID" \
  --arg name "$DISPLAY_NAME" \
  '{
    chat_id: "264468965",
    text: ("🔔 New Ubraine access request\n\nName: " + $name + "\nTelegram ID: " + $uid + "\n\nApprove to give them access."),
    reply_markup: {
      inline_keyboard: [[
        {"text": "✅ Approve", "callback_data": ("approve_user_" + $uid)},
        {"text": "❌ Deny",    "callback_data": ("deny_user_"    + $uid)}
      ]]
    }
  }')
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"
```

Done. Stop processing. Do not attempt to handle the original user request.

---

## Flow B: `approve_user_<ID>` callback

Owner pressed ✅ Approve. The callback value is `approve_user_<USER_ID>` — extract the user ID from it.

### Step 1: Get user name from pending before approving

```bash
TARGET_UID="<AGENT: extract from callback, strip 'approve_user_' prefix>"
APPROVED=/data/workspace/social/approved-users.json
PENDING=/data/workspace/social/pending-users.json
[ -f "$APPROVED" ] || echo '["264468965"]' > "$APPROVED"
[ -f "$PENDING" ] || echo '[]' > "$PENDING"
USER_NAME=$(jq -r --arg uid "$TARGET_UID" '.[] | select(.id == $uid) | .name' "$PENDING")
[ -z "$USER_NAME" ] && USER_NAME="User #$TARGET_UID"
echo "USER_NAME=$USER_NAME"
```

### Step 2: Approve and remove from pending

```bash
TARGET_UID="<AGENT: same as Step 1>"
APPROVED=/data/workspace/social/approved-users.json
PENDING=/data/workspace/social/pending-users.json
jq --arg uid "$TARGET_UID" '. += [$uid] | unique' "$APPROVED" > /tmp/.approved_tmp && mv /tmp/.approved_tmp "$APPROVED"
jq --arg uid "$TARGET_UID" 'map(select(.id != $uid))' "$PENDING" > /tmp/.pending_tmp && mv /tmp/.pending_tmp "$PENDING"
echo "APPROVED=true"
```

### Step 3: Reply to owner

> ✅ **[USER_NAME]** approved! They've been notified.

### Step 4: Notify the approved user

```bash
TARGET_UID="<AGENT: same>"
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\":\"$TARGET_UID\",\"text\":\"✅ You've been approved! Welcome to Ubraine 🧠\\n\\nI'm your LinkedIn growth coach. Send me anything to get started — let's build your LinkedIn presence! 🚀\"}"
```

---

## Flow C: `deny_user_<ID>` callback

Owner pressed ❌ Deny. Extract user ID from callback (`deny_user_<USER_ID>`).

### Step 1: Get name and remove from pending

```bash
TARGET_UID="<AGENT: extract from callback, strip 'deny_user_' prefix>"
PENDING=/data/workspace/social/pending-users.json
[ -f "$PENDING" ] || echo '[]' > "$PENDING"
USER_NAME=$(jq -r --arg uid "$TARGET_UID" '.[] | select(.id == $uid) | .name' "$PENDING")
[ -z "$USER_NAME" ] && USER_NAME="User #$TARGET_UID"
jq --arg uid "$TARGET_UID" 'map(select(.id != $uid))' "$PENDING" > /tmp/.pending_tmp && mv /tmp/.pending_tmp "$PENDING"
echo "USER_NAME=$USER_NAME DENIED=true"
```

### Step 2: Reply to owner

> ❌ **[USER_NAME]** denied.

### Step 3: Notify the denied user (optional, owner can skip)

```bash
TARGET_UID="<AGENT: same>"
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\":\"$TARGET_UID\",\"text\":\"Sorry, your access request wasn't approved at this time.\"}"
```
