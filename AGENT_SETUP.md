# Trump Telegram Agent — optional persistence

Default DuckAI model: `gpt-6-luna`.

## Vercel environment variables

- `TELEGRAM_BOT_TOKEN`: Telegram bot token (already required).
- `TELEGRAM_BOT_USERNAME`: bot username without @, for group mention filtering.
- `UPSTASH_REDIS_REST_URL`: optional Upstash Redis REST HTTPS URL.
- `UPSTASH_REDIS_REST_TOKEN`: optional matching REST token.
- `SEARXNG_URL`: optional trusted HTTPS SearXNG instance URL with JSON search enabled (e.g. your own deployment). No API key required. Avoid untrusted public instances.

When both Upstash variables are set, conversation history, model choice and news topic survive serverless restarts for 7 days. Without them the bot works with temporary in-memory state. `/clear` deletes stored history; `/status` displays memory mode. The store keeps at most 12 short text turns per chat/user and does not store image bytes.

## Supported tools

Recent news RSS, optional bounded two-step SearXNG web search (triggered by explicit search requests), bounded calculator, Wikipedia encyclopedia lookup, text/code-file analysis, vision, image generation, chat export, group mention handling.

## Limitations

Not a complete Vortex clone: arbitrary page browsing, fully autonomous LLM-driven tool planning, voice transcription, task scheduling and admin panel are not yet available. Do not store credentials in chat. Public source content is untrusted.

## Keyless search

Set `SEARXNG_URL` in Vercel to the HTTPS origin of a SearXNG instance that supports `format=json`, then redeploy. Without it, Wikipedia and news RSS still work. Vercel does not host SearXNG automatically; a separate reachable instance is required. Do not use an arbitrary untrusted public instance for private searches.
