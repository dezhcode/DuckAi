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
| `یک ماشین پرنده طراحی کن` or `Draw a flying car` | Generate and send an image directly from normal chat; no command is needed |
| `/draw description` or `/image description` | Generate an image through DuckAI and upload a JPEG to Telegram |
| `/models` or `/model` | Select a text model with inline buttons |
| `/clear` or `/new` | Clear recent text context |

When the selected text model is not configured for vision (GPT OSS), photo analysis uses the default Luna model and tells the user. Image generation always uses that default model. Photos and generated files live only in a temporary directory and are deleted after the request; binary image data is not retained in conversation history.

Ordinary chat consumes all repository `stream_events` results, including provider-selected image-generation tools and completed images. It does not use the text-only `ask()` wrapper, which drops image events. Clear creation requests in Persian and English take a direct generation path; explanations, negations and code questions stay in ordinary chat, where the provider can still choose tools. Captioned/replied-to photos use the vision path without requiring a slash command. `/draw` remains an optional shortcut.

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

## Connection lifecycle and provider rejections

Version 2.3 follows the user's explicit preference: every accepted AI request creates a fresh DuckAI client and HTTP session. The core stream initializes a new challenge, and the client is closed in a finally block after success or failure. Provider clients, cookies and proofs are not cached in conversation state. Bounded text history remains the bot's conversation context; connection state is new on every request. Requests rejected locally by the existing busy/cooldown checks do not open provider sessions. This replaces version 2.2's connection-reuse policy and does not claim to remove provider-side challenge rejection.

The client does not replay generic HTTP 418 or usage-limit HTTP 429 responses. There is one bounded protocol-recovery case inherited from the CLI: if a reused conversation proof receives explicit `ERR_CHALLENGE`, with no `Retry-After`, it may fetch a fresh challenge once. A fresh proof rejected on the first request is not replayed. A warm bot instance permits only one upstream operation at a time and pauses upstream calls for at least 30 seconds after a rejection, honoring a longer `Retry-After` value when provided. Help, model selection and clearing conversation remain available, but clearing does not cancel the pause. This state is local to the instance; it is not a distributed provider quota.

Safe diagnostics record HTTP status, stage (`bootstrap`, `status`, `solver`, `chat`, `stream`), allowlisted provider error code, and `Retry-After`. Response bodies, prompts, cookies, proofs and bot credentials are not logged. An HTTP 418 means the request was rejected; it is not automatically labelled as a confirmed usage-limit event. Real provider quotas/rejections cannot be removed by this adapter.

The live local diagnostic check on 2026-11-15 reached the chat endpoint and received HTTP 418 with `ERR_CHALLENGE` on the first request after fetching a new proof. No further request was made after that rejection. This confirms an upstream challenge rejection for that check, not a demonstrated permanent repair of all 418 responses; the production environment needs the new stage/code diagnostics before its exact rejection can be attributed.
