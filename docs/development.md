# Development

This repository is structured as a HACS-compatible Home Assistant custom integration:

```text
custom_components/waste_pickup_ai/
```

Home Assistant loads custom integrations from the configuration directory under `custom_components/<domain>`. During development, prefer one of these workflows:

1. Run a disposable Home Assistant Core development environment and mount or copy this repository's `custom_components/waste_pickup_ai` into its config directory.
2. Publish a public GitHub branch and install it through HACS as a custom repository on a test Home Assistant instance.

Avoid using Samba as the normal development or installation mechanism. It is useful for emergency file inspection, but HACS gives users a repeatable install and update path.

## Local Validation

```bash
python3 scripts/check_no_secrets.py
python3 -m unittest discover -s tests
python3 -m compileall custom_components tests scripts
node --check custom_components/waste_pickup_ai/frontend/waste-pickup-ai-panel.js
```

The test suite intentionally keeps parser and scheduling logic free of Home Assistant runtime dependencies, so the core behavior can be tested without a full HA environment.

## Compatibility Target

The integration targets Home Assistant `2025.5.0` or newer.

When raising the minimum version:

1. Update `hacs.json`.
2. Update `custom_components/waste_pickup_ai/const.py`.
3. Update the README compatibility section.
4. Bump the integration `version` in `manifest.json`.

## Dependency Policy

The integration has no pip requirements. Use Home Assistant helpers and the Python standard library where possible.

The OpenAI call is made through Home Assistant's shared aiohttp client session.

## Internationalization

Custom integration translations live in:

```text
custom_components/waste_pickup_ai/translations/
```

Do not use `strings.json` for this custom integration. Add new language files as `<language>.json`.
