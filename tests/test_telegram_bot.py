import base64
import io
import tempfile
import threading
import unittest
from http.server import HTTPServer
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from PIL import Image

import telegram_bot as telegram
from duck_cli import DuckAI


def image_bytes():
    buffer = io.BytesIO()
    Image.new('RGB', (16, 16), 'red').save(buffer, 'JPEG')
    return buffer.getvalue()


class FakeAPI:
    token = 'test-only-token'

    def __init__(self):
        self.sent = []
        self.photos = []
        self.calls = []
        self.downloads = []

    def send(self, chat, text, reply_to=None, markup=None):
        self.sent.append((chat, text, reply_to, markup))

    def call(self, method, payload):
        self.calls.append((method, payload))

    def action(self, chat, action):
        self.calls.append(('action', action))

    def download(self, attachment):
        self.downloads.append(attachment)
        return image_bytes()

    def photo(self, chat, path, reply_to=None):
        self.photos.append((chat, Path(path).read_bytes(), reply_to, path))


class EventClient(DuckAI):
    def __init__(self):
        super().__init__()
        self.text_stream = Mock(return_value=[('message', 'یک تصویر قرمز است.')])
        self.image_requests = []

    def stream_events(self, prompt, **kwargs):
        if kwargs.get('draw'):
            self.image_requests.append((prompt, kwargs))
            yield ('message', 'تصویر آماده شد.')
            yield ('image', {'b64': base64.b64encode(image_bytes()).decode(), 'format': 'jpeg'})
        else:
            yield from self.text_stream(prompt, **kwargs)


class BotFlowTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeAPI()
        self.client = EventClient()
        self.bot = telegram.Bot(self.api, lambda: self.client)
        self.message = {'chat': {'id': 12}, 'from': {'id': 34}, 'message_id': 56}

    def run_message(self, **fields):
        self.bot.handle_update({'update_id': 1, 'message': dict(self.message, **fields)})

    def test_captioned_photo_reaches_client_as_webp(self):
        small = {'file_id': 'small', 'width': 10, 'height': 10}
        large = {'file_id': 'large', 'width': 100, 'height': 100}
        self.run_message(photo=[large, small], caption='چه می‌بینی؟')
        args, kwargs = self.client.text_stream.call_args
        self.assertEqual(args[0], 'چه می‌بینی؟')
        self.assertEqual(self.api.downloads, [large])
        part = kwargs['images'][0]
        self.assertEqual(part['mimeType'], 'image/webp')
        with Image.open(io.BytesIO(base64.b64decode(part['image'].split(',')[1]))) as picture:
            self.assertEqual(picture.format, 'WEBP')
        self.assertIn('قرمز', self.api.sent[-1][1])

    def test_photo_without_caption_gets_default_question(self):
        self.run_message(photo=[{'file_id': 'photo', 'width': 1, 'height': 1}])
        self.assertIn('تصویر', self.client.text_stream.call_args.args[0])

    def test_reply_to_photo_uses_the_new_question(self):
        self.run_message(text='رنگ آن چیست؟', reply_to_message={'photo': [{'file_id': 'reply'}]})
        self.assertEqual(self.api.downloads[0]['file_id'], 'reply')
        self.assertEqual(self.client.text_stream.call_args.args[0], 'رنگ آن چیست؟')

    def test_image_document_is_supported(self):
        self.run_message(document={'file_id': 'document', 'mime_type': 'image/png'}, caption='شرح بده')
        self.assertEqual(self.api.downloads[0]['file_id'], 'document')

    def test_text_chat_still_works(self):
        self.run_message(text='سلام')
        self.assertIsNone(self.client.text_stream.call_args.kwargs['images'])

    def test_image_generation_uses_repo_parser_and_uploads_a_jpeg(self):
        self.run_message(text='/draw یک گربه فضانورد')
        self.assertEqual(self.client.image_requests[0][0], 'یک گربه فضانورد')
        self.assertTrue(self.client.image_requests[0][1]['draw'])
        self.assertEqual(self.client.image_requests[0][1]['retries'], 1)
        self.assertEqual(len(self.api.photos), 1)
        chat, data, reply_to, path = self.api.photos[0]
        self.assertEqual((chat, reply_to), (12, 56))
        with Image.open(io.BytesIO(data)) as photo:
            self.assertEqual(photo.format, 'JPEG')
        self.assertFalse(Path(path).exists(), 'temporary generated files must be removed')

    def test_draw_requires_a_prompt(self):
        self.run_message(text='/draw')
        self.assertFalse(self.client.image_requests)
        self.assertIn('/draw', self.api.sent[0][1])

    def test_flying_car_request_generates_image_without_command(self):
        self.run_message(text='یک ماشین پرنده طراحی کن')
        self.assertEqual(self.client.image_requests[0][0], 'یک ماشین پرنده طراحی کن')
        self.assertEqual(len(self.api.photos), 1)
        self.assertIn('ماشین پرنده', self.bot.session(self.message)['history'][0]['content'][0]['text'])

    def test_polite_and_english_image_requests_do_not_need_commands(self):
        for prompt in ('یک ماشین پرنده طراحی کن لطفاً', 'طراحی کن یک ماشین پرنده',
                       'می\u200cخوام یک عکس از جنگل بسازی', 'یه گربه برام بکش',
                       'Create an image of a flying car', 'Please draw a cat'):
            with self.subTest(prompt=prompt):
                api = FakeAPI()
                bot = telegram.Bot(api, lambda: EventClient())
                bot.handle_update({'message': dict(self.message, text=prompt)})
                self.assertEqual(len(api.photos), 1)

    def test_image_questions_negations_and_code_stay_in_text_chat(self):
        for prompt in ('چطور یک ماشین پرنده طراحی کنم؟', 'طراحی ماشین پرنده را توضیح بده',
                       'نمی\u200cخوام عکس بسازی', 'عکس نساز', 'کد یک برنامه طراحی کن',
                       'یک برنامه ورزشی طراحی کن', 'برام سایت طراحی کن',
                       'How do I draw a cat?', "Don't draw a cat", 'Translate: draw a cat'):
            with self.subTest(prompt=prompt):
                api = FakeAPI()
                client = EventClient()
                bot = telegram.Bot(api, lambda: client)
                bot.handle_update({'message': dict(self.message, text=prompt)})
                self.assertEqual(len(api.photos), 0)
                self.assertEqual(len(client.image_requests), 0)
                client.text_stream.assert_called_once()

    def test_provider_selected_image_tool_is_delivered_from_ordinary_chat(self):
        self.client.text_stream.return_value = [
            ('tool', {'toolName': 'GenerateImage'}),
            ('image_partial', {'status': 'partial'}),
            ('image', {'b64': base64.b64encode(image_bytes()).decode(), 'format': 'jpeg'}),
        ]
        self.run_message(text='یک منظره رؤیایی برایم مجسم می‌کنی؟')
        self.assertEqual(len(self.api.photos), 1)
        self.assertFalse(self.client.text_stream.call_args.kwargs['draw'])
        self.assertFalse(self.api.sent, 'an image-only response must not send empty-answer text')

    def test_photo_description_is_not_routed_to_image_generation(self):
        self.run_message(photo=[{'file_id': 'photo'}], caption='این عکس را توصیف کن')
        self.assertEqual(len(self.api.photos), 0)
        self.assertTrue(self.client.text_stream.call_args.kwargs['images'])

    def test_incomplete_generated_image_is_reported_as_failure(self):
        self.client.text_stream.return_value = [('image_title', 'Generating')]
        self.run_message(text='یک منظره رؤیایی برایم مجسم می‌کنی؟')
        self.assertFalse(self.api.photos)
        self.assertIn('ناموفق', self.api.sent[-1][1])

    def test_unsupported_vision_model_falls_back_without_changing_selection(self):
        session = self.bot.session(self.message)
        session['model'] = telegram.MODELS['oss']
        self.run_message(photo=[{'file_id': 'photo'}])
        self.assertEqual(self.client.text_stream.call_args.kwargs['model'], telegram.DEFAULT_MODEL)
        self.assertEqual(session['model'], telegram.MODELS['oss'])

    def test_duplicate_updates_do_not_generate_duplicate_images(self):
        self.run_message(text='/draw a cat')
        self.run_message(text='/draw a cat')
        self.assertEqual(len(self.api.photos), 1)

    def test_callback_model_selection_clears_previous_history(self):
        session = self.bot.session(self.message)
        session['history'] = [{'role': 'assistant', 'content': 'old'}]
        self.bot.handle_update({'callback_query': {'id': 'callback', 'from': {'id': 34},
                              'message': self.message, 'data': 'model:' + telegram.MODELS['mini']}})
        self.assertEqual(session['model'], telegram.MODELS['mini'])
        self.assertEqual(session['history'], [])

    def test_errors_never_echo_credentials(self):
        self.client.text_stream.side_effect = RuntimeError('sensitive-token')
        self.run_message(text='hi')
        self.assertNotIn('sensitive-token', self.api.sent[-1][1])

    def test_upstream_rate_limits_have_a_useful_safe_message(self):
        self.client.text_stream.side_effect = telegram.DuckAIError('private provider details', status=429)
        self.run_message(text='hi')
        self.assertIn('محدود', self.api.sent[-1][1])
        self.assertNotIn('private provider details', self.api.sent[-1][1])

    def test_users_in_same_group_have_separate_history(self):
        first = self.bot.session(self.message)
        second = self.bot.session(dict(self.message, **{'from': {'id': 35}}))
        self.assertIsNot(first, second)

    def test_each_request_uses_a_new_client_and_closes_it(self):
        first, second = EventClient(), EventClient()
        first.s.cookies.set('fixture', 'first-only')
        self.bot.client_factory = Mock(side_effect=[first, second])
        with patch.object(first.s, 'close') as first_close, patch.object(second.s, 'close') as second_close:
            self.run_message(text='سلام')
            self.bot.handle_update({'update_id': 2, 'message': dict(self.message, text='ادامه بده')})
            first_close.assert_called_once()
            second_close.assert_called_once()
        self.assertEqual(self.bot.client_factory.call_count, 2)
        self.assertIsNone(second.s.cookies.get('fixture'))
        self.assertNotIn('client', self.bot.session(self.message))

    def test_clear_resets_conversation_without_holding_a_provider_client(self):
        self.run_message(text='سلام')
        self.bot.handle_update({'update_id': 2, 'message': dict(self.message, text='/clear')})
        session = self.bot.session(self.message)
        self.assertNotIn('client', session)
        self.assertEqual(session['history'], [])

    def test_failed_request_also_closes_the_client(self):
        self.client.text_stream.side_effect = RuntimeError('fixture failure')
        with patch.object(self.client.s, 'close') as close:
            self.run_message(text='سلام')
            close.assert_called_once()
        self.assertTrue(self.bot.ai_gate.acquire(blocking=False))
        self.bot.ai_gate.release()

    def test_real_stream_initializes_a_fresh_challenge_for_each_request(self):
        clients = []
        def factory():
            client = DuckAI()
            def handshake():
                client.fe_version = 'fixture-version'
                client.jsa = 'fixture-proof'
            client.rehandshake = Mock(side_effect=handshake)
            response = Mock(status_code=200)
            response.iter_lines.return_value = iter([b'data: {"message":"hello"}'])
            client.chat = Mock(return_value=response)
            client.s.close = Mock(wraps=client.s.close)
            clients.append(client)
            return client
        self.bot.client_factory = factory
        self.run_message(text='سلام')
        self.bot.handle_update({'update_id': 2, 'message': dict(self.message, text='ادامه بده')})
        self.assertEqual(len(clients), 2)
        self.assertIsNot(clients[0].s, clients[1].s)
        for client in clients:
            client.rehandshake.assert_called_once()
            client.chat.assert_called_once()
            client.s.close.assert_called_once()

    def test_upstream_retry_after_blocks_repeated_calls_before_new_client(self):
        clock = [100.0]
        self.bot.client_factory = Mock(return_value=self.client)
        self.client.text_stream.side_effect = telegram.DuckAIError('reject', status=418, stage='chat', retry_after=120)
        with patch.object(telegram.time, 'monotonic', side_effect=lambda: clock[0]):
            self.run_message(text='سلام')
            clock[0] = 110
            self.bot.handle_update({'update_id': 2, 'message': dict(self.message, text='دوباره')})
            self.assertEqual(self.client.text_stream.call_count, 1)
            self.assertIn('110', self.api.sent[-1][1])
            self.client.text_stream.side_effect = None
            clock[0] = 221
            self.bot.handle_update({'update_id': 3, 'message': dict(self.message, text='ادامه')})
            self.assertEqual(self.client.text_stream.call_count, 2)
            self.assertEqual(self.bot.client_factory.call_count, 2)
            self.assertNotIn('client', self.bot.session(self.message))

    def test_new_chat_does_not_cancel_cooldown(self):
        self.bot.ai_not_before = telegram.time.monotonic() + 120
        self.run_message(text='/clear')
        self.bot.handle_update({'update_id': 2, 'message': dict(self.message, text='سلام')})
        self.client.text_stream.assert_not_called()

    def test_busy_instance_does_not_start_another_upstream_request(self):
        self.bot.ai_gate.acquire()
        try:
            self.run_message(text='سلام')
            self.client.text_stream.assert_not_called()
            self.assertIn('در حال پردازش', self.api.sent[-1][1])
        finally:
            self.bot.ai_gate.release()

    def test_expired_conversation_does_not_retain_connections(self):
        self.run_message(text='سلام')
        first = self.bot.session(self.message)
        first['used'] = telegram.time.monotonic() - 1801
        self.bot.session(dict(self.message, **{'from': {'id': 99}}))
        self.assertNotIn((12, 34), self.bot.sessions)
        self.assertNotIn('client', first)

    def test_error_log_has_stage_without_provider_message_or_token(self):
        self.client.text_stream.side_effect = telegram.DuckAIError('secret prompt and token', status=418,
                                                                  stage='chat', provider_code='ERR_LIMIT')
        with self.assertLogs('telegram_bot', level='WARNING') as logs:
            self.run_message(text='سلام')
        self.assertIn('stage=chat', logs.output[0])
        self.assertIn('provider_code=ERR_LIMIT', logs.output[0])
        self.assertNotIn('secret prompt', logs.output[0])

    def test_challenge_failure_is_not_labelled_as_a_confirmed_usage_limit(self):
        self.client.text_stream.side_effect = telegram.DuckAIError('reject', status=418, stage='chat',
                                                                  provider_code='ERR_CHALLENGE')
        self.run_message(text='سلام')
        self.assertIn('ممکن نشد', self.api.sent[-1][1])
        self.assertNotIn('اعتبارسنجی', self.api.sent[-1][1])
        self.assertNotIn('محدودیت استفاده', self.api.sent[-1][1])

    def test_challenge_without_retry_after_has_no_countdown_and_only_one_retry(self):
        self.client.text_stream.side_effect = telegram.DuckAIError('reject', status=418, stage='chat',
                                                                  provider_code='ERR_CHALLENGE')
        self.run_message(text='سلام')
        self.assertLessEqual(self.bot.ai_not_before, telegram.time.monotonic())
        self.assertNotIn('ثانیه', self.api.sent[-1][1])
        self.assertEqual(self.client.text_stream.call_count, 2)
        self.bot.handle_update({'update_id': 2, 'message': dict(self.message, text='یک درخواست جدید')})
        self.assertEqual(self.client.text_stream.call_count, 4)

    def test_provider_retry_after_on_challenge_still_applies(self):
        self.client.text_stream.side_effect = telegram.DuckAIError('reject', status=418, stage='chat',
                                                                  provider_code='ERR_CHALLENGE', retry_after=120)
        self.run_message(text='سلام')
        self.assertIn('120', self.api.sent[-1][1])
        self.bot.handle_update({'update_id': 2, 'message': dict(self.message, text='یک درخواست جدید')})
        self.assertEqual(self.client.text_stream.call_count, 1)

    def test_usage_limit_without_retry_after_retains_bounded_backoff(self):
        self.client.text_stream.side_effect = telegram.DuckAIError('limit', status=429, stage='chat')
        self.run_message(text='سلام')
        self.assertIn('30', self.api.sent[-1][1])
        self.assertIn('محدودیت استفاده', self.api.sent[-1][1])

    def test_first_challenge_failure_is_hidden_and_fresh_session_can_succeed(self):
        first, second = EventClient(), EventClient()
        first.text_stream.side_effect = telegram.DuckAIError('private error', status=418, stage='chat',
                                                            provider_code='ERR_CHALLENGE')
        self.bot.client_factory = Mock(side_effect=[first, second])
        with patch.object(first.s, 'close') as first_close, patch.object(second.s, 'close') as second_close:
            self.run_message(text='سلام')
            first_close.assert_called_once()
            second_close.assert_called_once()
        self.assertEqual(self.bot.client_factory.call_count, 2)
        self.assertEqual(len(self.api.sent), 1)
        self.assertEqual(self.api.sent[0][1], 'یک تصویر قرمز است.')
        self.assertNotIn('اعتبارسنجی', self.api.sent[0][1])
        self.assertEqual(len(self.bot.session(self.message)['history']), 2)

    def test_two_failures_stop_and_show_only_a_generic_message(self):
        first, second = EventClient(), EventClient()
        for client in (first, second):
            client.text_stream.side_effect = telegram.DuckAIError('private error', status=418, stage='chat',
                                                                 provider_code='ERR_CHALLENGE')
        self.bot.client_factory = Mock(side_effect=[first, second])
        self.run_message(text='سلام')
        self.assertEqual(self.bot.client_factory.call_count, 2)
        self.assertEqual(len(self.api.sent), 1)
        self.assertIn('ممکن نشد', self.api.sent[0][1])
        self.assertNotIn('اعتبارسنجی', self.api.sent[0][1])
        self.assertNotIn('private error', self.api.sent[0][1])

    def test_partial_response_is_not_replayed(self):
        def partial(*args, **kwargs):
            yield ('message', 'partial response')
            raise telegram.DuckAIError('reject', status=418, stage='chat', provider_code='ERR_CHALLENGE')
        self.client.text_stream.side_effect = partial
        self.bot.client_factory = Mock(return_value=self.client)
        self.run_message(text='سلام')
        self.bot.client_factory.assert_called_once()
        self.assertEqual(len(self.api.sent), 1)
        self.assertNotIn('partial response', self.api.sent[0][1])

    def test_image_request_retries_once_and_uploads_only_once(self):
        first, second = EventClient(), EventClient()
        first.stream_events = Mock(side_effect=telegram.DuckAIError('reject', status=418, stage='chat',
                                                                   provider_code='ERR_CHALLENGE'))
        self.bot.client_factory = Mock(side_effect=[first, second])
        self.run_message(text='یک ماشین پرنده طراحی کن')
        self.assertEqual(self.bot.client_factory.call_count, 2)
        self.assertEqual(len(self.api.photos), 1)
        self.assertEqual(first.stream_events.call_args.args[0], second.image_requests[0][0])
        self.assertFalse(any('اعتبارسنجی' in item[1] for item in self.api.sent))

    def test_stopping_response_stream_closes_upstream_response_and_client(self):
        client = DuckAI()
        client.fe_version, client.jsa = 'fixture', 'fixture'
        response = Mock(status_code=200)
        response.iter_lines.return_value = iter([b'data: {"message":"a"}', b'data: {"message":"b"}'])
        client.chat = Mock(return_value=response)
        self.bot.client_factory = Mock(return_value=client)
        with patch.object(client.s, 'close') as close:
            events = self.bot.response_events('hello')
            self.assertEqual(next(events), ('message', 'a'))
            events.close()
            close.assert_called_once()
            response.close.assert_called_once()


class TelegramTransportTests(unittest.TestCase):
    def test_invalid_webhook_secret_is_rejected_without_throwing(self):
        for supplied in ('', 'invalid', 'é' * 32, None):
            self.assertFalse(telegram.authorized('test', supplied))

    def test_photo_is_a_multipart_upload(self):
        response = Mock(ok=True)
        response.json.return_value = {'ok': True, 'result': {}}
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'image.jpg'
            path.write_bytes(image_bytes())
            with patch.object(telegram.requests, 'post', return_value=response) as post:
                telegram.TelegramAPI('test').photo(12, str(path), 56)
                kwargs = post.call_args.kwargs
                self.assertIn('photo', kwargs['files'])
                self.assertEqual(kwargs['data']['chat_id'], 12)
                self.assertNotIn('json', kwargs)

    def test_oversized_download_is_rejected_before_network_call(self):
        api = telegram.TelegramAPI('test')
        api.call = Mock()
        with self.assertRaises(telegram.UserInputError):
            api.download({'file_id': 'x', 'file_size': telegram.MAX_FILE_BYTES + 1})
        api.call.assert_not_called()

    def test_utf16_message_limit_is_respected(self):
        api = telegram.TelegramAPI('test')
        api.call = Mock()
        api.send(12, '😀' * 4500)
        self.assertEqual(api.call.call_count, 3)
        for call in api.call.call_args_list:
            self.assertLessEqual(len(call.args[1]['text'].encode('utf-16-le')) // 2, 4096)


class WebhookHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import api.webhook as webhook
        cls.webhook = webhook
        cls.server = HTTPServer(('127.0.0.1', 0), webhook.handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = 'http://127.0.0.1:' + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_post_authentication_and_payload_validation(self):
        with patch.object(self.webhook, 'TOKEN', 'test'), patch.object(self.webhook, 'bot') as bot:
            self.assertEqual(requests.post(self.url, json={}).status_code, 401)
            bot.handle_update.assert_not_called()
            headers = {'X-Telegram-Bot-Api-Secret-Token': telegram.webhook_secret('test')}
            self.assertEqual(requests.post(self.url, data='bad', headers=headers).status_code, 400)
            self.assertEqual(requests.post(self.url, json={'update_id': 1}, headers=headers).status_code, 200)
            bot.handle_update.assert_called_once_with({'update_id': 1})

    def test_health_reports_features_without_secrets(self):
        response = requests.get(self.url)
        self.assertIn('image-understanding', response.json()['features'])
        self.assertIn('image-generation', response.json()['features'])
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertNotIn('token', response.text.lower())
