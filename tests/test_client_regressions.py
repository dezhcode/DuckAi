import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import duck_cli as duck


class FileInputTests(unittest.TestCase):
    def test_source_extensions_are_accepted_even_without_mime_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            for suffix in ('.py', '.json', '.yaml', '.dart', '.ts'):
                with self.subTest(suffix=suffix):
                    path = Path(directory) / ('sample' + suffix)
                    path.write_text('hello', encoding='utf-8')
                    with patch.object(duck.mimetypes, 'guess_type', return_value=(None, None)):
                        chunk = duck.file_to_prompt_chunk(str(path))
                    self.assertIn('```' + suffix[1:] + '\nhello', chunk)

    def test_binary_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sample.exe'
            path.write_bytes(b'\x00binary')
            with self.assertRaises(duck.DuckAIError):
                duck.file_to_prompt_chunk(str(path))

    def test_large_file_is_truncated_at_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sample.py'
            path.write_text('abcdefghij', encoding='utf-8')
            chunk = duck.file_to_prompt_chunk(str(path), max_chars=4)
            self.assertIn('abcd\n```', chunk)
            self.assertNotIn('abcde', chunk)
            self.assertIn('truncated', chunk)

    def test_webp_requires_a_real_webp_header_without_pillow(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fake.webp'
            path.write_bytes(b'not an image')
            with patch.object(duck, 'HAS_PIL', False):
                with self.assertRaises(duck.DuckAIError):
                    duck.image_to_data_url(str(path))

    def test_image_limit_applies_to_encoded_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'image.webp'
            path.write_bytes(b'RIFF\x04\x00\x00\x00WEBP' + b'x' * 24)
            with patch.object(duck, 'HAS_PIL', False), patch.object(duck, 'IMG_MAX_PAYLOAD', 60):
                with self.assertRaises(duck.DuckAIError):
                    duck.image_to_data_url(str(path))


class StreamTests(unittest.TestCase):
    def setUp(self):
        self.client = duck.DuckAI()
        self.client.fe_version = 'test-version'
        self.client.jsa = 'test-proof'
        self.addCleanup(self.client.s.close)

    def response(self, status=200, lines=()):
        response = Mock(status_code=status, text='upstream error')
        response.iter_lines.return_value = iter(lines)
        return response

    def test_successful_response_is_closed(self):
        response = self.response(lines=[b'data: {"message":"hello"}', b'data: [DONE]'])
        with patch.object(self.client, 'chat', return_value=response):
            self.assertEqual(self.client.ask('hi'), 'hello')
        response.close.assert_called_once()

    def test_response_is_closed_on_server_error_event(self):
        response = self.response(lines=[b'data: {"action":"error","status":500,"type":"failed"}'])
        with patch.object(self.client, 'chat', return_value=response):
            with self.assertRaises(duck.DuckAIError):
                self.client.ask('hi')
        response.close.assert_called_once()

    def test_response_is_closed_if_consumer_stops_reading(self):
        response = self.response(lines=[b'data: {"message":"hello"}', b'data: {"message":"world"}'])
        with patch.object(self.client, 'chat', return_value=response):
            events = self.client.stream_events('hi')
            self.assertEqual(next(events), ('message', 'hello'))
            events.close()
        response.close.assert_called_once()

    def test_permanent_errors_and_rate_limits_are_not_replayed(self):
        for status in (400, 401, 403, 418, 429):
            with self.subTest(status=status):
                response = self.response(status=status)
                with patch.object(self.client, 'chat', return_value=response) as chat:
                    with self.assertRaises(duck.DuckAIError) as error:
                        self.client.ask('hi')
                self.assertEqual(error.exception.status, status)
                chat.assert_called_once()
                response.close.assert_called_once()

    def test_upstream_error_has_safe_stage_code_and_retry_after(self):
        response = self.response(status=429)
        response.headers = {'Retry-After': '120'}
        response.json.return_value = {'type': 'ERR_LIMIT', 'message': 'private prompt and secret'}
        with patch.object(self.client, 'chat', return_value=response), \
             patch.object(self.client, 'rehandshake') as handshake, patch.object(duck.time, 'sleep') as sleep:
            with self.assertRaises(duck.DuckAIError) as caught:
                self.client.ask('hi', retries=4)
        error = caught.exception
        self.assertEqual((error.stage, error.provider_code, error.retry_after), ('chat', 'ERR_LIMIT', 120))
        self.assertNotIn('private', str(error))
        handshake.assert_not_called()
        sleep.assert_not_called()

    def test_challenge_endpoint_rejection_is_distinct_from_chat_rejection(self):
        response = self.response(status=418)
        response.headers = {}
        response.json.return_value = {}
        with patch.object(self.client.s, 'get', return_value=response):
            with self.assertRaises(duck.DuckAIError) as caught:
                self.client.fetch_challenge()
        self.assertEqual(caught.exception.stage, 'status')
        self.assertEqual(caught.exception.status, 418)
        response.close.assert_called_once()

    def test_bootstrap_rejection_is_closed_and_annotated(self):
        response = self.response(status=403)
        response.headers = {}
        response.json.return_value = {}
        with patch.object(self.client.s, 'get', return_value=response):
            with self.assertRaises(duck.DuckAIError) as caught:
                self.client.bootstrap()
        self.assertEqual(caught.exception.stage, 'bootstrap')
        response.close.assert_called_once()

    def test_arbitrary_provider_text_is_not_used_as_a_diagnostic_code(self):
        response = self.response(status=418)
        response.headers = {'Retry-After': 'invalid'}
        response.json.return_value = {'type': 'user prompt contains private data'}
        error = duck.DuckAIError.from_response(response, 'chat')
        self.assertIsNone(error.provider_code)
        self.assertIsNone(error.retry_after)

    def test_expired_reused_challenge_can_refresh_once(self):
        failed = self.response(status=418)
        failed.headers = {}
        failed.json.return_value = {'type': 'ERR_CHALLENGE'}
        success = self.response(lines=[b'data: {"message":"ok"}'])
        with patch.object(self.client, 'chat', side_effect=[failed, success]) as chat, \
             patch.object(self.client, 'rehandshake') as handshake:
            self.assertEqual(self.client.ask('hello', retries=2), 'ok')
        self.assertEqual(chat.call_count, 2)
        handshake.assert_called_once()

    def test_newly_fetched_challenge_rejection_is_not_replayed(self):
        self.client.fe_version = self.client.jsa = ''
        failed = self.response(status=418)
        failed.headers = {}
        failed.json.return_value = {'type': 'ERR_CHALLENGE'}
        with patch.object(self.client, 'chat', return_value=failed) as chat, \
             patch.object(self.client, 'rehandshake') as handshake:
            with self.assertRaises(duck.DuckAIError):
                self.client.ask('hello', retries=4)
        chat.assert_called_once()
        handshake.assert_called_once()  # Only the initial protocol initialization.

    def test_rejected_challenge_refresh_is_not_repeated(self):
        failed = self.response(status=418)
        failed.headers = {}
        failed.json.return_value = {'type': 'ERR_CHALLENGE'}
        with patch.object(self.client, 'chat', return_value=failed) as chat, \
             patch.object(self.client, 'rehandshake') as handshake:
            with self.assertRaises(duck.DuckAIError):
                self.client.ask('hello', retries=4)
        self.assertEqual(chat.call_count, 2)
        handshake.assert_called_once()

    def test_challenge_retry_after_is_honored_without_refresh(self):
        failed = self.response(status=418)
        failed.headers = {'Retry-After': '60'}
        failed.json.return_value = {'type': 'ERR_CHALLENGE'}
        with patch.object(self.client, 'chat', return_value=failed) as chat, \
             patch.object(self.client, 'rehandshake') as handshake:
            with self.assertRaises(duck.DuckAIError):
                self.client.ask('hello', retries=4)
        chat.assert_called_once()
        handshake.assert_not_called()

    def test_transient_error_is_closed_before_retry(self):
        failed = self.response(status=503)
        success = self.response(lines=[b'data: {"message":"recovered"}'])
        with patch.object(self.client, 'chat', side_effect=[failed, success]), \
             patch.object(self.client, 'rehandshake'), patch.object(duck.time, 'sleep'):
            self.assertEqual(self.client.ask('hi'), 'recovered')
        failed.close.assert_called_once()
        success.close.assert_called_once()

    def test_final_attempt_does_not_sleep(self):
        response = self.response(status=503)
        with patch.object(self.client, 'chat', return_value=response), \
             patch.object(duck.time, 'sleep') as sleep:
            with self.assertRaises(duck.DuckAIError):
                self.client.ask('hi', retries=1)
        sleep.assert_not_called()
        response.close.assert_called_once()

    def test_success_response_challenge_is_used_for_next_call_without_bootstrap(self):
        first = self.response(lines=[b'data: {"message":"first"}'])
        first.headers = {'x-vqd-hash-1': base64.b64encode(b'fixture-next-challenge').decode()}
        second = self.response(lines=[b'data: {"message":"second"}'])
        second.headers = {}
        with patch.object(self.client, 'chat', side_effect=[first, second]), \
             patch.object(self.client, 'solve', return_value={'client_hashes': ['next-proof']}) as solve, \
             patch.object(self.client, 'rehandshake') as handshake:
            self.assertEqual(self.client.ask('one'), 'first')
            solve.assert_not_called()  # Do not delay/read the first response body to solve future state.
            first.json.assert_not_called()
            self.assertEqual(self.client.ask('two'), 'second')
        solve.assert_called_once_with('fixture-next-challenge')
        handshake.assert_not_called()
        proof = json.loads(base64.b64decode(self.client.jsa))
        self.assertEqual(proof['client_hashes'], [duck.sha256_b64('next-proof')])
        first.close.assert_called_once()
        second.close.assert_called_once()

    def test_rejected_request_can_use_server_replacement_challenge(self):
        failed = self.response(status=418)
        failed.headers = {'x-vqd-hash-1': base64.b64encode(b'fixture-next-challenge').decode()}
        failed.json.return_value = {'type': 'ERR_CHALLENGE'}
        success = self.response(lines=[b'data: {"message":"recovered"}'])
        success.headers = {}
        self.client.fe_version = self.client.jsa = ''
        def initialize():
            self.client.fe_version, self.client.jsa = 'version', 'initial-proof'
        with patch.object(self.client, 'chat', side_effect=[failed, success]) as chat, \
             patch.object(self.client, 'solve', return_value={'client_hashes': ['next']}) as solve, \
             patch.object(self.client, 'rehandshake', side_effect=initialize) as handshake:
            self.assertEqual(self.client.ask('hello', retries=2), 'recovered')
        self.assertEqual(chat.call_count, 2)
        handshake.assert_called_once()  # Initial status request only.
        solve.assert_called_once_with('fixture-next-challenge')

    def test_bad_response_challenges_do_not_break_a_successful_answer(self):
        for header in ('!invalid!', base64.b64encode(b'\xff').decode(), 'a' * 300001):
            with self.subTest(header_length=len(header)):
                response = self.response(lines=[b'data: {"message":"ok"}'])
                response.headers = {'x-vqd-hash-1': header}
                with patch.object(self.client, 'chat', return_value=response), patch.object(self.client, 'solve') as solve:
                    self.assertEqual(self.client.ask('hello'), 'ok')
                solve.assert_not_called()
                self.assertIsNone(self.client._pending_response_challenge)

    def test_replacement_header_does_not_bypass_rate_limit_wait(self):
        failed = self.response(status=429)
        failed.headers = {'x-vqd-hash-1': base64.b64encode(b'fixture-next-challenge').decode(), 'Retry-After': '120'}
        failed.json.return_value = {'type': 'ERR_LIMIT'}
        with patch.object(self.client, 'chat', return_value=failed) as chat, patch.object(self.client, 'solve') as solve:
            with self.assertRaises(duck.DuckAIError) as caught:
                self.client.ask('hello', retries=4)
        self.assertEqual(caught.exception.retry_after, 120)
        chat.assert_called_once()
        solve.assert_not_called()

    def test_chat_transport_targets_only_duck_even_with_gemini_key_present(self):
        with patch.dict(duck.os.environ, {'GEMINI_API_KEY': 'unused-fixture'}), \
             patch.object(self.client.s, 'post', return_value=self.response()) as post:
            self.client.chat('hello', draw=True)
        post.assert_called_once()
        self.assertEqual(post.call_args.args[0], 'https://duck.ai/duckchat/v1/chat')
        self.assertEqual(json.loads(post.call_args.kwargs['data'])['metadata'], {'toolChoice': {'GenerateImage': True}})


if __name__ == '__main__':
    unittest.main()
