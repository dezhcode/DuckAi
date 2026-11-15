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

Version 2.3.2 follows the user's explicit retry preference: if the first attempt receives HTTP 418 / `ERR_CHALLENGE` at the chat stage, with no `Retry-After` and no response events yet, the bot silently makes one fresh-session attempt using the same provider and normal authentication flow. Each attempt performs only one core request and closes its client. Two failures stop; the user receives a generic failure message instead of technical validation details. Partial responses, HTTP 429, unknown 418 errors, and provider-declared waiting periods are not replayed by this adapter. The retry preserves the original prompt, images, model and history, and appends history only after success.

A warm bot instance permits only one upstream operation at a time. HTTP 429, unknown 418 errors and provider-declared waiting periods still receive backoff, honoring longer `Retry-After` values. Help, model selection and clearing conversation remain available, but clearing does not cancel an applicable pause. Explicit `ERR_CHALLENGE` without a declared wait has no invented countdown. This state is local to the instance; it is not a distributed provider quota and does not guarantee the provider will accept the second attempt.

Safe diagnostics record HTTP status, stage (`bootstrap`, `status`, `solver`, `chat`, `stream`), allowlisted provider error code, and `Retry-After`. Response bodies, prompts, cookies, proofs and bot credentials are not logged. An HTTP 418 means the request was rejected; it is not automatically labelled as a confirmed usage-limit event. Real provider quotas/rejections cannot be removed by this adapter.

The live local diagnostic check on 2026-11-15 reached the chat endpoint and received HTTP 418 with `ERR_CHALLENGE` on the first request after fetching a new proof. No further request was made after that rejection. This confirms an upstream challenge rejection for that check, not a demonstrated permanent repair of all 418 responses; the production environment needs the new stage/code diagnostics before its exact rejection can be attributed.

## Server-returned challenges (2.4.0)

The client now handles `x-vqd-hash-1` returned by the chat response, following the response-state lifecycle observed in [DuckAiChat](https://github.com/DarkBytee/DuckAiChat/blob/588b43b1853dc0e44de2b10756703e2db783bc86/app/api/duckchat/route.ts#L455). It validates/queues the encoded challenge without consuming or delaying the SSE body, and prepares its proof before the next request that needs it. Invalid/oversized replacement headers do not invalidate an otherwise successful streamed answer.

The Telegram bot keeps the user's fresh-session-per-message preference. Within its single bounded retry, if the server supplied a replacement challenge, the new HTTP session receives the matching Duck.ai cookies and frontend version from that same request. It uses the returned challenge instead of discarding it and starting an unrelated bootstrap/status exchange. There is no shared cross-user cookie/proof cache, and both attempt clients still close reliably. If no replacement challenge exists, the existing one-shot fresh handshake remains the fallback. Quota errors, Retry-After and partial-output protections remain in force.

All model requests remain on Duck.ai. Gemini integration, SDK, alternate provider endpoint and fallback are absent. Even setting `GEMINI_API_KEY` does not enable another provider. The optional Gemini/proxy paths from the comparison repository are not part of this port. This protocol update does not guarantee that Duck.ai will accept every request.

## Serious simulated Trump persona and recent news (2.5.0)

Every text/vision request receives Persian style instructions for a serious, direct, natural Trump-inspired character. The first successful reply and `/start` identify this as a simulation, and explicit identity questions are answered honestly without a model request. The service never claims to be Trump's real account or representative. The disclosure is not repeated in every turn. Sessions remain in-memory and can reset on cold starts. There is no Gemini or alternative model provider.

Duck.ai's transport accepts the persona as a leading user/assistant instruction pair. The original user prompt and image payload stay intact; only original user turns and displayed answers enter the bounded conversation history. All existing challenge, Retry-After and retry limits remain unchanged.

Current-news questions and short news follow-ups trigger a separate publisher-feed reader: [BBC Persian](https://feeds.bbci.co.uk/persian/rss.xml), [BBC World](https://feeds.bbci.co.uk/news/world/rss.xml), and the [White House news feed](https://www.whitehouse.gov/news/feed/). This is relevance matching over these publishers' recent feeds, not a general web search or comprehensive news archive. It does not open arbitrary URLs sent by users. No additional API key is required. RSS results are cached for 120 seconds, limited to the previous 72 hours, and a question containing “today” restricts publication dates to the current Tehran date. Publication time does not establish the time of an event. English/Persian geographic keywords have a small translation map; some phrasing and topics will have no matching coverage.

Up to three matching reports are selected, preferring different publisher groups. The two BBC feeds count as one publisher group. A White House statement is labelled an official claim, not independent verification. Article text is fetched where accessible; otherwise the context explicitly says only the RSS headline/summary was read. HTTPS host allowlists apply to feeds, article URLs and every redirect; response sizes and request timeouts are bounded. No authentication or access restrictions on publishers are bypassed.

The model receives the retrieval time, publisher, publication date, headline, summary and available article excerpts as untrusted source data. Instructions require attribution, qualified language for disputed/sensitive claims, no invented event dates, and no first-person claims of real military actions. The application appends the actual source URLs and Tehran publication times. Recognizable invented first-person attack claims and source URLs outside the retrieved set trigger an attributed-headline fallback. These checks are additional safeguards, not a guarantee that a generative model is always accurate; the linked sources remain available for verification. When there are no relevant current sources, ordinary news requests return an honest no-confirmation response without asking the model to invent live news. Attached photos can still be analysed, with no assertion of verified news. Generated images are not evidence of real news events.

Validation: Python regression coverage exercises disclosure, identity, policy/history handling, photo and image generation preservation, feed age/host checks, redirect blocking, article extraction and summary-only labelling, publisher grouping, source append, unsupported-claim fallback, no-news behaviour and one retrieval across the existing bounded Duck.ai retry. Node tests continue to cover solver authentication. Deployment health reports version 2.5.0 and the new persona/news features; it does not prove upstream Duck.ai accepts every request.
