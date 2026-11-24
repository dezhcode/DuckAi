// Text, image, and tool protocol adapted from DarkBytee/DuckAiChat,
// commit 588b43b1853dc0e44de2b10756703e2db783bc86, lib/duck-protocol.ts.
// Copyright (c) 2026 DuckAI Chat Studio Contributors. See LICENSE.duckaichat.

const MODEL_ALIASES = new Map([
  ['luna', 'gpt-6-luna'],
  ['mini', 'gpt-5.4-mini'],
  ['nano', 'gpt-5.4-nano'],
  ['haiku-5.5', 'claude-haiku-5-5'],
  ['haiku', 'claude-haiku-4-5'],
  ['gemma', 'tinfoil/gemma4-31b'],
  ['gemma4-31b', 'tinfoil/gemma4-31b'],
  ['gpt-oss', 'tinfoil/gpt-oss-120b'],
  ['gpt-oss-120b', 'tinfoil/gpt-oss-120b'],
  ['mistral', 'mistral-small-2603'],
]);
for (const id of [...MODEL_ALIASES.values(), 'gpt-5.6-luna']) {
  MODEL_ALIASES.set(id, id);
}

function buildChatRequestBody({ prompt, model, tools, history, images, draw, promptExtra }) {
  const name = typeof model === 'string' ? model.trim() : '';
  const resolvedModel = MODEL_ALIASES.get(name.toLowerCase()) || name || 'gpt-6-luna';
  const content = [{ type: 'text', text: prompt + (promptExtra ?? '') }, ...images];
  const body = {
    model: resolvedModel,
    messages: [...history, { role: 'user', content }],
    canUseTools: resolvedModel === 'mistral-small-2603' ? false : (tools ?? true),
    reasoningEffort: resolvedModel === 'tinfoil/gpt-oss-120b' ? 'low' : 'none',
    canUseApproxLocation: null,
    canDelegateImageGeneration: null,
    canShowGreeting: false,
  };
  if (draw) body.metadata = { toolChoice: { GenerateImage: true } };
  return body;
}

function parseSseLine(rawLine) {
  const line = rawLine.trim();
  if (!line.startsWith('data: ')) return null;
  const payload = line.slice(6).trim();
  if (!payload || payload.startsWith('[')) return null;

  let event;
  try {
    event = JSON.parse(payload);
  } catch {
    return null;
  }
  if (!event || typeof event !== 'object') return null;

  if (event.action === 'error') {
    const status = Number(event.status);
    return {
      kind: 'error',
      status: Number.isInteger(status) && status >= 400 && status <= 599 ? status : 502,
      code: event.type === 'ERR_BN_LIMIT' ? event.type : 'STREAM_ERROR',
    };
  }
  if (typeof event.message === 'string' && event.message.length > 0) {
    return { kind: 'message', value: event.message };
  }
  if (event.role === 'ui-component' && event.name === 'generate-image') {
    const data = event.data || {};
    if (data.type === 'image-title') {
      return { kind: 'image_title', value: String(data.title || '') };
    }
    if (data.type === 'image-partial' || data.status === 'partial') {
      return { kind: 'image_partial', value: data };
    }
    if (data.status === 'success' && data.b64Image) {
      return {
        kind: 'image',
        value: {
          b64: String(data.b64Image),
          width: data.width,
          height: data.height,
          format: data.format || 'jpeg',
        },
      };
    }
  }
  if (event.role === 'tool-invocation') {
    return {
      kind: 'tool',
      value: {
        toolName: event.toolName,
        state: event.state,
        toolArguments: event.toolArguments,
      },
    };
  }
  return null;
}

async function readChatResult(stream) {
  const events = [];
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      for (const line of lines) {
        const event = parseSseLine(line);
        if (event) events.push(event);
      }
    }
  } finally {
    reader.releaseLock();
  }

  const finalEvent = parseSseLine(buffer + decoder.decode());
  if (finalEvent) events.push(finalEvent);
  const error = events.find(event => event.kind === 'error');
  if (error) return { ok: false, status: error.status, code: error.code };
  return { ok: true, events };
}

module.exports = { buildChatRequestBody, readChatResult };
