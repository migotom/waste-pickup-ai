"""Sensor platform for Waste Pickup AI."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_CATEGORIES, ATTR_DATE, ATTR_DAYS_UNTIL, ATTR_YEAR, DOMAIN
from .schedule import next_pickup, next_pickups_by_category, schedule_status


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
            WasteCategoryPickupsSensor(runtime, entry.entry_id),
            WasteScheduleStatusSensor(runtime, entry.entry_id),
        ]
    )
    WasteCategorySensorManager(runtime, entry.entry_id, async_add_entities).setup()


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


class WasteCategoryPickupsSensor(_WastePickupSensorBase):
    """Sensor exposing upcoming pickup metadata for all categories."""

    _attr_name = "Waste category pickups"

    def __init__(self, runtime: Any, entry_id: str) -> None:
        super().__init__(runtime, entry_id)
        self._attr_unique_id = f"{entry_id}_waste_category_pickups"

    @property
    def native_value(self) -> int:
        """Return the number of categories with a future pickup date."""
        return len([item for item in _category_pickups(self._runtime) if item["date"]])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return category pickup metadata."""
        pickups = _category_pickups(self._runtime)
        return {
            "pickups": pickups,
            "summary": "; ".join(_format_pickup(item) for item in pickups if item["date"]),
        }


class WasteCategoryNextPickupSensor(_WastePickupSensorBase):
    """Sensor showing days until the next pickup for one category."""

    _attr_native_unit_of_measurement = "d"

    def __init__(
        self,
        runtime: Any,
        entry_id: str,
        category_key: str,
        category_name: str,
    ) -> None:
        super().__init__(runtime, entry_id)
        self._category_key = category_key
        self._category_name = category_name
        self._attr_unique_id = f"{entry_id}_waste_category_{category_key}_next_pickup"

    @property
    def name(self) -> str:
        """Return a category-specific entity name."""
        item = self._category_item()
        category = item["category"] if item else self._category_name
        return f"Odpady: {category}"

    @property
    def native_value(self) -> int | None:
        """Return days until the next pickup for this category."""
        item = self._category_item()
        return item["days_until"] if item and item["date"] else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return pickup metadata for this category."""
        item = self._category_item()
        if not item:
            return {"category": self._category_name, "category_key": self._category_key}
        return {
            "category": item["category"],
            "category_key": item["category_key"],
            ATTR_DATE: item["date"],
            ATTR_DAYS_UNTIL: item["days_until"],
            "future_dates": item["future_dates"],
            "display": _format_pickup(item) if item["date"] else "Brak przyszłego terminu",
        }

    def _category_item(self) -> dict[str, Any] | None:
        for item in _category_pickups(self._runtime):
            if item["category_key"] == self._category_key:
                return item
        return None


class WasteCategorySensorManager:
    """Create category sensors when categories appear in the active schedule."""

    def __init__(
        self,
        runtime: Any,
        entry_id: str,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        self._runtime = runtime
        self._entry_id = entry_id
        self._async_add_entities = async_add_entities
        self._known_category_keys: set[str] = set()
        self._remove_update_listener = None

    def setup(self) -> None:
        """Register the manager and add any already-known categories."""
        self._sync_entities()
        self._remove_update_listener = self._runtime.async_add_update_listener(
            self._sync_entities
        )

    @callback
    def _sync_entities(self) -> None:
        new_entities = []
        for item in _category_pickups(self._runtime):
            category_key = item["category_key"]
            if category_key in self._known_category_keys:
                continue
            self._known_category_keys.add(category_key)
            new_entities.append(
                WasteCategoryNextPickupSensor(
                    self._runtime,
                    self._entry_id,
                    category_key,
                    item["category"],
                )
            )
        if new_entities:
            self._async_add_entities(new_entities)


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


def _category_pickups(runtime: Any) -> list[dict[str, Any]]:
    return next_pickups_by_category(runtime.store.data.get("active_schedule"), date.today())


def _format_pickup(item: dict[str, Any]) -> str:
    date_value = item.get(ATTR_DATE) or item.get("date")
    days_until = item.get(ATTR_DAYS_UNTIL) if ATTR_DAYS_UNTIL in item else item.get(
        "days_until"
    )
    if date_value is None or days_until is None:
        return f"{item['category']}: brak przyszłego terminu"
    if days_until == 0:
        relative = "dzisiaj"
    elif days_until == 1:
        relative = "jutro"
    else:
        relative = f"za {days_until} dni"
    return f"{item['category']}: {date_value} ({relative})"
