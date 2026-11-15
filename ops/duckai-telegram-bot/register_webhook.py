"""Register DuckAI's Telegram webhook with the exact secret expected by api/webhook.py.

Usage:
  TELEGRAM_BOT_TOKEN='...' python ops/duckai-telegram-bot/register_webhook.py

Never paste your bot token into a public URL, source file, or chat.
"""
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

WEBHOOK_URL = "https://duckai-telegram-bot.vercel.app/api/webhook"


def telegram_call(token, method, payload):
    url = "https://api.telegram.org/bot" + token + "/" + method
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        # Never print the request URL: it contains the bot token.
        raise RuntimeError(f"Telegram {method} failed (HTTP {exc.code})") from None
    except urllib.error.URLError:
        raise RuntimeError(f"Telegram {method} network error") from None


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token or ":" not in token:
        print("Set TELEGRAM_BOT_TOKEN in your local environment first.", file=sys.stderr)
        return 1

    identity = telegram_call(token, "getMe", {})
    if not identity.get("ok"):
        print("Telegram rejected this bot token.", file=sys.stderr)
        return 1

    secret = hashlib.sha256((token + "duck-webhook").encode()).hexdigest()[:32]
    result = telegram_call(token, "setWebhook", {
        "url": WEBHOOK_URL,
        "secret_token": secret,
        "allowed_updates": ["message", "callback_query"],
        "drop_pending_updates": False,
    })
    if not result.get("ok"):
        print("Telegram did not accept setWebhook.", file=sys.stderr)
        return 1

    info = telegram_call(token, "getWebhookInfo", {})
    data = info.get("result") or {}
    print("Bot:", identity.get("result", {}).get("username", "(unknown)"))
    print("Webhook:", data.get("url", "(missing)"))
    print("Pending updates:", data.get("pending_update_count", 0))
    if data.get("last_error_message"):
        print("Last reported error (may be historical):", data["last_error_message"])
    print("Webhook registered with matching secret token.")
    return 0 if data.get("url") == WEBHOOK_URL else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
