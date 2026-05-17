"""Config flow for Waste Pickup AI."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import (
    CONF_ANNUAL_SCAN_REMINDER_TIME,
    CONF_EVENING_TIME,
    CONF_MORNING_TIME,
    CONF_NOTIFICATION_CHANNEL,
    CONF_NOTIFICATION_CRITICAL,
    CONF_NOTIFICATION_SOUND_IOS,
    CONF_NOTIFICATION_STICKY,
    CONF_NOTIFY_TARGETS,
    CONF_OPENAI_API_KEY,
    CONF_OPENAI_MODEL,
    DEFAULT_ANNUAL_SCAN_REMINDER_TIME,
    DEFAULT_EVENING_TIME,
    DEFAULT_MORNING_TIME,
    DEFAULT_NOTIFICATION_CHANNEL,
    DEFAULT_NOTIFICATION_CRITICAL,
    DEFAULT_NOTIFICATION_SOUND_IOS,
    DEFAULT_NOTIFICATION_STICKY,
    DEFAULT_OPENAI_MODEL,
    DOMAIN,
)
from .schedule import parse_time_value


class WastePickupAIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Waste Pickup AI."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> Any:
        """Handle the initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_input(user_input)
            if not errors:
                return self.async_create_entry(
                    title="Działdowo Waste Pickup AI",
                    data={
                        CONF_OPENAI_API_KEY: user_input[CONF_OPENAI_API_KEY],
                        CONF_OPENAI_MODEL: user_input.get(CONF_OPENAI_MODEL) or DEFAULT_OPENAI_MODEL,
                        CONF_NOTIFY_TARGETS: _normalize_notify_targets_input(
                            user_input.get(CONF_NOTIFY_TARGETS)
                        ),
                        CONF_MORNING_TIME: user_input.get(CONF_MORNING_TIME) or DEFAULT_MORNING_TIME,
                        CONF_EVENING_TIME: user_input.get(CONF_EVENING_TIME) or DEFAULT_EVENING_TIME,
                        CONF_ANNUAL_SCAN_REMINDER_TIME: user_input.get(
                            CONF_ANNUAL_SCAN_REMINDER_TIME
                        )
                        or DEFAULT_ANNUAL_SCAN_REMINDER_TIME,
                        CONF_NOTIFICATION_CHANNEL: (
                            user_input.get(CONF_NOTIFICATION_CHANNEL)
                            or DEFAULT_NOTIFICATION_CHANNEL
                        ),
                        CONF_NOTIFICATION_STICKY: bool(
                            user_input.get(CONF_NOTIFICATION_STICKY, DEFAULT_NOTIFICATION_STICKY)
                        ),
                        CONF_NOTIFICATION_SOUND_IOS: (
                            user_input.get(CONF_NOTIFICATION_SOUND_IOS)
                            or DEFAULT_NOTIFICATION_SOUND_IOS
                        ),
                        CONF_NOTIFICATION_CRITICAL: bool(
                            user_input.get(
                                CONF_NOTIFICATION_CRITICAL, DEFAULT_NOTIFICATION_CRITICAL
                            )
                        ),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(self.hass, user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return WastePickupAIOptionsFlow(config_entry)


class WastePickupAIOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Waste Pickup AI."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> Any:
        """Manage integration options."""
        current = {**self._config_entry.data, **self._config_entry.options}
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_input(user_input)
            if not errors:
                return self.async_create_entry(
                    title="",
                    data={
                        **user_input,
                        CONF_NOTIFY_TARGETS: _normalize_notify_targets_input(
                            user_input.get(CONF_NOTIFY_TARGETS)
                        ),
                        CONF_NOTIFICATION_STICKY: bool(
                            user_input.get(CONF_NOTIFICATION_STICKY, DEFAULT_NOTIFICATION_STICKY)
                        ),
                        CONF_NOTIFICATION_CRITICAL: bool(
                            user_input.get(
                                CONF_NOTIFICATION_CRITICAL, DEFAULT_NOTIFICATION_CRITICAL
                            )
                        ),
                    },
                )

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(self.hass, current if user_input is None else user_input),
            errors=errors,
        )


def _schema(hass: HomeAssistant | None, defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_OPENAI_API_KEY,
                default=defaults.get(CONF_OPENAI_API_KEY, ""),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Optional(
                CONF_OPENAI_MODEL,
                default=defaults.get(CONF_OPENAI_MODEL, DEFAULT_OPENAI_MODEL),
            ): str,
            vol.Optional(
                CONF_NOTIFY_TARGETS,
                default=_normalize_notify_targets_input(defaults.get(CONF_NOTIFY_TARGETS)),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_notify_service_options(hass),
                    multiple=True,
                    custom_value=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    sort=True,
                )
            ),
            vol.Optional(
                CONF_MORNING_TIME,
                default=defaults.get(CONF_MORNING_TIME, DEFAULT_MORNING_TIME),
            ): str,
            vol.Optional(
                CONF_EVENING_TIME,
                default=defaults.get(CONF_EVENING_TIME, DEFAULT_EVENING_TIME),
            ): str,
            vol.Optional(
                CONF_ANNUAL_SCAN_REMINDER_TIME,
                default=defaults.get(
                    CONF_ANNUAL_SCAN_REMINDER_TIME,
                    DEFAULT_ANNUAL_SCAN_REMINDER_TIME,
                ),
            ): str,
            vol.Optional(
                CONF_NOTIFICATION_CHANNEL,
                default=defaults.get(
                    CONF_NOTIFICATION_CHANNEL, DEFAULT_NOTIFICATION_CHANNEL
                ),
            ): str,
            vol.Optional(
                CONF_NOTIFICATION_STICKY,
                default=bool(
                    defaults.get(CONF_NOTIFICATION_STICKY, DEFAULT_NOTIFICATION_STICKY)
                ),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_NOTIFICATION_SOUND_IOS,
                default=defaults.get(
                    CONF_NOTIFICATION_SOUND_IOS, DEFAULT_NOTIFICATION_SOUND_IOS
                ),
            ): str,
            vol.Optional(
                CONF_NOTIFICATION_CRITICAL,
                default=bool(
                    defaults.get(CONF_NOTIFICATION_CRITICAL, DEFAULT_NOTIFICATION_CRITICAL)
                ),
            ): selector.BooleanSelector(),
        }
    )


def _validate_input(user_input: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not str(user_input.get(CONF_OPENAI_API_KEY, "")).strip():
        errors[CONF_OPENAI_API_KEY] = "required"
    for key, default in (
        (CONF_MORNING_TIME, DEFAULT_MORNING_TIME),
        (CONF_EVENING_TIME, DEFAULT_EVENING_TIME),
        (CONF_ANNUAL_SCAN_REMINDER_TIME, DEFAULT_ANNUAL_SCAN_REMINDER_TIME),
    ):
        try:
            parse_time_value(user_input.get(key), default)
        except ValueError:
            errors[key] = "invalid_time"
    return errors


def _notify_service_options(hass: HomeAssistant | None) -> list[selector.SelectOptionDict]:
    """Return available notify services for a multi-select config flow field."""
    if hass is None:
        return []
    services = hass.services.async_services().get("notify", {})
    return [
        {"value": service, "label": f"notify.{service}"}
        for service in sorted(services)
    ]


def _normalize_notify_targets_input(value: Any) -> list[str]:
    """Normalize config flow notify selector output to notify service names."""
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = [item for chunk in value.splitlines() for item in chunk.split(",")]
    elif isinstance(value, list):
        raw_items = [str(item) for item in value]
    else:
        raw_items = [str(value)]

    targets: list[str] = []
    for item in raw_items:
        target = item.strip()
        if not target:
            continue
        if target.startswith("notify."):
            target = target.removeprefix("notify.")
        if target not in targets:
            targets.append(target)
    return targets
