# Image Generation Skill

Generates images from a text prompt using Vertex AI Imagen 4.0 via the LiteLLM gateway.

## CRITICAL — Do NOT use the built-in image generation tool

OpenClaw's native image generation plugin is not configured for this deployment. **Always use exec bash with curl** to call the images API directly. Never use the native image tool — it will fail.

## Trigger

User asks to generate, create, draw, or make an image. Any variation — "generate an image of...", "draw me...", "create a picture of...", "make an image showing...".

## Flow

### Step 1: Clarify or proceed

If the user gave a clear prompt, skip to Step 2.

If the prompt is vague (e.g. "generate something cool"), ask once:
> What would you like me to generate? Describe the scene, style, mood, or subject.

### Step 2: Generate the image via curl

The response may contain a large base64 payload — never store it in a variable or echo it. Write directly to file and only report status back.

```bash
PROMPT_JSON=$(printf '%s' "<AGENT: user's full prompt>" | jq -Rs '.')
IMG_FILE=/data/workspace/media/generated/$(date +%s).png
mkdir -p /data/workspace/media/generated

# Stream response to a temp JSON file — never into a variable
curl -s -X POST "${LITELLM_BASE_URL}/images/generations" \
  -H "Authorization: Bearer ${LITELLM_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"vertex_ai/imagen-4.0-fast-generate-001\", \"prompt\": $PROMPT_JSON, \"n\": 1}" \
  -o /tmp/imggen_response.json

ERROR=$(jq -r '.error.message // empty' /tmp/imggen_response.json)
if [ -n "$ERROR" ]; then
  rm -f /tmp/imggen_response.json
  echo "GENERATE_ERROR=$ERROR"
  exit 0
fi

IMG_URL=$(jq -r '.data[0].url // empty' /tmp/imggen_response.json)
if [ -n "$IMG_URL" ]; then
  rm -f /tmp/imggen_response.json
  echo "IMAGE_READY=url"
  echo "IMAGE_URL=$IMG_URL"
else
  # Decode base64 directly from jq into file — no variable holding the data
  jq -r '.data[0].b64_json' /tmp/imggen_response.json | base64 -d > "$IMG_FILE"
  rm -f /tmp/imggen_response.json
  echo "IMAGE_READY=file"
  echo "IMAGE_FILE=$IMG_FILE"
fi
```

### Step 3: Send the image to the user

**If `IMAGE_READY=file`:**
```bash
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendPhoto" \
  -F "chat_id=${TELEGRAM_USER_ID}" \
  -F "photo=@${IMAGE_FILE}" \
  -F "caption=🎨 Generated!"
rm -f "$IMAGE_FILE"
```

**If `IMAGE_READY=url`:**
```bash
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendPhoto" \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\": \"${TELEGRAM_USER_ID}\", \"photo\": \"$IMAGE_URL\", \"caption\": \"🎨 Generated!\"}"
```

**If `GENERATE_ERROR` is set:**
> ❌ Image generation failed: [error]. Try rephrasing your prompt — be more specific about the subject, style, or mood.

### Step 4: Follow-up buttons

After successfully sending the image, reply with:
> ✅ Done! Want to tweak it?

With presentation buttons:
```json
{
  "blocks": [{
    "type": "buttons",
    "buttons": [
      {"label": "🔄 Regenerate", "action": {"type": "callback", "value": "imagegen_regenerate"}, "style": "secondary"},
      {"label": "✏️ Change prompt", "action": {"type": "callback", "value": "imagegen_change_prompt"}, "style": "secondary"},
      {"label": "📤 Post to LinkedIn", "action": {"type": "callback", "value": "imagegen_post_linkedin"}, "style": "primary"}
    ]
  }]
}
```

**`imagegen_regenerate`:** Re-run Step 2 with the same prompt.
**`imagegen_change_prompt`:** Ask for a new prompt, re-run Step 2.
**`imagegen_post_linkedin`:** Pass the generated image to the `linkedin-publish` skill's image upload flow.


Generates images from a text prompt using Vertex AI Imagen 4.0 via the LiteLLM gateway.

## Trigger

User asks to generate, create, draw, or make an image. Any variation — "generate an image of...", "draw me...", "create a picture of...", "make an image showing...".

## Flow

### Step 1: Clarify or proceed

If the user gave a clear prompt, skip to Step 2.

If the prompt is vague (e.g. "generate something cool"), ask once:
> What would you like me to generate? Describe the scene, style, mood, or subject.

### Step 2: Generate the image

Replace `<PROMPT>` with the user's full prompt (properly escaped for JSON).

```bash
PROMPT_JSON=$(printf '%s' "<AGENT: user's full prompt>" | jq -Rs '.')
RESPONSE=$(curl -s -X POST "${LITELLM_BASE_URL}/images/generations" \
  -H "Authorization: Bearer ${LITELLM_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"vertex_ai/imagen-4.0-fast-generate-001\", \"prompt\": $PROMPT_JSON, \"n\": 1}")

ERROR=$(printf '%s' "$RESPONSE" | jq -r '.error.message // empty')
[ -n "$ERROR" ] && echo "GENERATE_ERROR=$ERROR" && exit 0

IMG_B64=$(printf '%s' "$RESPONSE" | jq -r '.data[0].b64_json // empty')
IMG_URL=$(printf '%s' "$RESPONSE" | jq -r '.data[0].url // empty')

if [ -n "$IMG_B64" ]; then
  printf '%s' "$IMG_B64" | base64 -d > /tmp/generated_image.png
  echo "IMAGE_READY=file"
elif [ -n "$IMG_URL" ]; then
  echo "IMAGE_READY=url"
  echo "IMAGE_URL=$IMG_URL"
else
  echo "IMAGE_READY=none"
fi
```

### Step 3: Send the image to the user

**If `IMAGE_READY=file`** — send the file directly via Telegram:

```bash
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendPhoto" \
  -F "chat_id=${TELEGRAM_USER_ID}" \
  -F "photo=@/tmp/generated_image.png" \
  -F "caption=🎨 Generated: <AGENT: short restatement of the prompt>"
```

**If `IMAGE_READY=url`** — send the URL via Telegram:

```bash
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendPhoto" \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\": \"${TELEGRAM_USER_ID}\", \"photo\": \"$IMAGE_URL\", \"caption\": \"🎨 Generated: <AGENT: short restatement of the prompt>\"}"
```

**If `IMAGE_READY=none` or `GENERATE_ERROR` is set** — reply to user:
> ❌ Image generation failed: [error message]. Try rephrasing your prompt and I'll try again.

### Step 4: Follow-up buttons

After successfully sending the image, reply with:

> ✅ Done! Want to tweak it?

With presentation buttons:
```json
{
  "blocks": [{
    "type": "buttons",
    "buttons": [
      {"label": "🔄 Regenerate", "action": {"type": "callback", "value": "imagegen_regenerate"}, "style": "secondary"},
      {"label": "✏️ Change prompt", "action": {"type": "callback", "value": "imagegen_change_prompt"}, "style": "secondary"}
    ]
  }]
}
```

**`imagegen_regenerate` callback:** Re-run Step 2 with the same prompt (no Step 1).

**`imagegen_change_prompt` callback:** Ask the user for a new prompt, then re-run from Step 2.

## Notes

- Model: `vertex_ai/imagen-4.0-fast-generate-001`
- Gateway: `${LITELLM_BASE_URL}/images/generations` with `Bearer ${LITELLM_API_KEY}`
- The model returns base64 (`b64_json`) or a URL (`url`) — handle both
- `/tmp/generated_image.png` is ephemeral per container turn — generate and send immediately
- For LinkedIn use: after image is generated, offer "📤 Post this to LinkedIn" button if the user has a linked account
