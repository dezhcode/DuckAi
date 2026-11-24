"""Launch the workspace tool in a private OpenClaw Gateway for one approved task."""

import base64
import json
import shlex

WORKSPACE_TOOL = r"""
import fs from 'node:fs/promises';
import { constants } from 'node:fs';
import path from 'node:path';

const root = path.join(process.env.HOME, 'duckai-agent-files');
const maxFileBytes = 4096;
const namePattern = /^[\p{L}\p{N}_][\p{L}\p{N}_ .()\-\u200c]{0,78}\.(?:txt|md|json|csv)$/iu;
const validName = (name) => typeof name === 'string' && namePattern.exec(name)?.[0] === name;
const outcome = (state, data) => ({ content: [], details: { state, data } });

async function listFiles() {
  const names = [];
  let visited = 0;
  for await (const entry of await fs.opendir(root)) {
    if (++visited > 200 || names.length === 40) {
      return outcome('done', { names: names.sort(), truncated: true });
    }
    if (entry.isFile() && validName(entry.name)) names.push(entry.name);
  }
  return outcome('done', { names: names.sort(), truncated: false });
}

async function readFile(target) {
  try {
    const file = await fs.open(target, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
    try {
      const info = await file.stat();
      if (!info.isFile() || info.nlink !== 1) return outcome('file_unavailable');
      if (info.size > maxFileBytes) return outcome('file_too_large');
      const bytes = Buffer.alloc(maxFileBytes + 1);
      let used = 0;
      while (used < bytes.length) {
        const { bytesRead } = await file.read(bytes, used, bytes.length - used, null);
        if (!bytesRead) break;
        used += bytesRead;
      }
      if (used > maxFileBytes) return outcome('file_too_large');
      const text = new TextDecoder('utf-8', { fatal: true }).decode(bytes.subarray(0, used));
      return text.includes('\0') ? outcome('file_unavailable') : outcome('done', text);
    } finally {
      await file.close();
    }
  } catch (error) {
    return outcome(error.code === 'ENOENT' ? 'file_missing' : 'file_unavailable');
  }
}

async function createFile(target, content) {
  const staged = await fs.mkdtemp(path.join(root, '.create-'));
  try {
    const stagingFile = path.join(staged, 'file');
    await fs.writeFile(stagingFile, content, { flag: 'wx', mode: 0o600 });
    await fs.link(stagingFile, target);
    return outcome('done');
  } catch (error) {
    if (error.code === 'EEXIST') return outcome('file_exists');
    throw error;
  } finally {
    await fs.rm(staged, { recursive: true, force: true });
  }
}

export default {
  id: 'duckai-workspace',
  register(api) {
    api.registerTool({
      name: 'duckai_workspace',
      description: 'List, read, or create text files in the private DuckAI agent workspace.',
      parameters: {
        type: 'object',
        properties: {
          action: { type: 'string', enum: ['list_files', 'read_file', 'create_file'] },
          filename: { type: 'string' },
          content: { type: 'string' },
        },
        required: ['action'],
        additionalProperties: false,
      },
      async execute(_id, input) {
        const { action, filename, content } = input;
        await fs.mkdir(root, { recursive: true, mode: 0o700 });
        if (!(await fs.lstat(root)).isDirectory()) return outcome('file_unavailable');
        if (action === 'list_files') return listFiles();
        if (!validName(filename)) return outcome('file_unavailable');
        const target = path.join(root, filename);
        if (action === 'read_file') return readFile(target);
        if (action === 'create_file' && typeof content === 'string' && !content.includes('\0')
            && Buffer.byteLength(content) <= maxFileBytes) {
          return createFile(target, content);
        }
        return outcome('file_unavailable');
      },
    });
  },
};
"""

GATEWAY_RUNNER = """
const fs = require('node:fs/promises');
const { tmpdir } = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { randomBytes } = require('node:crypto');
const { setTimeout: delay } = require('node:timers/promises');

async function execute() {
  const plan = JSON.parse(Buffer.from(process.argv[1], 'base64url').toString('utf8'));
  const source = Buffer.from(process.argv[2], 'base64url');
  const state = await fs.mkdtemp(path.join(tmpdir(), 'duckai-openclaw-'));
  const token = randomBytes(32).toString('hex');
  const port = '19829';
  const origin = 'http://127.0.0.1:' + port;
  const configPath = path.join(state, 'openclaw.json');
  const pluginPath = path.join(state, 'duckai-workspace');
  let gateway;
  let closed;
  try {
    await fs.mkdir(pluginPath, { mode: 0o700 });
    await fs.writeFile(path.join(pluginPath, 'index.mjs'), source, { mode: 0o600 });
    await fs.writeFile(path.join(pluginPath, 'package.json'), JSON.stringify({
      name: 'duckai-workspace', type: 'module', version: '1.0.0',
      openclaw: { extensions: ['./index.mjs'] },
    }), { mode: 0o600 });
    await fs.writeFile(path.join(pluginPath, 'openclaw.plugin.json'), JSON.stringify({
      id: 'duckai-workspace', name: 'DuckAI Workspace',
      activation: { onStartup: true }, contracts: { tools: ['duckai_workspace'] },
      configSchema: { type: 'object', properties: {}, additionalProperties: false },
    }), { mode: 0o600 });
    await fs.writeFile(configPath, JSON.stringify({
      gateway: { mode: 'local', bind: 'loopback', controlUi: { enabled: false } },
      agents: { defaults: { workspace: state, skipBootstrap: true } },
      tools: { allow: ['duckai_workspace'] },
      plugins: {
        allow: ['duckai-workspace'],
        load: { paths: [pluginPath] },
        entries: { 'duckai-workspace': { enabled: true } },
      },
    }), { mode: 0o600 });
    gateway = spawn('openclaw', [
      'gateway', 'run', '--bind', 'loopback', '--port', port, '--auth', 'token', '--tailscale', 'off',
    ], {
      cwd: state, stdio: 'ignore',
      env: {
        HOME: process.env.HOME,
        PATH: process.env.HOME + '/.local/bin:' + process.env.PATH,
        OPENCLAW_NO_RESPAWN: '1',
        OPENCLAW_GATEWAY_TOKEN: token,
        OPENCLAW_STATE_DIR: state,
        OPENCLAW_CONFIG_PATH: configPath,
      },
    });
    let spawnError;
    closed = new Promise((resolve) => {
      gateway.once('close', resolve);
      gateway.once('error', (error) => { spawnError = error.code; resolve(); });
    });
    const deadline = Date.now() + 25000;
    while (Date.now() < deadline) {
      if (spawnError === 'ENOENT') return { state: 'missing' };
      if (gateway.exitCode !== null || spawnError) return { state: 'box_error' };
      const health = await fetch(origin + '/readyz', { signal: AbortSignal.timeout(1000) }).catch(() => null);
      await health?.body?.cancel();
      if (health?.ok) {
        const response = await fetch(origin + '/tools/invoke', {
          method: 'POST', redirect: 'error', signal: AbortSignal.timeout(8000),
          headers: { authorization: 'Bearer ' + token, 'content-type': 'application/json' },
          body: JSON.stringify({ tool: 'duckai_workspace', args: plan }),
        });
        const result = response.ok ? await response.json() : null;
        return result?.ok && result.result?.details ? result.result.details : { state: 'box_error' };
      }
      await delay(500);
    }
    return { state: 'unreachable' };
  } finally {
    if (gateway?.pid && gateway.exitCode === null) {
      gateway.kill('SIGTERM');
      await Promise.race([closed, delay(1500)]);
      if (gateway.exitCode === null && gateway.signalCode === null) gateway.kill('SIGKILL');
    }
    await fs.rm(state, { recursive: true, force: true });
  }
}

execute().then((result) => console.log(JSON.stringify(result)))
  .catch(() => console.log(JSON.stringify({ state: 'box_error' })));
"""


def workspace_command(plan):
    payload = json.dumps(plan, ensure_ascii=False).encode()
    return shlex.join(['timeout', '--kill-after=5s', '40s', 'node', '-e', GATEWAY_RUNNER,
                       base64.urlsafe_b64encode(payload).decode(),
                       base64.urlsafe_b64encode(WORKSPACE_TOOL.encode()).decode()])
