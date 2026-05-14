"""Pure schedule parsing and notification helpers for Waste Pickup AI."""

from __future__ import annotations

import calendar as calendar_lib
from collections import defaultdict
from collections.abc import Iterable, Mapping
from copy import deepcopy
from datetime import date, datetime, time, timedelta
import re
import unicodedata
from typing import Any

MONTH_ALIASES: dict[str, int] = {
    "1": 1,
    "01": 1,
    "i": 1,
    "jan": 1,
    "styczen": 1,
    "stycznia": 1,
    "2": 2,
    "02": 2,
    "ii": 2,
    "lut": 2,
    "luty": 2,
    "lutego": 2,
    "3": 3,
    "03": 3,
    "iii": 3,
    "mar": 3,
    "marzec": 3,
    "marca": 3,
    "4": 4,
    "04": 4,
    "iv": 4,
    "kwi": 4,
    "kwiecien": 4,
    "kwietnia": 4,
    "5": 5,
    "05": 5,
    "v": 5,
    "maj": 5,
    "maja": 5,
    "6": 6,
    "06": 6,
    "vi": 6,
    "cze": 6,
    "czerwiec": 6,
    "czerwca": 6,
    "7": 7,
    "07": 7,
    "vii": 7,
    "lip": 7,
    "lipiec": 7,
    "lipca": 7,
    "8": 8,
    "08": 8,
    "viii": 8,
    "sie": 8,
    "sierpien": 8,
    "sierpnia": 8,
    "9": 9,
    "09": 9,
    "ix": 9,
    "wrz": 9,
    "wrzesien": 9,
    "wrzesnia": 9,
    "10": 10,
    "x": 10,
    "paz": 10,
    "pazdziernik": 10,
    "pazdziernika": 10,
    "11": 11,
    "xi": 11,
    "lis": 11,
    "listopad": 11,
    "listopada": 11,
    "12": 12,
    "xii": 12,
    "gru": 12,
    "grudzien": 12,
    "grudnia": 12,
}

EMPTY_CELL_VALUES = {"", "-", "—", "–", "brak", "none", "null", "n/a"}
EXCLUDED_CATEGORY_KEYS = {"popiol"}


class ScheduleValidationError(ValueError):
    """Raised when a schedule cannot be activated."""


def strip_diacritics(value: str) -> str:
    """Return ASCII-ish lowercase text without diacritics."""
    value = value.replace("ł", "l").replace("Ł", "L")
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def normalize_text(value: Any) -> str:
    """Normalize text for fuzzy matching."""
    return re.sub(r"\s+", " ", strip_diacritics(str(value or "")).lower()).strip()


def normalize_category(value: Any) -> str:
    """Normalize a waste category into a stable key."""
    normalized = normalize_text(value)
    return re.sub(r"[^a-z0-9]+", "", normalized)


def should_notify_category(category: Any) -> bool:
    """Return whether a category should generate reminders."""
    key = normalize_category(category)
    return not any(excluded in key for excluded in EXCLUDED_CATEGORY_KEYS)


def month_number(value: Any) -> int:
    """Convert a numeric, roman, or Polish month label to a month number."""
    key = normalize_category(value)
    if key in MONTH_ALIASES:
        return MONTH_ALIASES[key]
    raise ValueError(f"Unknown month label: {value!r}")


def month_key(value: Any) -> str:
    """Return the canonical string key for a month label."""
    return str(month_number(value))


def parse_days_cell(value: Any) -> list[int]:
    """Parse a table cell into sorted unique day numbers."""
    if value is None:
        return []
    if isinstance(value, bool):
        return []
    if isinstance(value, int):
        return [value] if value > 0 else []
    if isinstance(value, float):
        return [int(value)] if value.is_integer() and value > 0 else []
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        days: list[int] = []
        for item in value:
            days.extend(parse_days_cell(item))
        return sorted(set(days))

    text = normalize_text(value)
    if text in EMPTY_CELL_VALUES:
        return []

    # OCR commonly turns separators into dots, semicolons, slashes, or spaces.
    parts = re.findall(r"\d+", text)
    return sorted({int(part) for part in parts if int(part) > 0})


def normalize_days_by_month(raw: Any) -> dict[str, list[int]]:
    """Normalize month-keyed day data to keys '1'...'12'."""
    days_by_month = {str(month): [] for month in range(1, 13)}
    if not isinstance(raw, Mapping):
        return days_by_month

    for raw_month, raw_days in raw.items():
        try:
            key = month_key(raw_month)
        except ValueError:
            continue
        days_by_month[key] = parse_days_cell(raw_days)

    return days_by_month


def normalize_schedule(payload: Mapping[str, Any] | None, fallback_year: int | None = None) -> dict[str, Any]:
    """Normalize an LLM/user schedule payload into the stored shape."""
    source = dict(payload or {})
    year = _coerce_year(source.get("year"), fallback_year)
    rows = []
    warnings: list[str] = [str(item) for item in source.get("warnings", []) if item]
    errors: list[str] = []

    for index, raw_row in enumerate(source.get("rows", []) or []):
        if not isinstance(raw_row, Mapping):
            warnings.append(f"Ignoring non-object row at index {index}.")
            continue

        category_raw = str(raw_row.get("category_raw") or raw_row.get("category") or "").strip()
        category_key = normalize_category(raw_row.get("category_key") or category_raw)
        if not category_raw:
            category_raw = category_key or f"Kategoria {index + 1}"
        if not category_key:
            category_key = normalize_category(category_raw)
        notify_allowed = should_notify_category(f"{category_key} {category_raw}")

        row = {
            "category_raw": category_raw,
            "category_key": category_key,
            "notify": bool(raw_row.get("notify", notify_allowed)) and notify_allowed,
            "confidence": _coerce_confidence(raw_row.get("confidence")),
            "warnings": [str(item) for item in raw_row.get("warnings", []) if item],
            "days_by_month": normalize_days_by_month(raw_row.get("days_by_month")),
        }
        rows.append(row)

    normalized = {
        "version": 1,
        "year": year,
        "rows": rows,
        "warnings": warnings,
        "errors": errors,
        "source": source.get("source") if isinstance(source.get("source"), Mapping) else {},
        "scanned_at": source.get("scanned_at"),
        "activated_at": source.get("activated_at"),
    }
    validate_schedule(normalized)
    return normalized


def validate_schedule(schedule: dict[str, Any]) -> dict[str, Any]:
    """Populate warning/error fields for a normalized schedule."""
    schedule.setdefault("warnings", [])
    schedule.setdefault("errors", [])
    schedule["errors"] = []

    year = schedule.get("year")
    if not isinstance(year, int) or year < 2000 or year > 2100:
        schedule["errors"].append("Brakuje poprawnego roku harmonogramu.")
        return schedule

    for row_index, row in enumerate(schedule.get("rows", [])):
        if not row.get("category_key"):
            schedule["errors"].append(f"Wiersz {row_index + 1}: brakuje kategorii.")
        days_by_month = row.setdefault("days_by_month", {str(month): [] for month in range(1, 13)})
        for month in range(1, 13):
            key = str(month)
            valid_days: list[int] = []
            last_day = calendar_lib.monthrange(year, month)[1]
            for day in parse_days_cell(days_by_month.get(key)):
                if 1 <= day <= last_day:
                    valid_days.append(day)
                else:
                    schedule["errors"].append(
                        f"{row.get('category_raw', 'Wiersz')} / {month}: dzień {day} nie istnieje w {year}."
                    )
            days_by_month[key] = sorted(set(valid_days))

    if not schedule.get("rows"):
        schedule["errors"].append("Nie znaleziono żadnych wierszy harmonogramu.")

    return schedule


def set_schedule_cell(schedule: Mapping[str, Any], row_index: int, month: Any, value: Any) -> dict[str, Any]:
    """Return a copy of schedule with one cell changed."""
    updated = deepcopy(dict(schedule))
    rows = updated.get("rows", [])
    if row_index < 0 or row_index >= len(rows):
        raise IndexError(f"Row index out of range: {row_index}")
    key = month_key(month)
    rows[row_index].setdefault("days_by_month", {})[key] = parse_days_cell(value)
    validate_schedule(updated)
    return updated


def build_pickup_events(schedule: Mapping[str, Any] | None, include_excluded: bool = False) -> list[dict[str, Any]]:
    """Build aggregated calendar events from a schedule."""
    if not schedule or not isinstance(schedule.get("year"), int):
        return []

    grouped: dict[date, dict[str, list[str]]] = defaultdict(lambda: {"categories": [], "category_keys": []})
    year = int(schedule["year"])

    for row in schedule.get("rows", []):
        category = str(row.get("category_raw") or row.get("category_key") or "").strip()
        category_key = normalize_category(row.get("category_key") or category)
        notify = bool(row.get("notify", should_notify_category(category_key)))
        if not include_excluded and not notify:
            continue

        for raw_month, raw_days in (row.get("days_by_month") or {}).items():
            try:
                month = month_number(raw_month)
            except ValueError:
                continue
            for day in parse_days_cell(raw_days):
                try:
                    event_date = date(year, month, day)
                except ValueError:
                    continue
                grouped[event_date]["categories"].append(category)
                grouped[event_date]["category_keys"].append(category_key)

    events = []
    for event_date, values in grouped.items():
        categories = sorted(set(values["categories"]), key=normalize_category)
        category_keys = sorted(set(values["category_keys"]))
        events.append(
            {
                "date": event_date.isoformat(),
                "categories": categories,
                "category_keys": category_keys,
                "summary": f"Odpady: {', '.join(categories)}",
            }
        )
    return sorted(events, key=lambda item: item["date"])


def next_pickup(schedule: Mapping[str, Any] | None, today: date | None = None) -> dict[str, Any] | None:
    """Return the next pickup event on or after today."""
    today = today or date.today()
    for event in build_pickup_events(schedule):
        if date.fromisoformat(event["date"]) >= today:
            return {
                **event,
                "days_until": (date.fromisoformat(event["date"]) - today).days,
            }
    return None


def parse_time_value(value: Any, default: str) -> time:
    """Parse HH:MM or HH:MM:SS to a time value."""
    text = str(value or default).strip()
    parts = text.split(":")
    if len(parts) not in (2, 3):
        raise ValueError(f"Invalid time value: {value!r}")
    hour = int(parts[0])
    minute = int(parts[1])
    second = int(parts[2]) if len(parts) == 3 else 0
    return time(hour, minute, second)


def notification_slot_for_now(now: datetime, morning_time: time, evening_time: time) -> str | None:
    """Return reminder slot name if now matches a configured reminder time."""
    current = now.time().replace(second=0, microsecond=0)
    if current == morning_time.replace(second=0, microsecond=0):
        return "morning"
    if current == evening_time.replace(second=0, microsecond=0):
        return "evening"
    return None


def notification_key(event: Mapping[str, Any], slot: str, target: str) -> str:
    """Build a stable dedupe key for a notification."""
    categories = ",".join(event.get("category_keys") or [normalize_category(c) for c in event.get("categories", [])])
    return f"{event.get('date')}|{slot}|{categories}|{target}"


def due_pickup_notifications(
    schedule: Mapping[str, Any] | None,
    now: datetime,
    morning_time: time,
    evening_time: time,
    targets: Iterable[str],
    sent_keys: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """Return target-specific notifications due at this exact minute."""
    slot = notification_slot_for_now(now, morning_time, evening_time)
    if slot is None:
        return []

    sent = set(sent_keys)
    tomorrow = now.date() + timedelta(days=1)
    due: list[dict[str, Any]] = []
    for event in build_pickup_events(schedule):
        if date.fromisoformat(event["date"]) != tomorrow:
            continue
        for target in targets:
            key = notification_key(event, slot, target)
            if key in sent:
                continue
            due.append({"key": key, "slot": slot, "target": target, "event": event})
    return due


def annual_scan_reminder_due(now: datetime, reminder_time: time, sent_keys: Iterable[str] = ()) -> bool:
    """Return whether the annual scan reminder is due at this exact minute."""
    if now.month != 1 or now.day != 1:
        return False
    current = now.time().replace(second=0, microsecond=0)
    if current != reminder_time.replace(second=0, microsecond=0):
        return False
    return f"annual-scan|{now.year}" not in set(sent_keys)


def schedule_status(schedule: Mapping[str, Any] | None, today: date | None = None) -> dict[str, Any]:
    """Return a compact status object for sensors and the panel."""
    today = today or date.today()
    if not schedule:
        return {
            "state": "needs_scan",
            "year": None,
            "warnings": ["Brak aktywnego harmonogramu."],
            "errors": [],
            "event_count": 0,
        }
    year = schedule.get("year")
    warnings = list(schedule.get("warnings", []))
    errors = list(schedule.get("errors", []))
    if isinstance(year, int) and year < today.year:
        warnings.append("Aktywny harmonogram jest z poprzedniego roku.")
    state = "active"
    if errors:
        state = "invalid"
    elif isinstance(year, int) and year < today.year:
        state = "stale"
    return {
        "state": state,
        "year": year,
        "warnings": warnings,
        "errors": errors,
        "event_count": len(build_pickup_events(schedule)),
    }


def _coerce_year(value: Any, fallback_year: int | None) -> int | None:
    if isinstance(value, bool):
        return fallback_year
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        match = re.search(r"\b(20\d{2}|21\d{2})\b", value)
        if match:
            return int(match.group(1))
    return fallback_year


def _coerce_confidence(value: Any) -> float | None:
    if value is None:
        return None
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, confidence))
