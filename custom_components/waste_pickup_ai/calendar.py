"""Calendar platform for Waste Pickup AI."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .schedule import build_pickup_events, next_pickup


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the waste pickup calendar."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WastePickupCalendar(runtime, entry.entry_id)])


class WastePickupCalendar(CalendarEntity):
    """Calendar entity exposing active waste pickup dates."""

    _attr_name = "Waste pickups"
    _attr_icon = "mdi:trash-can-outline"

    def __init__(self, runtime: Any, entry_id: str) -> None:
        self._runtime = runtime
        self._attr_unique_id = f"{entry_id}_waste_pickups"
        self._remove_update_listener = None

    async def async_added_to_hass(self) -> None:
        """Register runtime updates."""
        self._remove_update_listener = self._runtime.async_add_update_listener(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        """Remove runtime updates."""
        await super().async_will_remove_from_hass()
        if self._remove_update_listener:
            self._remove_update_listener()

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        event = next_pickup(self._runtime.store.data.get("active_schedule"), date.today())
        if event is None:
            return None
        return _calendar_event(event)

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return waste pickup events within a datetime range."""
        active_schedule = self._runtime.store.data.get("active_schedule")
        events = []
        for event in build_pickup_events(active_schedule):
            event_date = date.fromisoformat(event["date"])
            if start_date.date() <= event_date < end_date.date():
                events.append(_calendar_event(event))
        return events

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


def _calendar_event(event: dict[str, Any]) -> CalendarEvent:
    event_date = date.fromisoformat(event["date"])
    categories = ", ".join(event["categories"])
    return CalendarEvent(
        start=event_date,
        end=event_date + timedelta(days=1),
        summary=f"Odpady: {categories}",
        description=f"Odbiór odpadów: {categories}",
    )
