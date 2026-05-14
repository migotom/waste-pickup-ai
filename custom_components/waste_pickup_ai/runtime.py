"""Home Assistant runtime for Waste Pickup AI."""

from __future__ import annotations

import base64
from collections.abc import Callable
from datetime import datetime
import logging
import mimetypes
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components import frontend
from homeassistant.components.http import KEY_HASS, HomeAssistantView, StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change

from .const import (
    CONF_ANNUAL_SCAN_REMINDER_TIME,
    CONF_EVENING_TIME,
    CONF_MORNING_TIME,
    CONF_NOTIFY_TARGETS,
    CONF_OPENAI_API_KEY,
    CONF_OPENAI_MODEL,
    DEFAULT_ANNUAL_SCAN_REMINDER_TIME,
    DEFAULT_EVENING_TIME,
    DEFAULT_MORNING_TIME,
    DEFAULT_OPENAI_MODEL,
    DOMAIN,
    MAX_IMAGE_BYTES,
    PANEL_COMPONENT_NAME,
    PANEL_MODULE_URL,
    PANEL_STATIC_URL,
    PANEL_URL_PATH,
    SERVICE_ACTIVATE_SCHEDULE,
    SERVICE_SCAN_IMAGE,
    SERVICE_SEND_TEST_NOTIFICATION,
    SERVICE_SET_CELL,
)
from .openai_client import OpenAIExtractionError, OpenAIWasteScheduleClient
from .schedule import (
    ScheduleValidationError,
    annual_scan_reminder_due,
    build_pickup_events,
    due_pickup_notifications,
    next_pickup,
    parse_time_value,
    schedule_status,
)
from .store import WastePickupStore

_LOGGER = logging.getLogger(__name__)

DATA_HTTP_REGISTERED = f"{DOMAIN}_http_registered"
DATA_SERVICES_REGISTERED = f"{DOMAIN}_services_registered"
DATA_PANEL_REGISTERED = f"{DOMAIN}_panel_registered"

ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

SCAN_IMAGE_SCHEMA = vol.Schema(
    {
        vol.Required("image_path"): cv.string,
        vol.Optional("year"): cv.positive_int,
    }
)

SET_CELL_SCHEMA = vol.Schema(
    {
        vol.Required("row_index"): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Required("month"): vol.Any(cv.positive_int, cv.string),
        vol.Required("value"): vol.Any(cv.string, [cv.positive_int], None),
    }
)

ACTIVATE_SCHEDULE_SCHEMA = vol.Schema({vol.Optional("year"): cv.positive_int})
SEND_TEST_NOTIFICATION_SCHEMA = vol.Schema({})


class WastePickupRuntime:
    """Stateful integration runtime for a single config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.store = WastePickupStore(hass)
        self._unsubs: list[CALLBACK_TYPE] = []
        self._update_listeners: list[Callable[[], None]] = []

    async def async_setup(self) -> None:
        """Load storage and start time listeners."""
        await self.store.async_load()
        for at_time in {
            self.morning_time,
            self.evening_time,
            self.annual_scan_reminder_time,
        }:
            self._register_time_listener(at_time)

    async def async_unload(self) -> None:
        """Unload runtime listeners."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        self._update_listeners.clear()

    @property
    def options(self) -> dict[str, Any]:
        """Merged config entry data and options."""
        return {**self.entry.data, **self.entry.options}

    @property
    def openai_api_key(self) -> str:
        """Configured OpenAI API key."""
        return str(self.options.get(CONF_OPENAI_API_KEY, ""))

    @property
    def openai_model(self) -> str:
        """Configured OpenAI model."""
        return str(self.options.get(CONF_OPENAI_MODEL) or DEFAULT_OPENAI_MODEL)

    @property
    def notify_targets(self) -> list[str]:
        """Configured notify service targets without the notify. prefix."""
        return parse_notify_targets(self.options.get(CONF_NOTIFY_TARGETS))

    @property
    def morning_time(self) -> Any:
        """Morning reminder time."""
        return parse_time_value(self.options.get(CONF_MORNING_TIME), DEFAULT_MORNING_TIME)

    @property
    def evening_time(self) -> Any:
        """Evening reminder time."""
        return parse_time_value(self.options.get(CONF_EVENING_TIME), DEFAULT_EVENING_TIME)

    @property
    def annual_scan_reminder_time(self) -> Any:
        """Annual scan reminder time."""
        return parse_time_value(
            self.options.get(CONF_ANNUAL_SCAN_REMINDER_TIME),
            DEFAULT_ANNUAL_SCAN_REMINDER_TIME,
        )

    @callback
    def async_add_update_listener(self, listener: Callable[[], None]) -> CALLBACK_TYPE:
        """Register an entity update listener."""
        self._update_listeners.append(listener)

        @callback
        def remove() -> None:
            if listener in self._update_listeners:
                self._update_listeners.remove(listener)

        return remove

    @callback
    def async_notify_updated(self) -> None:
        """Notify entities that stored data changed."""
        for listener in list(self._update_listeners):
            try:
                listener()
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Failed to update a Waste Pickup AI entity listener")

    async def async_scan_image_data_url(
        self,
        data_url: str,
        *,
        filename: str | None = None,
        fallback_year: int | None = None,
    ) -> dict[str, Any]:
        """Scan an image data URL with OpenAI and store the draft schedule."""
        _validate_image_data_url(data_url)
        if not self.openai_api_key:
            raise HomeAssistantError("Brakuje klucza OpenAI API w konfiguracji integracji.")

        session = async_get_clientsession(self.hass)
        client = OpenAIWasteScheduleClient(session, self.openai_api_key, self.openai_model)
        try:
            extracted = await client.extract_schedule(data_url)
        except OpenAIExtractionError as err:
            raise HomeAssistantError(str(err)) from err

        schedule = await self.store.async_set_draft(
            extracted,
            fallback_year=fallback_year,
            source={"filename": filename or "", "model": self.openai_model},
        )
        self.async_notify_updated()
        return schedule

    async def async_scan_image_path(self, image_path: str, fallback_year: int | None = None) -> dict[str, Any]:
        """Read an image path and scan it with OpenAI."""
        config_path = Path(self.hass.config.path()).resolve()
        path = Path(image_path)
        if not path.is_absolute():
            path = config_path / image_path
        path = path.resolve()
        if not path.is_relative_to(config_path):
            raise HomeAssistantError("Plik obrazu musi znajdować się w katalogu konfiguracji Home Assistanta.")
        if not path.exists() or not path.is_file():
            raise HomeAssistantError(f"Nie znaleziono pliku: {image_path}")
        data = await self.hass.async_add_executor_job(path.read_bytes)
        if len(data) > MAX_IMAGE_BYTES:
            raise HomeAssistantError("Plik obrazu jest za duży.")
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
            raise HomeAssistantError("Obsługiwane są tylko obrazy JPG, PNG i WebP.")
        data_url = f"data:{mime_type};base64,{base64.b64encode(data).decode('ascii')}"
        return await self.async_scan_image_data_url(
            data_url,
            filename=path.name,
            fallback_year=fallback_year,
        )

    async def async_set_cell(self, row_index: int, month: Any, value: Any) -> dict[str, Any]:
        """Update one draft cell."""
        schedule = await self.store.async_set_cell(row_index, month, value)
        self.async_notify_updated()
        return schedule

    async def async_activate(self, year: int | None = None) -> dict[str, Any]:
        """Activate the current draft schedule."""
        schedule = await self.store.async_activate(year)
        self.async_notify_updated()
        return schedule

    async def async_send_test_notification(self) -> None:
        """Send a notification test to configured targets."""
        await self._async_send_to_all_targets(
            title="Odpady",
            message="Test powiadomień harmonogramu odpadów.",
            tag="waste-pickup-ai-test",
        )

    async def async_handle_time(self, now: datetime) -> None:
        """Handle scheduled notification checks."""
        active_schedule = self.store.data.get("active_schedule")
        sent_keys = self.store.data.get("sent_notifications", {}).keys()
        targets = self.notify_targets

        due = due_pickup_notifications(
            active_schedule,
            now,
            self.morning_time,
            self.evening_time,
            targets or [""],
            sent_keys,
        )
        for item in due:
            event = item["event"]
            await self._async_send_notify(
                target=item["target"],
                title="Odpady",
                message=f"Jutro odbiór: {', '.join(event['categories'])}",
                tag=item["key"],
            )
            await self.store.async_mark_sent(item["key"])

        if annual_scan_reminder_due(now, self.annual_scan_reminder_time):
            for target in targets or [""]:
                key = f"annual-scan|{now.year}|{target}"
                if key in self.store.data.get("sent_notifications", {}):
                    continue
                await self._async_send_notify(
                    target=target,
                    title="Odpady",
                    message="Zeskanuj nowy harmonogram odbioru odpadów na ten rok.",
                    tag=key,
                )
                await self.store.async_mark_sent(key)

    def _register_time_listener(self, at_time: Any) -> None:
        @callback
        def _handle(now: datetime) -> None:
            self.hass.async_create_task(self.async_handle_time(now))

        self._unsubs.append(
            async_track_time_change(
                self.hass,
                _handle,
                hour=at_time.hour,
                minute=at_time.minute,
                second=0,
            )
        )

    async def _async_send_to_all_targets(self, title: str, message: str, tag: str) -> None:
        for target in self.notify_targets or [""]:
            await self._async_send_notify(target=target, title=title, message=message, tag=tag)

    async def _async_send_notify(self, target: str, title: str, message: str, tag: str) -> None:
        if target:
            await self.hass.services.async_call(
                "notify",
                target,
                {
                    "title": title,
                    "message": message,
                    "data": {
                        "tag": tag,
                        "group": "waste_pickup_ai",
                        "url": f"/{PANEL_URL_PATH}",
                    },
                },
                blocking=False,
            )
            return

        await self.hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": title,
                "message": message,
                "notification_id": tag,
            },
            blocking=False,
        )


async def async_register_runtime_hass_bits(hass: HomeAssistant) -> None:
    """Register services, HTTP API, and frontend panel once."""
    await _async_register_http(hass)
    await _async_register_panel(hass)
    _async_register_services(hass)


def get_runtime(hass: HomeAssistant) -> WastePickupRuntime:
    """Return the configured runtime."""
    runtimes = hass.data.get(DOMAIN, {})
    if not runtimes:
        raise HomeAssistantError("Waste Pickup AI is not configured.")
    return next(iter(runtimes.values()))


def parse_notify_targets(value: Any) -> list[str]:
    """Parse notify targets from config flow input."""
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = re_split_targets(value)
    elif isinstance(value, list):
        raw_items = [str(item) for item in value]
    else:
        raw_items = [str(value)]

    targets = []
    for item in raw_items:
        target = item.strip()
        if not target:
            continue
        if target.startswith("notify."):
            target = target.removeprefix("notify.")
        targets.append(target)
    return targets


def re_split_targets(value: str) -> list[str]:
    """Split a comma/newline separated target list."""
    return [item for chunk in value.splitlines() for item in chunk.split(",")]


async def _async_register_http(hass: HomeAssistant) -> None:
    if hass.data.get(DATA_HTTP_REGISTERED):
        return
    hass.http.register_view(WastePickupScheduleView())
    hass.http.register_view(WastePickupScanView())
    hass.http.register_view(WastePickupCellView())
    hass.http.register_view(WastePickupActivateView())
    hass.http.register_view(WastePickupTestNotificationView())
    frontend_dir = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(PANEL_STATIC_URL, str(frontend_dir), False)]
    )
    hass.data[DATA_HTTP_REGISTERED] = True


async def _async_register_panel(hass: HomeAssistant) -> None:
    if hass.data.get(DATA_PANEL_REGISTERED):
        return
    frontend.async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title="Odpady Działdowo",
        sidebar_icon="mdi:trash-can-outline",
        frontend_url_path=PANEL_URL_PATH,
        config={
            "_panel_custom": {
                "name": PANEL_COMPONENT_NAME,
                "embed_iframe": False,
                "trust_external": False,
                "module_url": PANEL_MODULE_URL,
            }
        },
        require_admin=True,
        config_panel_domain=DOMAIN,
    )
    hass.data[DATA_PANEL_REGISTERED] = True


def _async_register_services(hass: HomeAssistant) -> None:
    if hass.data.get(DATA_SERVICES_REGISTERED):
        return

    async def _scan_image(call: ServiceCall) -> None:
        runtime = get_runtime(hass)
        await runtime.async_scan_image_path(call.data["image_path"], call.data.get("year"))

    async def _set_cell(call: ServiceCall) -> None:
        runtime = get_runtime(hass)
        await runtime.async_set_cell(
            call.data["row_index"],
            call.data["month"],
            call.data.get("value"),
        )

    async def _activate(call: ServiceCall) -> None:
        runtime = get_runtime(hass)
        await runtime.async_activate(call.data.get("year"))

    async def _send_test_notification(_: ServiceCall) -> None:
        runtime = get_runtime(hass)
        await runtime.async_send_test_notification()

    hass.services.async_register(DOMAIN, SERVICE_SCAN_IMAGE, _scan_image, schema=SCAN_IMAGE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SET_CELL, _set_cell, schema=SET_CELL_SCHEMA)
    hass.services.async_register(
        DOMAIN,
        SERVICE_ACTIVATE_SCHEDULE,
        _activate,
        schema=ACTIVATE_SCHEDULE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_TEST_NOTIFICATION,
        _send_test_notification,
        schema=SEND_TEST_NOTIFICATION_SCHEMA,
    )
    hass.data[DATA_SERVICES_REGISTERED] = True


class WastePickupScheduleView(HomeAssistantView):
    """Return the current schedule state."""

    url = f"/api/{DOMAIN}/schedule"
    name = f"api:{DOMAIN}:schedule"
    requires_admin = True

    async def get(self, request: Any) -> Any:
        runtime = get_runtime(request.app[KEY_HASS])
        active_schedule = runtime.store.data.get("active_schedule")
        draft_schedule = runtime.store.data.get("draft_schedule")
        return self.json(
            {
                "draft_schedule": draft_schedule,
                "active_schedule": active_schedule,
                "status": schedule_status(active_schedule),
                "next_pickup": next_pickup(active_schedule),
                "events": build_pickup_events(active_schedule),
                "options": {
                    "notify_targets": runtime.notify_targets,
                    "morning_time": runtime.morning_time.strftime("%H:%M"),
                    "evening_time": runtime.evening_time.strftime("%H:%M"),
                    "annual_scan_reminder_time": runtime.annual_scan_reminder_time.strftime("%H:%M"),
                    "model": runtime.openai_model,
                },
            }
        )


class WastePickupScanView(HomeAssistantView):
    """Scan an uploaded image data URL."""

    url = f"/api/{DOMAIN}/scan"
    name = f"api:{DOMAIN}:scan"
    requires_admin = True

    async def post(self, request: Any) -> Any:
        runtime = get_runtime(request.app[KEY_HASS])
        try:
            payload = await request.json()
            data_url = payload["data_url"]
            filename = payload.get("filename")
            year = payload.get("year")
            schedule = await runtime.async_scan_image_data_url(
                data_url,
                filename=filename,
                fallback_year=year,
            )
        except (KeyError, ValueError, HomeAssistantError) as err:
            return self.json_message(str(err), status_code=400)
        return self.json({"draft_schedule": schedule})


class WastePickupCellView(HomeAssistantView):
    """Update one editable table cell."""

    url = f"/api/{DOMAIN}/cell"
    name = f"api:{DOMAIN}:cell"
    requires_admin = True

    async def post(self, request: Any) -> Any:
        runtime = get_runtime(request.app[KEY_HASS])
        try:
            payload = await request.json()
            schedule = await runtime.async_set_cell(
                int(payload["row_index"]),
                payload["month"],
                payload.get("value"),
            )
        except (KeyError, ValueError, IndexError, ScheduleValidationError) as err:
            return self.json_message(str(err), status_code=400)
        return self.json({"draft_schedule": schedule})


class WastePickupActivateView(HomeAssistantView):
    """Activate the current draft schedule."""

    url = f"/api/{DOMAIN}/activate"
    name = f"api:{DOMAIN}:activate"
    requires_admin = True

    async def post(self, request: Any) -> Any:
        runtime = get_runtime(request.app[KEY_HASS])
        try:
            payload = await request.json()
            schedule = await runtime.async_activate(payload.get("year"))
        except (ValueError, ScheduleValidationError) as err:
            return self.json_message(str(err), status_code=400)
        return self.json({"active_schedule": schedule, "events": build_pickup_events(schedule)})


class WastePickupTestNotificationView(HomeAssistantView):
    """Send a test notification."""

    url = f"/api/{DOMAIN}/test_notification"
    name = f"api:{DOMAIN}:test_notification"
    requires_admin = True

    async def post(self, request: Any) -> Any:
        runtime = get_runtime(request.app[KEY_HASS])
        await runtime.async_send_test_notification()
        return self.json({"ok": True})


def _validate_image_data_url(data_url: str) -> None:
    if not isinstance(data_url, str) or not data_url.startswith("data:image/"):
        raise HomeAssistantError("Niepoprawny obraz. Oczekiwany data URL JPG, PNG lub WebP.")
    header, _, encoded = data_url.partition(",")
    mime_type = header.removeprefix("data:").split(";", 1)[0]
    if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise HomeAssistantError("Obsługiwane są tylko obrazy JPG, PNG i WebP.")
    estimated_size = int(len(encoded) * 0.75)
    if estimated_size > MAX_IMAGE_BYTES:
        raise HomeAssistantError("Plik obrazu jest za duży.")
