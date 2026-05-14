# Security

## Secrets

Do not commit OpenAI API keys, Home Assistant tokens, `.storage` files, `.env` files, private keys, or local assistant files.

The repository includes:

- `.gitignore` entries for common Home Assistant and AI-secret files,
- `scripts/check_no_secrets.py` for local and CI checks.

## Data Sent To OpenAI

Only the uploaded waste schedule image is sent to OpenAI, and only when a Home Assistant admin explicitly starts a scan. The integration does not send Home Assistant entity state, user credentials, or notification targets to OpenAI.

## Reporting Issues

Use the GitHub issue tracker configured in `manifest.json` for security or privacy reports until a dedicated private disclosure channel is added.
