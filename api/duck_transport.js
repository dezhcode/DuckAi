// Node transport port of DuckAiChat's session/handshake flow.
// Upstream protocol reference: reference/duck-protocol.ts (MIT).
const crypto = require('crypto');
const { solveChallenge } = require('../jsa_jsdom');
const BASE = 'https://duck.ai';
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36';
const state = { feVersion: '', jsa: '', cookies: new Map() };
let inFlightHandshake = null;
const b64 = x => Buffer.from(JSON.stringify(x)).toString('base64');
function cookies(headers) {
  const values = typeof headers.getSetCookie === 'function' ? headers.getSetCookie() : [headers.get('set-cookie')].filter(Boolean);
  for (const value of values) {
    const first = value.split(';')[0], idx = first.indexOf('=');
    if (idx > 0) state.cookies.set(first.slice(0, idx).trim(), first.slice(idx + 1).trim());
  }
}
function cookieHeader() { return [...state.cookies].map(([k,v]) => k + '=' + v).join('; '); }
function proof(solved) {
  const p = { ...solved };
  p.client_hashes = (solved.client_hashes || []).map(x => crypto.createHash('sha256').update(x).digest('base64'));
  p.meta = { ...(solved.meta || {}), origin: BASE,
    stack: 'Error\nat l (https://duck.ai/dist/duckai-dist/entry.duckai.js:2:2129171)\nat async https://duck.ai/dist/duckai-dist/entry.duckai.js:2:1859809',
    duration: '58' };
  return b64(p);
}
async function solve(raw) {
  const solved = await solveChallenge(Buffer.from(raw, 'base64').toString('utf8'), UA);
  if (!solved || !Array.isArray(solved.client_hashes)) throw Error('Invalid challenge');
  return proof(solved);
}
async function handshake() {
  if (inFlightHandshake) return inFlightHandshake;
  inFlightHandshake = (async () => {
    const headers = { 'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9' };
    const boot = await fetch(BASE + '/', { headers, signal: AbortSignal.timeout(15000) });
    if (!boot.ok) throw Error('Bootstrap HTTP ' + boot.status);
    console.info('transport_bootstrap', JSON.stringify({status:boot.status, cookiesBefore:state.cookies.size}));
    cookies(boot.headers);
    const html = await boot.text();
    state.feVersion = (html.match(/data-version-tag="([^"]*)"/)?.[1] || 'dev') + '-' +
      (html.match(/data-version-sha="([^"]*)"/)?.[1] || 'hash');
    const status = await fetch(BASE + '/duckchat/v1/status', { headers: {
      ...headers, 'x-vqd-accept': '1', 'Cache-Control': 'no-store',
      'x-fe-version': state.feVersion, Origin: BASE, Referer: BASE + '/',
      ...(cookieHeader() ? { Cookie: cookieHeader() } : {}) },
      signal: AbortSignal.timeout(15000) });
    cookies(status.headers);
    const raw = status.headers.get('x-vqd-hash-1');
    console.info('transport_status', JSON.stringify({status:status.status, challengePresent:!!raw, cookies:state.cookies.size, feVersionPresent:!!state.feVersion}));
    if (!raw) throw Error('Challenge HTTP ' + status.status);
    state.jsa = await solve(raw);
    console.info('transport_handshake_complete', JSON.stringify({proofPresent:!!state.jsa, cookies:state.cookies.size}));
  })();
  try { await inFlightHandshake; } finally { inFlightHandshake = null; }
}
function parse(line) {
  if (!line.startsWith('data: ')) return null;
  const raw = line.slice(6).trim();
  if (!raw || raw.startsWith('[')) return null;
  let ev; try { ev = JSON.parse(raw); } catch { return null; }
  if (ev.action === 'error') return { kind: 'error', value: 'Upstream stream error' };
  if (typeof ev.message === 'string' && ev.message) return { kind: 'message', value: ev.message };
  if (ev.role === 'tool-invocation') return { kind: 'tool', value: { toolName: ev.toolName, state: ev.state, toolArguments: ev.toolArguments } };
  if (ev.role === 'ui-component' && ev.name === 'generate-image') {
    const d = ev.data || {};
    if (d.type === 'image-title') return { kind: 'image_title', value: String(d.title || '') };
    if (d.type === 'image-partial' || d.status === 'partial') return { kind: 'image_partial', value: d };
    if (d.status === 'success' && d.b64Image) return { kind: 'image', value: { b64: d.b64Image, width: d.width, height: d.height, format: d.format || 'jpeg' } };
  }
  return null;
}
async function chat(body) {
  let lastStatus = 502;
  for (let attempt = 0; attempt < 2; attempt++) {
    if (attempt || !state.feVersion || !state.jsa) await handshake();
    const model = body.model || 'gpt-6-luna';
    const payload = { model,
      messages: [...(Array.isArray(body.history) ? body.history : []),
        { role: 'user', content: [{ type: 'text', text: (body.prompt || '') + (body.prompt_extra || '') }, ...(body.images || [])] }],
      canUseTools: model !== 'mistral-small-2603',
      reasoningEffort: model === 'tinfoil/gpt-oss-120b' ? 'low' : 'none',
      canUseApproxLocation: null, canDelegateImageGeneration: null, canShowGreeting: false };
    if (body.draw) payload.metadata = { toolChoice: { GenerateImage: true } };
    const response = await fetch(BASE + '/duckchat/v1/chat', { method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream', Origin: BASE,
        Referer: BASE + '/', 'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9',
        'x-fe-version': state.feVersion,
        'x-fe-signals': b64({ start: Date.now(), events: [{ name: 'action', delta: 1200, trusted: true }], end: 1500 }),
        'X-Vqd-Hash-1': state.jsa, ...(cookieHeader() ? { Cookie: cookieHeader() } : {}) },
      body: JSON.stringify(payload), signal: AbortSignal.timeout(45000) });
    cookies(response.headers);
    const next = response.headers.get('x-vqd-hash-1');
    if (next) { try { state.jsa = await solve(next); } catch { state.jsa = ''; } }
    console.info('transport_chat_status', JSON.stringify({attempt:attempt+1, status:response.status, responseChallenge:!!next, proofPresent:!!state.jsa, cookies:state.cookies.size, historyCount:Array.isArray(body.history)?body.history.length:0}));
    if (response.status === 200 && response.body) {
      const events = [], reader = response.body.getReader(), decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { value, done } = await reader.read(); if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n'); buffer = lines.pop();
        for (const line of lines) { const ev = parse(line.trim()); if (ev) events.push(ev); }
      }
      if (buffer) { const ev = parse(buffer.trim()); if (ev) events.push(ev); }
      if (events.some(e => e.kind === 'error')) return { ok: false, status: 502, code: 'STREAM_ERROR' };
      return { ok: true, events };
    }
    lastStatus = response.status;
    await response.body?.cancel().catch(() => {});
    if (!next) state.jsa = '';
    if ([418, 429, 401, 403].includes(lastStatus)) break;
    if (attempt < 1) await new Promise(resolve => setTimeout(resolve, (attempt + 1) * 1000));
  }
  return { ok: false, status: lastStatus, code: lastStatus === 418 ? 'ERR_CHALLENGE' : 'UPSTREAM_ERROR' };
}
module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });
  const token = process.env.TELEGRAM_BOT_TOKEN || '';
  const expected = crypto.createHash('sha256').update(token + 'duckai-transport').digest('hex');
  const supplied = req.headers['x-duckai-transport'];
  if (!token || typeof supplied !== 'string' || supplied.length !== expected.length ||
      !crypto.timingSafeEqual(Buffer.from(supplied), Buffer.from(expected))) return res.status(401).json({ error: 'Unauthorized' });
  try {
    const result = await chat(req.body || {});
    return res.status(result.ok ? 200 : 502).json(result);
  } catch (err) {
    console.error('duckai_transport_failure', err?.name || 'Error');
    return res.status(502).json({ ok: false, status: 502, code: 'TRANSPORT_ERROR' });
  }
};
