import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from openclaw_box import BOX_API_URL, CHECK_COMMAND, OpenClawBox
from openclaw_tasks import OpenClawTasks, TRANSITION
from telegram_bot import Bot, TelegramError

OWNER = 12345
JOB = 'u7Z40_mocvRogfP2'
BOX_ID = 'test-openclaw-123'
BOX_KEY = 'test-box-key'


class OpenClawBotTests(unittest.TestCase):
    def setUp(self):
        self.api = Mock()
        self.bot = Bot(self.api)
        self.queue = Mock()
        self.queue.enabled = True
        self.queue.is_owner.side_effect = self.is_owner
        self.bot.openclaw = self.queue
        self.bot.shared_cooldown.enabled = False

    @staticmethod
    def is_owner(message):
        return message['from']['id'] == OWNER and message['chat'] == {'id': OWNER, 'type': 'private'}

    def message(self, chat_type='private', user=OWNER, text='/agent check'):
        return {'message_id': 1, 'chat': {'id': OWNER, 'type': chat_type},
                'from': {'id': user}, 'text': text}

    def click(self, data, message=None):
        message = message or self.message()
        self.bot.handle_update({'callback_query': {'id': 'answer', 'data': data,
                                                 'message': message, 'from': message['from']}})

    def test_confirmation_is_separate_from_request(self):
        self.queue.request.return_value = {'id': JOB, 'state': 'pending'}
        message = self.message()
        self.bot.handle_update({'message': message})
        self.queue.request.assert_called_once_with()
        self.queue.decide.assert_not_called()
        self.queue.box.check.assert_not_called()
        approval = self.api.send.call_args.args[3]['inline_keyboard'][0][0]['callback_data']
        self.assertEqual(approval, 'openclaw:approve:' + JOB)
        self.queue.decide.return_value = {'id': JOB, 'state': 'running'}

        def check():
            self.api.call.assert_called_once()
            self.assertEqual(self.api.call.call_args.args[0], 'answerCallbackQuery')
            return 'ready'

        self.queue.box.check.side_effect = check
        self.click(approval, message)
        self.queue.decide.assert_called_once_with(JOB, approve=True)
        self.queue.box.check.assert_called_once_with()
        self.queue.complete.assert_called_once_with(JOB, 'ready')
        self.assertIn('آماده است', self.api.send.call_args.args[1])

    def test_duplicate_approval_and_cancellation_do_not_run_the_box(self):
        self.queue.decide.side_effect = [
            {'id': JOB, 'state': 'running'}, None, {'id': JOB, 'state': 'cancelled'},
        ]
        self.queue.box.check.return_value = 'ready'
        self.click('openclaw:approve:' + JOB)
        self.click('openclaw:approve:' + JOB)
        self.click('openclaw:cancel:' + JOB)
        self.queue.box.check.assert_called_once()

    def test_expired_telegram_callback_still_runs_the_approved_check(self):
        self.queue.decide.return_value = {'id': JOB, 'state': 'running'}
        self.queue.box.check.return_value = 'box_error'
        self.api.call.side_effect = TelegramError('callback expired')
        self.click('openclaw:approve:' + JOB)
        self.queue.complete.assert_called_once_with(JOB, 'box_error')

    def test_groups_and_other_users_cannot_request_or_confirm(self):
        for message in (self.message(chat_type='group'), self.message(user=999)):
            self.bot.handle_update({'message': message})
            self.click('openclaw:approve:' + JOB, message)
        self.queue.request.assert_not_called()
        self.queue.decide.assert_not_called()
        self.queue.box.check.assert_not_called()

    def test_status_only_reads_the_latest_result(self):
        self.queue.current.return_value = {'id': JOB, 'state': 'ready'}
        self.bot.handle_update({'message': self.message(text='/agent status')})
        self.assertIn('آماده است', self.api.send.call_args.args[1])
        self.queue.request.assert_not_called()
        self.queue.decide.assert_not_called()


class OpenClawQueueTests(unittest.TestCase):
    def setUp(self):
        with patch.dict(os.environ, {
            'TELEGRAM_ADMIN_ID': str(OWNER), 'UPSTASH_BOX_ID': BOX_ID,
            'UPSTASH_BOX_API_KEY': BOX_KEY,
            'UPSTASH_REDIS_REST_URL': 'https://redis.example.test',
            'UPSTASH_REDIS_REST_TOKEN': 'test',
        }, clear=True):
            self.queue = OpenClawTasks()
        self.queue.store.command = Mock()

    def test_box_key_and_id_are_required(self):
        self.assertTrue(self.queue.enabled)
        self.queue.box.api_key = ''
        self.assertFalse(self.queue.enabled)
        self.queue.box.api_key = BOX_KEY
        self.queue.box.box_id = 'a/b'
        self.assertFalse(self.queue.enabled)

    def test_approval_and_result_are_bound_to_prior_state_and_job_id(self):
        command = self.queue.store.command
        self.assertIsNone(self.queue.decide('bad-id', approve=True))
        self.assertIsNone(self.queue.complete(JOB, 'shell'))
        command.assert_not_called()
        command.return_value = json.dumps({'id': JOB, 'state': 'running'})
        self.assertEqual(self.queue.decide(JOB, approve=True)['state'], 'running')
        command.assert_called_with(['EVAL', TRANSITION, '1', self.queue.key,
                                    'pending', 'running', JOB, '300'])
        command.return_value = None
        self.assertIsNone(self.queue.complete(JOB, 'ready'))
        command.assert_called_with(['EVAL', TRANSITION, '1', self.queue.key,
                                    'running', 'ready', JOB, '600'])


class OpenClawBoxTests(unittest.TestCase):
    def setUp(self):
        with patch.dict(os.environ, {'UPSTASH_BOX_ID': BOX_ID, 'UPSTASH_BOX_API_KEY': BOX_KEY}):
            self.check = OpenClawBox()
        self.sdk = Mock()
        sdk_patch = patch.dict(sys.modules, {'upstash_box': self.sdk})
        sdk_patch.start()
        self.addCleanup(sdk_patch.stop)
        self.sdk.BoxError = type('BoxError', (Exception,), {})
        context = self.sdk.Box.get.return_value
        self.box = Mock(keep_alive=False)
        context.__enter__ = Mock(return_value=self.box)
        context.__exit__ = Mock(return_value=False)

    def test_only_fixed_readiness_check_runs_and_result_is_validated(self):
        self.box.exec.command.return_value = SimpleNamespace(status='completed', result='ready\n')
        self.assertEqual(self.check.check(), 'ready')
        self.sdk.Box.get.assert_called_once_with(BOX_ID, api_key=BOX_KEY,
                                                base_url=BOX_API_URL, timeout=55_000)
        self.box.exec.command.assert_called_once_with(CHECK_COMMAND)
        self.box.exec.command.return_value.result = 'ready\nunexpected data'
        self.assertEqual(self.check.check(), 'box_error')

    def test_keep_alive_box_is_skipped(self):
        self.box.keep_alive = True
        self.assertEqual(self.check.check(), 'box_error')
        self.box.exec.command.assert_not_called()

    def test_provider_error_becomes_a_retryable_chat_result(self):
        self.sdk.Box.get.side_effect = self.sdk.BoxError('details stay private')
        self.assertEqual(self.check.check(), 'box_error')
