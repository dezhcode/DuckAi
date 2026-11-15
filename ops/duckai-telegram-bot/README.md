# Telegram bot deployment repair

Historical packaging-only repair. The current vision/image-generation adapter and deployment instructions are in `TELEGRAM.md`. The cached-source manifest below restores the older text-only bot and is retained for rollback, not for releasing the current adapter.

Reviewed on 2026-11-15. Vercel project: `duckai-telegram-bot`.

## Confirmed deployment failure

The production deployment `dpl_GyXQF9ybZwR7awSYYYrXVPFdoDNV` has source files nested under an extra `src/` directory. Its build logs report a 32 ms build with no prepared output files, and `/api/webhook` returns HTTP 404. The latest preview (`dpl_A32SzA6NkcLpXhScJyjh8NKVyfCC`) has a different, newer bot implementation; it is not the production source.

`repair-preview.json` is a Vercel Create Deployment request body that relocates the existing production files to the project root. The source hashes reference existing files already uploaded to this Vercel account. It adds a small landing page and `Cache-Control: no-store` for API responses. It intentionally omits `target` so it creates a preview.

The original `api/setup.py` is excluded: its unauthenticated GET handler calls Telegram `setWebhook`, allowing any visitor to change operational configuration. Configure the webhook only through an authenticated administrative procedure.

This manifest reuses the original production bot source. The Python client fixes in this PR are separate and are not included in these cached source hashes. Do not overwrite the deployed Python client with the CLI file without porting the bot's remote-solver integration.

## Verified result

Repair preview: https://duckai-telegram-5cbrq1sjy-98benyamins-projects.vercel.app

- Build: READY (`dpl_3QxejH9cZYWsDq3gwqWkoceMgdxy`).
- `/api/webhook`: HTTP 200, JSON health response, `Cache-Control: no-store`.
- `/`: HTTP 200.
- `/api/setup`: HTTP 404, as intended.
- Recent error/fatal runtime-log query: no matching records.

No Telegram messages, AI chat requests, image generation, or transcription were sent during verification. End-to-end bot responses and durable conversation state remain unverified. The Vercel source connector truncates long source files, and the dashboard browser requires sign-in; a complete review of the deployed webhook implementation remains pending access to its full source.

## Release status

Production is unchanged. Automatic approval review rejected a production deployment because explicit approval to change the live service was missing. Obtain that approval before releasing. Reuse the verified file manifest, choose the production target explicitly, and verify the canonical domain after deployment. Do not call the removed public setup endpoint.

Keep source hashes and the prior deployment ID for rollback. This repair does not change bot credentials, register a new webhook, or promote the newer feature preview.

## Client regression checks

Run from the repository root:

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

The regression suite covers source-file attachments, bounded reads, WebP validation without Pillow, encoded image-size limits, response cleanup, and retry behavior. It uses mocked HTTP responses and does not contact Duck.ai or Telegram.
