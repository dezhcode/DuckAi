"""Optional persistent Telegram conversation state via Upstash Redis REST.

Set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN on Vercel.
No credentials are logged. Data expires automatically after 7 days.
"""
import hashlib
import json
import os
import requests

TTL = 7 * 24 * 3600
MAX_HISTORY = 12
MAX_CONTENT = 3500


class ConversationStore:
    def __init__(self, url=None, token=None):
        self.url = (url if url is not None else os.getenv('UPSTASH_REDIS_REST_URL', '')).rstrip('/')
        self.token = token if token is not None else os.getenv('UPSTASH_REDIS_REST_TOKEN', '')

    @property
    def enabled(self):
        return self.url.startswith('https://') and bool(self.token)

    def _key(self, chat_id, user_id):
        identifier = str(chat_id) + ':' + str(user_id)
        return 'trump:session:' + hashlib.sha256(identifier.encode()).hexdigest()

    def _command(self, args):
        if not self.enabled:
            return None
        response = requests.post(self.url, json=args, headers={
            'Authorization': 'Bearer ' + self.token,
            'Content-Type': 'application/json'}, timeout=(2, 4))
        response.raise_for_status()
        body = response.json()
        if body.get('error'):
            raise ValueError('Redis command failed')
        return body.get('result')

    def load(self, chat_id, user_id):
        if not self.enabled:
            return {}
        raw = self._command(['GET', self._key(chat_id, user_id)])
        if not raw:
            return {}
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            return {}
        history = obj.get('history', [])
        clean = []
        if isinstance(history, list):
            for turn in history[-MAX_HISTORY:]:
                if isinstance(turn, dict) and turn.get('role') in ('user', 'assistant') and isinstance(turn.get('content'), str):
                    clean.append({'role': turn['role'], 'content': turn['content'][:MAX_CONTENT]})
        return {'history': clean, 'model': str(obj.get('model', ''))[:100],
                'news_topic': str(obj.get('news_topic') or '')[:700] or None}

    def save(self, chat_id, user_id, session):
        if not self.enabled:
            return
        history = []
        for turn in session.get('history', [])[-MAX_HISTORY:]:
            if isinstance(turn, dict) and turn.get('role') in ('user', 'assistant') and isinstance(turn.get('content'), str):
                history.append({'role': turn['role'], 'content': turn['content'][:MAX_CONTENT]})
        obj = {'history': history, 'model': session.get('model', ''),
               'news_topic': session.get('news_topic')}
        self._command(['SET', self._key(chat_id, user_id), json.dumps(obj, ensure_ascii=False), 'EX', TTL])

    def clear(self, chat_id, user_id):
        if self.enabled:
            self._command(['DEL', self._key(chat_id, user_id)])
