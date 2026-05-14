"""Config flow for Waste Pickup AI."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

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
                        CONF_NOTIFY_TARGETS: user_input.get(CONF_NOTIFY_TARGETS, ""),
                        CONF_MORNING_TIME: user_input.get(CONF_MORNING_TIME) or DEFAULT_MORNING_TIME,
                        CONF_EVENING_TIME: user_input.get(CONF_EVENING_TIME) or DEFAULT_EVENING_TIME,
                        CONF_ANNUAL_SCAN_REMINDER_TIME: user_input.get(
                            CONF_ANNUAL_SCAN_REMINDER_TIME
                        )
                        or DEFAULT_ANNUAL_SCAN_REMINDER_TIME,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input),
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
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(current if user_input is None else user_input),
            errors=errors,
        )


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
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
                default=defaults.get(CONF_NOTIFY_TARGETS, ""),
            ): str,
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
