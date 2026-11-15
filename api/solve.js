// Authenticated Node counterpart of the repository's CLI challenge runner.
const crypto = require('crypto');
const { solveChallenge } = require('../jsa_jsdom');

module.exports = async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });
  const token = process.env.TELEGRAM_BOT_TOKEN || '';
  const expected = crypto.createHash('sha256').update(token + 'duckai-solver').digest('hex');
  const supplied = req.headers['x-duckai-solver'];
  if (!token || typeof supplied !== 'string' || !/^[a-f0-9]{64}$/.test(supplied) ||
      !crypto.timingSafeEqual(Buffer.from(supplied), Buffer.from(expected))) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  const { source, ua } = req.body || {};
  if (typeof source !== 'string' || source.length > 200000 ||
      (ua !== undefined && (typeof ua !== 'string' || ua.length > 1000))) {
    return res.status(400).json({ error: 'Invalid request' });
  }
  try {
    const result = await solveChallenge(source, ua);
    if (!result || !Array.isArray(result.client_hashes)) throw new Error('Invalid result');
    return res.status(200).json(result);
  } catch (_) {
    return res.status(502).json({ error: 'Challenge execution failed' });
  }
};
