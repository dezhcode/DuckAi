"""Owner-approved, single-job OpenClaw queue shared by Vercel functions."""

import hashlib
import json
import os
import re
import secrets

from conversation_store import ConversationStore
from openclaw_box import BOX_OUTCOMES, OpenClawBox
from openclaw_plan import validate_plan

JOB_ID = re.compile(r'[A-Za-z0-9_-]{16}')
OUTCOMES = (*BOX_OUTCOMES, 'box_error')
ACTIVE_TTL = 300
RESULT_TTL = 600

REQUEST = """
local current = redis.call('GET', KEYS[1])
if current then
    local job = cjson.decode(current)
    if job.state == 'pending' then
        if (job.plan_key or 'check') == ARGV[3] then return current end
        return false
    end
    if job.state == 'running' then return false end
end
redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2])
return ARGV[1]
"""

TRANSITION = """
local current = redis.call('GET', KEYS[1])
if not current then return false end
local job = cjson.decode(current)
if job.state ~= ARGV[1] or job.id ~= ARGV[3] then
    return false
end
job.state = ARGV[2]
if job.state ~= 'running' then
    job.plan = nil
    job.plan_key = nil
end
local updated = cjson.encode(job)
redis.call('SET', KEYS[1], updated, 'EX', ARGV[4])
return updated
"""


class OpenClawTasks:
    def __init__(self):
        self.owner_id = os.getenv('TELEGRAM_ADMIN_ID', '').strip()
        self.box = OpenClawBox()
        self.store = ConversationStore()
        if not self.store.enabled:
            self.store = ConversationStore(os.getenv('KV_REST_API_URL', ''),
                                           os.getenv('KV_REST_API_TOKEN', ''))
        namespace = (os.getenv('VERCEL_ENV', 'development'), self.owner_id, self.box.box_id)
        key = hashlib.sha256(':'.join(namespace).encode()).hexdigest()
        self.key = 'duckai:openclaw:box-task:' + key

    @property
    def enabled(self):
        return (self.store.enabled
                and re.fullmatch(r'[1-9][0-9]{0,19}', self.owner_id) is not None
                and self.box.enabled)

    def is_owner(self, message):
        chat = message.get('chat', {})
        return (bool(self.owner_id) and chat.get('type') == 'private'
                and str(chat.get('id')) == self.owner_id
                and str(message.get('from', {}).get('id')) == self.owner_id)

    def current(self):
        raw = self.store.command(['GET', self.key])
        return json.loads(raw) if raw else None

    def request(self, plan=None):
        plan = validate_plan({'action': 'check'} if plan is None else plan)
        plan_key = ('check' if plan['action'] == 'check' else hashlib.sha256(
            json.dumps(plan, sort_keys=True, ensure_ascii=False).encode()).hexdigest())
        job = json.dumps({'id': secrets.token_urlsafe(12), 'state': 'pending',
                          'plan': plan, 'plan_key': plan_key}, ensure_ascii=False)
        raw = self.store.command(['EVAL', REQUEST, '1', self.key, job, str(ACTIVE_TTL), plan_key])
        return json.loads(raw) if raw else None

    def decide(self, job_id, approve):
        if not valid_job_id(job_id):
            return None
        state = 'running' if approve else 'cancelled'
        return self._transition('pending', state, ACTIVE_TTL, job_id)

    def complete(self, job_id, outcome):
        if not valid_job_id(job_id) or outcome not in OUTCOMES:
            return None
        return self._transition('running', outcome, RESULT_TTL, job_id)

    def _transition(self, before, after, ttl, job_id):
        raw = self.store.command(['EVAL', TRANSITION, '1', self.key, before, after, job_id, str(ttl)])
        return json.loads(raw) if raw else None


def valid_job_id(value):
    return isinstance(value, str) and JOB_ID.fullmatch(value) is not None
