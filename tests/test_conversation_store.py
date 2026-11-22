import json
import unittest
from unittest.mock import patch
from conversation_store import ConversationStore


class StoreTests(unittest.TestCase):
    def test_disabled_without_credentials(self):
        store = ConversationStore('', '')
        self.assertFalse(store.enabled)
        self.assertEqual(store.load(1, 2), {})
        store.save(1, 2, {'history': []})

    def test_roundtrip_sanitized_history(self):
        store = ConversationStore('https://example.upstash.io', 'test-token')
        calls = []
        def fake(args):
            calls.append(args)
            if args[0] == 'GET':
                return json.dumps({'history': [
                    {'role': 'user', 'content': 'hello'},
                    {'role': 'system', 'content': 'ignored'}],
                    'model': 'gpt-6-luna'})
            return 'OK'
        with patch.object(store, '_command', side_effect=fake):
            loaded = store.load(1, 2)
            self.assertEqual(loaded['history'], [{'role': 'user', 'content': 'hello'}])
            store.save(1, 2, loaded)
            self.assertEqual(calls[-1][0], 'SET')
            self.assertEqual(calls[-1][-2:], ['EX', 604800])


if __name__ == '__main__':
    unittest.main()
