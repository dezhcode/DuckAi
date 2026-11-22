# Trump Telegram Agent — optional persistence

Default DuckAI model: `gpt-6-luna`.

## Vercel environment variables

- `TELEGRAM_BOT_TOKEN`: Telegram bot token (already required).
- `TELEGRAM_BOT_USERNAME`: bot username without @, for group mention filtering.
- `UPSTASH_REDIS_REST_URL`: optional Upstash Redis REST HTTPS URL.
- `UPSTASH_REDIS_REST_TOKEN`: optional matching REST token.

When both Upstash variables are set, conversation history, model choice and news topic survive serverless restarts for 7 days. Without them the bot works with temporary in-memory state. `/clear` deletes stored history; `/status` displays memory mode. The store keeps at most 12 short text turns per chat/user and does not store image bytes.

## Supported tools

Recent news RSS, Duck.ai native WebSearch event detection and provider-supplied source links, bounded calculator, Wikipedia encyclopedia lookup, text/code-file analysis, vision, image generation, chat export, group mention handling.

## Limitations

Not a complete Vortex clone: arbitrary page browsing, fully autonomous LLM-driven tool planning, voice transcription, task scheduling and admin panel are not yet available. Do not store credentials in chat. Public source content is untrusted.

## Native search

Duck.ai requests use `canUseTools=true`. The bot observes `WebSearch` tool events and attaches HTTPS source URLs only when explicitly supplied by the provider. The model decides whether to search; this is not a guarantee that every question uses live web search. No Brave or SearXNG credentials are needed. RSS and Wikipedia remain optional independent evidence tools.
