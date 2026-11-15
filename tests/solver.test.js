const assert = require('node:assert/strict');
const test = require('node:test');
const crypto = require('crypto');
const handler = require('../api/solve');
function response() {
  return { code: null, body: null, setHeader() {}, status(code) { this.code = code; return this; }, json(body) { this.body = body; return this; } };
}
test('solver rejects unauthenticated calls', async () => {
  const res = response();
  await handler({ method: 'POST', headers: {}, body: { source: 'invalid' } }, res);
  assert.equal(res.code, 401);
});
test('solver runs the same shared CLI runner for authenticated requests', async () => {
  process.env.TELEGRAM_BOT_TOKEN = 'test-only';
  const secret = crypto.createHash('sha256').update('test-onlyduckai-solver').digest('hex');
  const res = response();
  await handler({ method: 'POST', headers: { 'x-duckai-solver': secret },
    body: { source: 'Promise.resolve({client_hashes: ["fixture"], server_hashes: []})' } }, res);
  assert.equal(res.code, 200);
  assert.deepEqual(Array.from(res.body.client_hashes), ['fixture']);
});
