"""Storage wrapper for Waste Pickup AI schedules."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .const import STORAGE_KEY, STORAGE_VERSION
from .schedule import ScheduleValidationError, normalize_schedule, set_schedule_cell, validate_schedule


def now_iso() -> str:
    """Return a UTC-ish timestamp suitable for HA storage."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


class WastePickupStore:
    """Persist draft/active schedules in Home Assistant storage."""

    def __init__(self, hass: Any) -> None:
        from homeassistant.helpers.storage import Store

        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.data: dict[str, Any] = _empty_data()

    async def async_load(self) -> None:
        """Load persisted data."""
        loaded = await self._store.async_load()
        if isinstance(loaded, dict):
            self.data = {**_empty_data(), **loaded}

    async def async_save(self) -> None:
        """Save persisted data."""
        await self._store.async_save(self.data)

    async def async_set_draft(
        self,
        payload: dict[str, Any],
        *,
        fallback_year: int | None = None,
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Store a draft schedule extracted from an image."""
        schedule = normalize_schedule(payload, fallback_year=fallback_year)
        schedule["scanned_at"] = now_iso()
        if source:
            schedule["source"] = source
        self.data["draft_schedule"] = schedule
        self.data["updated_at"] = now_iso()
        await self.async_save()
        return schedule

    async def async_set_cell(self, row_index: int, month: Any, value: Any) -> dict[str, Any]:
        """Update one draft schedule cell."""
        draft = self.data.get("draft_schedule")
        if not isinstance(draft, dict):
            raise ScheduleValidationError("Brak szkicu harmonogramu do edycji.")
        updated = set_schedule_cell(draft, row_index, month, value)
        self.data["draft_schedule"] = updated
        self.data["updated_at"] = now_iso()
        await self.async_save()
        return updated

    async def async_activate(self, year: int | None = None) -> dict[str, Any]:
        """Validate and promote the draft schedule to active."""
        draft = self.data.get("draft_schedule")
        if not isinstance(draft, dict):
            raise ScheduleValidationError("Brak szkicu harmonogramu do aktywacji.")
        schedule = normalize_schedule({**draft, "year": year or draft.get("year")})
        validate_schedule(schedule)
        if schedule.get("errors"):
            raise ScheduleValidationError("; ".join(schedule["errors"]))
        schedule["activated_at"] = now_iso()
        self.data["active_schedule"] = schedule
        self.data["draft_schedule"] = schedule
        self.data["sent_notifications"] = {}
        self.data["updated_at"] = now_iso()
        await self.async_save()
        return schedule

    async def async_mark_sent(self, key: str) -> None:
        """Persist a sent notification dedupe key."""
        sent = self.data.setdefault("sent_notifications", {})
        sent[key] = now_iso()
        if len(sent) > 1000:
            newest = sorted(sent.items(), key=lambda item: item[1], reverse=True)[:800]
            self.data["sent_notifications"] = dict(newest)
        await self.async_save()


def _empty_data() -> dict[str, Any]:
    return {
        "draft_schedule": None,
        "active_schedule": None,
        "sent_notifications": {},
        "updated_at": None,
    }
