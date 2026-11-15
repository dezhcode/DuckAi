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
        for status in (400, 401, 403, 429):
            with self.subTest(status=status):
                response = self.response(status=status)
                with patch.object(self.client, 'chat', return_value=response) as chat:
                    with self.assertRaises(duck.DuckAIError) as error:
                        self.client.ask('hi')
                self.assertEqual(error.exception.status, status)
                chat.assert_called_once()
                response.close.assert_called_once()

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


if __name__ == '__main__':
    unittest.main()
