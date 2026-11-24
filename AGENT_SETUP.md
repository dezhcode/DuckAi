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

## OpenClaw on Upstash Box

In a private chat, the owner writes a request after `/agent`. Duck.ai proposes one task and the bot shows its exact details for confirmation. Vercel runs the approved task on the configured Box, which wakes on demand. The bot sends the result in the same chat and keeps the task status available with `/agent status` for ten minutes. Approval expires after five minutes.

For example, send `/agent یک فایل Plan.txt بساز و در آن بنویس سلام`, `/agent محتوای Plan.txt را نشان بده`, or `/agent فایل‌های پوشه را فهرست کن`. OpenClaw uses the dedicated `duckai-agent-files` folder in the Box home directory for `.txt`, `.md`, `.json`, and `.csv` files up to 4 KB each. File creation requires a new name. `/agent check` still runs the readiness check directly after confirmation. Duck.ai receives the owner's request to propose the task. The bot returns file results directly to the owner.

1. Create a free, standard Box with the Debian Node runtime and Keep Alive off. Use a dedicated Box for the bot. Copy its ID and create a Box API key in the Upstash Console. [Box quickstart](https://upstash.com/docs/box/overall/quickstart)
2. Open the Box shell and install OpenClaw. The command below installs it under the Box user's home directory. The readiness task starts the Gateway on loopback when needed and stops the process it started. This task uses no model calls. [OpenClaw Gateway options](https://docs.openclaw.ai/cli/gateway/running)

   ```sh
   npm install --global --prefix "$HOME/.local" openclaw
   "$HOME/.local/bin/openclaw" --version
   ```

3. Configure `UPSTASH_BOX_ID` and the sensitive variable `UPSTASH_BOX_API_KEY` on the Vercel project. Keep the existing numeric `TELEGRAM_ADMIN_ID` and Redis REST credential pair. The bot accepts either `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` or `KV_REST_API_URL` and `KV_REST_API_TOKEN`. [Vercel environment variables](https://vercel.com/docs/environment-variables)
4. Deploy, then send `/agent check` to the Telegram bot and confirm. For a preview test, use a separate Box and test bot with their own preview environment variables.
