# Publishing

## Current Target

The first public distribution target is HACS as a custom repository. After real-world testing, the repository can be submitted to the HACS default catalog.

## Before First Public Release

1. Confirm the final GitHub owner and repository name.
2. Update these metadata values if the repository is not published as `migotom/waste-pickup-ai`:
   - `custom_components/waste_pickup_ai/manifest.json`
   - `.github/CODEOWNERS`
3. Enable GitHub issues.
4. Add repository description and topics:
   - `home-assistant`
   - `hacs`
   - `custom-integration`
   - `waste-management`
   - `dzialdowo`
5. Run all local checks.
6. Confirm `hacs.json` and `MIN_HOME_ASSISTANT_VERSION` still match.
7. Push to GitHub.
8. Confirm GitHub Actions pass:
   - local validation
   - HACS validation
   - Hassfest
9. Create a GitHub release, for example `v0.1.0`.

## HACS Custom Repository Install

Users can add the public GitHub URL in HACS:

```text
HACS -> Custom repositories -> URL -> Integration -> Add
```

## HACS Default Catalog

For default HACS inclusion, the repository must remain public and hosted on GitHub. It should have:

- valid HACS repository structure,
- `hacs.json`,
- valid Home Assistant manifest,
- brand icon,
- passing HACS Action,
- passing Hassfest,
- at least one GitHub release,
- repository description, topics, and issues enabled.
