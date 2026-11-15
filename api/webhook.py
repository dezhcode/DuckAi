import json
import logging
import os
from http.server import BaseHTTPRequestHandler

from telegram_bot import Bot, TelegramAPI, authorized

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
bot = Bot(TelegramAPI(TOKEN))
MAX_UPDATE_BYTES = 1024 * 1024


class handler(BaseHTTPRequestHandler):
    def respond(self, status, body):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.respond(200, {'ok': bool(TOKEN), 'service': 'DuckAI Telegram webhook',
                           'features': ['text', 'image-understanding', 'image-generation', 'natural-image-requests'], 'version': '2.1.0'})

    def do_POST(self):
        if not authorized(TOKEN, self.headers.get('X-Telegram-Bot-Api-Secret-Token', '')):
            self.respond(401, {'ok': False})
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= MAX_UPDATE_BYTES:
                self.respond(413, {'ok': False})
                return
            update = json.loads(self.rfile.read(size))
            if not isinstance(update, dict):
                raise ValueError('Invalid update')
        except (ValueError, UnicodeDecodeError):
            self.respond(400, {'ok': False})
            return
        try:
            bot.handle_update(update)
        except Exception as error:
            logging.warning('update_failed type=%s', type(error).__name__)
            self.respond(500, {'ok': False})
            return
        self.respond(200, {'ok': True})
