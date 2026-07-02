---
name: webhooks/chatwoot
version: 1.0.0
description: |
  Handles incoming Chatwoot webhook events (conversation_created, message_created).
  Parses the payload, generates an AI response, and sends it back to the
  customer via the Chatwoot Create Message API.
triggers:
  - "chatwoot webhook"
  - "chatwoot message received"
  - "handle chatwoot event"
tools:
  - http_request
  - search
  - put_page
mutating: true
---

# Chatwoot Webhook Controller

## Purpose

Handle POST events from Chatwoot and reply to the customer using the Chatwoot API.

## Contract

- Parse and validate the Chatwoot payload.
- Only act on `message_created` events where `message_type` is `incoming` (ignore
  outgoing/bot messages to prevent loops).
- Generate a contextual reply using the agent's knowledge base.
- Send the reply back via `POST /api/v1/accounts/{account_id}/conversations/{id}/messages`.
- Log the event to the brain for context retention.

## Payload Shape (Chatwoot `message_created`)

```json
{
  "event": "message_created",
  "id": 123,
  "content": "Hello, I need help with my account",
  "message_type": "incoming",
  "conversation": {
    "id": 456,
    "meta": {
      "sender": { "name": "John Doe", "email": "john@example.com" }
    }
  },
  "account": { "id": 1 }
}
```

## Processing Steps

### 1. Guard Clause — Ignore Non-Incoming Messages

```
if payload.event != "message_created" → skip
if payload.message_type != "incoming"  → skip  (avoids echo loops)
```

### 2. Extract Key Fields

```
conversation_id = payload.conversation.id
account_id      = payload.account.id  (or env CHATWOOT_ACCOUNT_ID)
user_message    = payload.content
sender_name     = payload.conversation.meta.sender.name
```

### 3. Build Context & Generate Reply

Search the brain for relevant context matching `user_message`, then compose a reply.
Keep replies concise (≤ 3 sentences) unless the question requires detail.

### 4. Send Reply via Chatwoot API

```
POST {CHATWOOT_BASE_URL}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages
Headers:
  api_access_token: {CHATWOOT_API_TOKEN}
  Content-Type: application/json
Body:
  {
    "content": "<generated reply>",
    "message_type": "outgoing",
    "private": false
  }
```

### 5. Log to Brain

Write a brief brain entry: sender, their message, and the reply sent.
Slug: `chatwoot/{conversation_id}/{timestamp}`

## Error Handling

- If the Chatwoot API returns non-2xx: log error, do **not** retry (prevents duplicate
  messages). Surface error to agent timeline.
- If reply generation fails: send a fallback message —
  "Thanks for reaching out! A team member will follow up shortly."

## Security Notes

- The OpenClaw gateway verifies the `X-Chatwoot-Signature-256` HMAC header using
  `OPENCLAW_WEBHOOK_SECRET` before this controller is invoked. No additional
  signature check is needed here.
- Never echo raw user input back without sanitisation.
