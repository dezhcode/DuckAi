# DuckAI Telegram bot

This adapter uses the same `DuckAI.ask`, `image_to_data_url`, and `DuckAI.generate_image` functions as the CLI. The deployed Python client now includes the attachment, payload-size, response-cleanup, and retry fixes merged in PR #1.

## Commands

| Input | Behavior |
| --- | --- |
| A text message | Text chat with bounded recent context |
| Photo with a caption | Analyze the photo using the caption as the question |
| Photo without a caption | Describe the image in Persian |
| A text reply to a photo | Analyze the replied-to photo using the new question |
| An image sent as a document | Validate and convert the image, then analyze it |
| `/draw description` or `/image description` | Generate an image through DuckAI and upload a JPEG to Telegram |
| `/models` or `/model` | Select a text model with inline buttons |
| `/clear` or `/new` | Clear recent text context |

When the selected text model is not configured for vision (GPT OSS), photo analysis uses the default Luna model and tells the user. Image generation always uses that default model. Photos and generated files live only in a temporary directory and are deleted after the request; binary image data is not retained in conversation history.

## Vercel deployment

Deploy repository-root files; do not put the app inside an extra `src/` folder. Both `api/webhook.py` and `api/solve.js` must be present. Set `TELEGRAM_BOT_TOKEN` in Vercel's appropriate environment. Keep the existing Telegram webhook URL, `/api/webhook`, and its existing secret token; no webhook re-registration is required for this upgrade. This code preserves the previously configured secret derivation. Never commit the token or put it in a URL.

The Python function delegates the existing CLI challenge runner to the authenticated Node function at `https://duckai-telegram-bot.vercel.app/api/solve`. Both use the same shared runner from `jsa_jsdom.js`. Other project domains must update this fixed service URL in `RemoteDuckAI` before deployment. Keep the solver behind its existing server-to-server authentication; do not add a public setup, source-export, or AI-test endpoint.

`vercel.json` allows up to 300 seconds for the webhook, including image generation. The health endpoint lists the available application features and whether the token is configured; it does not prove that Duck.ai is responding successfully.

## Verification

```sh
python -m pip install -r requirements.txt
npm install
python -m unittest discover -s tests -v
npm test
```

The suite tests the full adapter path with synthetic image fixtures and mocked external services: caption/reply/document photos, WebP encoding, the repository's generated-image parser, JPEG multipart upload, text chat, model callbacks, oversized downloads, temporary-file cleanup, duplicate updates, UTF-16 text limits, and webhook authentication over local HTTP. It also tests the shared Node runner and solver authentication. It never sends Telegram messages.

After release, use the actual bot to confirm a captioned photo and `/draw a blue circle` both produce a response. Duck.ai uses an unofficial endpoint and may reject requests or change model/image support; display a safe user-facing error rather than raw provider exceptions.

Live client checks on 2026-11-15: vision correctly identified the red synthetic fixture; image generation produced a valid 1254×1254 JPEG. The first image-generation check received HTTP 418, and a subsequent check using the repository's two-attempt recovery succeeded. The adapter therefore allows two attempts for image generation. These checks contact Duck.ai directly; the final Telegram delivery still needs confirmation from an actual bot conversation.

Recent text context, model selection, per-user locks, and duplicate-update detection are bounded and local to a warm instance. They reset on cold starts and are not shared between instances. The adapter acknowledges the webhook after processing; Telegram retries can still duplicate work across separate instances. Durable conversation state and exactly-once delivery require external storage and are not claimed by this version.
