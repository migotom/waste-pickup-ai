"""Sensor platform for Waste Pickup AI."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_CATEGORIES, ATTR_DATE, ATTR_DAYS_UNTIL, ATTR_YEAR, DOMAIN
from .schedule import next_pickup, schedule_status


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up waste pickup sensors."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            WasteNextPickupSensor(runtime, entry.entry_id),
            WasteScheduleStatusSensor(runtime, entry.entry_id),
        ]
    )


class _WastePickupSensorBase(SensorEntity):
    _attr_icon = "mdi:trash-can-outline"

    def __init__(self, runtime: Any, entry_id: str) -> None:
        self._runtime = runtime
        self._entry_id = entry_id
        self._remove_update_listener = None

    async def async_added_to_hass(self) -> None:
        """Register runtime updates."""
        self._remove_update_listener = self._runtime.async_add_update_listener(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        """Remove runtime updates."""
        if self._remove_update_listener:
            self._remove_update_listener()

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


class WasteNextPickupSensor(_WastePickupSensorBase):
    """Sensor showing the next active pickup."""

    _attr_name = "Waste next pickup"

    def __init__(self, runtime: Any, entry_id: str) -> None:
        super().__init__(runtime, entry_id)
        self._attr_unique_id = f"{entry_id}_waste_next_pickup"

    @property
    def native_value(self) -> str | None:
        """Return the next pickup date."""
        event = next_pickup(self._runtime.store.data.get("active_schedule"), date.today())
        return event["date"] if event else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return pickup metadata."""
        event = next_pickup(self._runtime.store.data.get("active_schedule"), date.today())
        if not event:
            return {}
        return {
            ATTR_DATE: event["date"],
            ATTR_CATEGORIES: event["categories"],
            ATTR_DAYS_UNTIL: event["days_until"],
        }


class WasteScheduleStatusSensor(_WastePickupSensorBase):
    """Sensor showing schedule activation health."""

    _attr_name = "Waste schedule status"

    def __init__(self, runtime: Any, entry_id: str) -> None:
        super().__init__(runtime, entry_id)
        self._attr_unique_id = f"{entry_id}_waste_schedule_status"

    @property
    def native_value(self) -> str:
        """Return schedule state."""
        return schedule_status(self._runtime.store.data.get("active_schedule"))["state"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return schedule status metadata."""
        status = schedule_status(self._runtime.store.data.get("active_schedule"))
        active = self._runtime.store.data.get("active_schedule") or {}
        return {
            ATTR_YEAR: status["year"],
            "warnings": status["warnings"],
            "errors": status["errors"],
            "event_count": status["event_count"],
            "scanned_at": active.get("scanned_at"),
            "activated_at": active.get("activated_at"),
        }

