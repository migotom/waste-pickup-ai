# Contributing

This integration is intentionally small and targeted to Gmina Działdowo waste pickup schedules.

Guidelines:

- Keep runtime dependencies at zero unless there is a strong reason.
- Prefer Home Assistant helpers and the Python standard library.
- Keep parser and scheduler behavior covered by unit tests.
- Do not commit local Home Assistant config, `.storage`, API keys, access tokens, image scans, or assistant workspace files.
- Keep user-facing strings translatable through `translations/` or the lightweight frontend translation map.

Run before opening a pull request:

```bash
python3 scripts/check_no_secrets.py
python3 -m unittest discover -s tests
python3 -m compileall custom_components tests scripts
node --check custom_components/waste_pickup_ai/frontend/waste-pickup-ai-panel.js
```
