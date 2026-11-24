const assert = require('node:assert/strict');
const { test } = require('node:test');
const { buildChatRequestBody, readChatResult } = require('../reference/duck-chat');

test('DuckAiChat model aliases retain the correct tools and reasoning settings', () => {
  const conversation = { prompt: 'سلام', history: [], images: [] };
  const mistral = buildChatRequestBody({ ...conversation, model: ' MISTRAL ' });
  assert.equal(mistral.model, 'mistral-small-2603');
  assert.equal(mistral.canUseTools, false);

  const oss = buildChatRequestBody({ ...conversation, model: 'gpt-oss', tools: false });
  assert.equal(oss.model, 'tinfoil/gpt-oss-120b');
  assert.equal(oss.reasoningEffort, 'low');
  assert.equal(oss.canUseTools, false);
});

test('SSE reader preserves Persian text split across UTF-8 chunks and trailing image events', async () => {
  const text = Buffer.from('data: {"message":"سلام"}\r\n');
  const splitAt = text.indexOf(Buffer.from('س')) + 1;
  const image = Buffer.from('data: {"role":"ui-component","name":"generate-image","data":{"status":"success","b64Image":"abcd"}}');
  const result = await readChatResult(ReadableStream.from([text.subarray(0, splitAt), text.subarray(splitAt), image]));
  assert.equal(result.ok, true);
  assert.deepEqual(result.events.map(event => event.kind), ['message', 'image']);
  assert.equal(result.events[0].value, 'سلام');
  assert.equal(result.events[1].value.b64, 'abcd');
});

test('SSE reader surfaces the Duck.ai limit code from a final error event', async () => {
  const stream = ReadableStream.from([Buffer.from('data: {"action":"error","type":"ERR_BN_LIMIT","status":418}')]);
  assert.deepEqual(await readChatResult(stream), { ok: false, status: 418, code: 'ERR_BN_LIMIT' });
});
