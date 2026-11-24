"""Run the approved readiness check in a configured Upstash Box."""

import logging
import os
import re
import shlex

log = logging.getLogger(__name__)
BOX_OUTCOMES = ('ready', 'not_ready', 'unreachable', 'missing')
BOX_API_URL = 'https://us-east-1.box.upstash.com'

# Only this fixed command reaches the Box. The Gateway stays on loopback.
CHECK_SCRIPT = """
const { spawn } = require('node:child_process');
const { randomBytes } = require('node:crypto');
const { setTimeout: delay } = require('node:timers/promises');

async function readiness() {
  try {
    const result = await fetch('http://127.0.0.1:18789/readyz', {
      redirect: 'error', signal: AbortSignal.timeout(1000),
    });
    if (result.body) await result.body.cancel();
    return result.status;
  } catch {
    return 0;
  }
}

async function check() {
  let status = await readiness();
  if (status === 200) return 'ready';
  if (status !== 0 && status !== 503) return 'unreachable';

  let gateway;
  let spawnError;
  if (status === 0) {
    gateway = spawn('openclaw', [
      'gateway', 'run', '--allow-unconfigured', '--bind', 'loopback',
      '--port', '18789', '--auth', 'token', '--tailscale', 'off',
    ], {
      stdio: 'ignore',
      env: {
        ...process.env,
        PATH: process.env.HOME + '/.local/bin:' + process.env.PATH,
        OPENCLAW_NO_RESPAWN: '1',
        OPENCLAW_GATEWAY_TOKEN: randomBytes(32).toString('hex'),
      },
    });
    gateway.on('error', (error) => { spawnError = error.code; });
    gateway.unref();
  }

  let answered = status === 503;
  try {
    const deadline = Date.now() + 25000;
    while (Date.now() < deadline) {
      status = await readiness();
      if (status === 200) return 'ready';
      if (spawnError === 'ENOENT') return 'missing';
      if (spawnError) return 'unreachable';
      answered ||= status === 503;
      if (gateway && gateway.exitCode !== null) break;
      await delay(750);
    }
    return answered ? 'not_ready' : 'unreachable';
  } finally {
    if (gateway?.pid && gateway.exitCode === null) gateway.kill('SIGTERM');
  }
}

check().then((outcome) => console.log(outcome)).catch(() => console.log('unreachable'));
"""
CHECK_COMMAND = 'timeout --kill-after=5s 35s node -e ' + shlex.quote(CHECK_SCRIPT)


class OpenClawBox:
    def __init__(self):
        self.box_id = os.getenv('UPSTASH_BOX_ID', '').strip()
        self.api_key = os.getenv('UPSTASH_BOX_API_KEY', '').strip()

    @property
    def enabled(self):
        return bool(self.api_key and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', self.box_id))

    def check(self):
        from httpx import RequestError
        from upstash_box import Box, BoxError

        try:
            with Box.get(self.box_id, api_key=self.api_key,
                         base_url=BOX_API_URL, timeout=55_000) as box:
                if box.keep_alive:
                    log.warning('openclaw_box_keep_alive_enabled')
                    return 'box_error'
                run = box.exec.command(CHECK_COMMAND)
        except (BoxError, RequestError, TimeoutError, ValueError) as error:
            log.warning('openclaw_box_check_failed type=%s', type(error).__name__)
            return 'box_error'
        result = run.result.strip() if isinstance(run.result, str) else ''
        if run.status == 'completed' and result in BOX_OUTCOMES:
            return result
        log.warning('openclaw_box_unexpected_result')
        return 'box_error'
