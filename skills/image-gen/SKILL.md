---
name: image-gen
description: Generate images from a text prompt via Vertex AI Imagen (LiteLLM gateway). Two modes — casual images delivered to Telegram, and LinkedIn-mode images saved to a file ready to attach to a post.
user-invocable: true
triggers:
  - "generate an image"
  - "create an image"
  - "draw me"
  - "make an image"
  - "make a picture"
  - "create a picture"
  - "generate a photo"
  - "image for my post"
  - "image for linkedin"
  - "create an infographic"
  - "make an infographic"
---

# Image Generation Skill

Generates images from a text prompt using Vertex AI Imagen 4.0 via the LiteLLM
gateway (synchronous curl). Always returns a real file on disk.

## Which mode?

| Situation | Mode |
|-----------|------|
| User just wants a picture sent to them in chat | **Casual mode** |
| Image is meant for a LinkedIn post | **LinkedIn mode** |
| User wants a data chart / stats comparison "infographic" | **Chart mode** (Imagen renders text poorly — use a chart) |

> Do NOT use the native `image_generate` tool for the LinkedIn pipeline. It is
> asynchronous and leaves no file you can attach to a post. Use the curl flow
> below — it returns a deterministic local path. (The native tool is fine only
> for a quick "send me a picture" with nothing to publish.)

## Step 1: Clarify or proceed

If the user gave a clear prompt, continue. If vague (e.g. "generate something
cool"), ask once:
> What would you like me to generate? Describe the scene, style, mood, or subject.

**Aspect ratio:** Imagen accepts `1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16,
16:9, 21:9` and a few others. For LinkedIn use `16:9`. `1.91:1` is INVALID.

## Step 2: Generate the image (curl → file)

Pick the output path based on mode:
- **Casual mode:** `OUT=/tmp/generated_image.png`
- **LinkedIn mode:** save under the user's images dir so `linkedin-publish` can
  attach it:
  ```bash
  mkdir -p "/data/workspace/social/linkedin/$TELEGRAM_USER_ID/images"
  OUT="/data/workspace/social/linkedin/$TELEGRAM_USER_ID/images/gen-$(date +%s).png"
  ```

Then generate:

```bash
PROMPT_JSON=$(printf '%s' "<AGENT: user's full prompt>" | jq -Rs '.')
RESPONSE=$(curl -s -X POST "${LITELLM_BASE_URL}/images/generations" \
  -H "Authorization: Bearer ${LITELLM_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"vertex_ai/imagen-4.0-fast-generate-001\", \"prompt\": $PROMPT_JSON, \"n\": 1}")

ERROR=$(printf '%s' "$RESPONSE" | jq -r '.error.message // empty')
if [ -n "$ERROR" ]; then
  echo "GENERATE_ERROR=$ERROR"
  exit 0
fi

IMG_B64=$(printf '%s' "$RESPONSE" | jq -r '.data[0].b64_json // empty')
IMG_URL=$(printf '%s' "$RESPONSE" | jq -r '.data[0].url // empty')

if [ -n "$IMG_B64" ]; then
  printf '%s' "$IMG_B64" | base64 -d > "$OUT"
  echo "IMAGE_READY=file PATH=$OUT"
elif [ -n "$IMG_URL" ]; then
  curl -sL "$IMG_URL" -o "$OUT"
  echo "IMAGE_READY=file PATH=$OUT"
else
  echo "IMAGE_READY=none"
fi
```

If `IMAGE_READY=none` or `GENERATE_ERROR` is set, tell the user it failed and
offer to retry with a clearer prompt. Do NOT proceed to post.

## Step 3 (Casual mode only): Send to Telegram

The native tool is not used here, so send the file yourself — exactly ONCE:

```bash
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendPhoto" \
  -F "chat_id=${TELEGRAM_USER_ID}" \
  -F "photo=@/tmp/generated_image.png" \
  -F "caption=🎨 Generated: <AGENT: short restatement of the prompt>"
```

Do NOT also send the same photo a second time. Then offer the follow-up buttons.

## Step 3 (LinkedIn mode): Hand off to linkedin-publish

The file is already saved at `$OUT`. Do NOT `sendPhoto` it separately. Pass the
path straight into the `linkedin-publish` Image post flow (source A):

```bash
{baseDir of linkedin-publish}/li-post.sh "$TELEGRAM_USER_ID" image "$OUT" "<POST_BODY>"
```

Follow `linkedin-publish` rules: confirm once, publish once. See its
**Single-publish guard**.

## Chart mode (data/stats "infographics")

Imagen cannot render crisp labels, numbers, or charts. For comparisons and
stats, build a chart with quickchart.io (Chart.js) and curl the PNG to a file —
do NOT use ImageMagick, PIL, the `canvas` tool, or the `browser` tool (none
work here).

```bash
mkdir -p "/data/workspace/social/linkedin/$TELEGRAM_USER_ID/images"
OUT="/data/workspace/social/linkedin/$TELEGRAM_USER_ID/images/chart-$(date +%s).png"
CHART='{"type":"bar","data":{"labels":["18 months researching","1 weekend shipping"],"datasets":[{"data":[18,0.25],"backgroundColor":["#888","#ff6b35"]}]},"options":{"plugins":{"legend":{"display":false},"title":{"display":true,"text":"Speed is the game"}}}}'
ENC=$(printf '%s' "$CHART" | jq -sRr @uri)
curl -sL "https://quickchart.io/chart?bkg=white&c=${ENC}" -o "$OUT"
echo "IMAGE_READY=file PATH=$OUT"
```

Then hand `$OUT` to LinkedIn mode's Step 3 (single publish).

## Follow-up buttons

After sending a casual image, reply WITH TEXT plus buttons (a buttons-only
message fails on Telegram):

```json
{
  "blocks": [
    {"type": "text", "text": "✅ Done! Want to tweak it?"},
    {"type": "buttons", "buttons": [
      {"label": "🔄 Regenerate", "action": {"type": "callback", "value": "imagegen_regenerate"}, "style": "secondary"},
      {"label": "✏️ Change prompt", "action": {"type": "callback", "value": "imagegen_change_prompt"}, "style": "secondary"},
      {"label": "📤 Post to LinkedIn", "action": {"type": "callback", "value": "imagegen_post_linkedin"}, "style": "primary"}
    ]}
  ]
}
```

- **`imagegen_regenerate`:** Re-run Step 2 with the same prompt.
- **`imagegen_change_prompt`:** Ask for a new prompt, re-run Step 2.
- **`imagegen_post_linkedin`:** Switch to LinkedIn mode — regenerate to the
  user's images dir (or reuse `$OUT` if already there), then run LinkedIn mode
  Step 3. Publish exactly once.

## Notes

- Model: `vertex_ai/imagen-4.0-fast-generate-001`
- Gateway: `${LITELLM_BASE_URL}/images/generations`, `Bearer ${LITELLM_API_KEY}`
- Casual files in `/tmp` are ephemeral per turn — send immediately.
- LinkedIn/chart files persist under
  `/data/workspace/social/linkedin/<uid>/images/` so they can be attached.
