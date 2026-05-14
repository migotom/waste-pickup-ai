# Działdowo Waste Pickup AI

Home Assistant custom integration for annual municipal waste pickup schedules used by **Gmina Działdowo, Poland**.

This is not intended to be a generic worldwide waste-management integration. It is built for the yearly table-style schedules used locally in Gmina Działdowo, with enough internal structure to add translations and adapt parsing rules later if needed.

## Features

- Upload a yearly JPG, PNG, or WebP schedule image from a Home Assistant panel.
- Extract table data with OpenAI Responses API and structured JSON output.
- Verify and correct the interpreted month/day table before activation.
- Create `calendar.waste_pickups` with all-day pickup events.
- Create `sensor.waste_next_pickup`, `sensor.waste_category_pickups`, per-category pickup sensors,
  and `sensor.waste_schedule_status`.
- Send reminders one day before pickup in the morning and evening.
- Exclude `Popiol` / `Popiół` from reminder notifications.
- Remind the user on January 1 to scan the new yearly schedule.
- Support Home Assistant mobile notify services such as `notify.mobile_app_iphone`.

## Privacy

The integration sends an image to OpenAI only when an admin explicitly scans a schedule. It does not run background OCR and does not send Home Assistant entity data to OpenAI.

The OpenAI API key is configured inside Home Assistant and must never be committed to this repository. The repository includes a local secret scanner and `.gitignore` rules for common Home Assistant and AI-secret files.

## Installation With HACS

Until this repository is accepted into the HACS default catalog, install it as a custom repository:

1. In Home Assistant, open HACS.
2. Open the menu and select **Custom repositories**.
3. Add the public GitHub repository URL.
4. Select repository type **Integration**.
5. Install **Działdowo Waste Pickup AI**.
6. Restart Home Assistant.
7. Add the integration from **Settings -> Devices & services**.

HACS installs the integration under the Home Assistant configuration directory at `custom_components/waste_pickup_ai`.

## Compatibility

Supported Home Assistant versions:

- `2025.5.0` or newer.

This target is chosen to keep compatibility at least one year back from the current Home Assistant `2026.5` release line. HACS reads the minimum version from `hacs.json`, and the integration also refuses setup on older manually installed Home Assistant versions.

## Configuration

Required:

- OpenAI API key.

Optional:

- OpenAI model, default `gpt-5.5`.
- Notification targets selected from available `notify.*` services, for example `notify.mobile_app_iphone`.
- Morning reminder time, default `08:00`.
- Evening reminder time, default `20:00`.
- January 1 scan reminder time, default `09:00`.

If no notify service is configured, reminders use Home Assistant persistent notifications.

## Dashboard Entities

After activating a schedule, the integration creates category-specific sensors such as `sensor.odpady_papier`.
Their state is the number of days until the next pickup, with attributes for the exact date and remaining
future dates. `sensor.waste_category_pickups` also exposes a full `pickups` attribute for cards/templates that
need all categories in one entity.

## Development Checks

Run from the repository root:

```bash
python3 scripts/check_no_secrets.py
python3 -m unittest discover -s tests
python3 -m compileall custom_components tests scripts
node --check custom_components/waste_pickup_ai/frontend/waste-pickup-ai-panel.js
```

See [docs/development.md](docs/development.md) and [docs/publishing.md](docs/publishing.md).
