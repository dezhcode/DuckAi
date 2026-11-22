# Trump Telegram Agent — optional persistence

Default DuckAI model: `gpt-6-luna`.

## Vercel environment variables

- `TELEGRAM_BOT_TOKEN`: Telegram bot token (already required).
- `TELEGRAM_BOT_USERNAME`: bot username without @, for group mention filtering.
- `UPSTASH_REDIS_REST_URL`: optional Upstash Redis REST HTTPS URL.
- `UPSTASH_REDIS_REST_TOKEN`: optional matching REST token.

When both Upstash variables are set, conversation history, model choice and news topic survive serverless restarts for 7 days. Without them the bot works with temporary in-memory state. `/clear` deletes stored history; `/status` displays memory mode. The store keeps at most 12 short text turns per chat/user and does not store image bytes.

## Supported tools

Recent news RSS, bounded calculator, Wikipedia encyclopedia lookup, text/code-file analysis, vision, image generation, chat export, group mention handling.

## Limitations

Not a complete Vortex clone: arbitrary web browsing, voice transcription, task scheduling and admin panel are not yet available. Do not store credentials in chat. Public source content is untrusted.
