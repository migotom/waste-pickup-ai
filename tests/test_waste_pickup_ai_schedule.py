from __future__ import annotations

from datetime import date, datetime, time
import unittest

from custom_components.waste_pickup_ai.openai_client import extract_response_text
from custom_components.waste_pickup_ai.schedule import (
    annual_scan_reminder_due,
    build_pickup_events,
    due_pickup_notifications,
    month_key,
    next_pickup,
    normalize_category,
    normalize_schedule,
    parse_days_cell,
    set_schedule_cell,
    should_notify_category,
)


class WastePickupScheduleTest(unittest.TestCase):
    def test_parse_days_cell_accepts_common_ocr_separators(self) -> None:
        self.assertEqual(parse_days_cell("8, 29"), [8, 29])
        self.assertEqual(parse_days_cell("8;29 / 30"), [8, 29, 30])
        self.assertEqual(parse_days_cell(["8", "29"]), [8, 29])
        self.assertEqual(parse_days_cell("-"), [])

    def test_month_key_accepts_roman_and_polish_labels(self) -> None:
        self.assertEqual(month_key("I"), "1")
        self.assertEqual(month_key("XII"), "12")
        self.assertEqual(month_key("październik"), "10")
        self.assertEqual(month_key("grudnia"), "12")

    def test_category_normalization_and_popiol_exclusion(self) -> None:
        self.assertEqual(normalize_category("  Popiół "), "popiol")
        self.assertFalse(should_notify_category("Popiół"))
        self.assertFalse(should_notify_category("Popiol"))
        self.assertTrue(should_notify_category("Odpady zmieszane"))

    def test_normalize_schedule_validates_invalid_month_days(self) -> None:
        schedule = normalize_schedule(
            {
                "year": 2023,
                "warnings": [],
                "rows": [
                    {
                        "category_raw": "Papier",
                        "category_key": "papier",
                        "confidence": 1,
                        "warnings": [],
                        "days_by_month": {"II": "29", "III": "31"},
                    }
                ],
            }
        )

        self.assertEqual(schedule["rows"][0]["days_by_month"]["2"], [])
        self.assertEqual(schedule["rows"][0]["days_by_month"]["3"], [31])
        self.assertIn("dzień 29", schedule["errors"][0])

    def test_leap_year_accepts_february_29(self) -> None:
        schedule = normalize_schedule(
            {
                "year": 2024,
                "warnings": [],
                "rows": [
                    {
                        "category_raw": "Papier",
                        "category_key": "papier",
                        "confidence": 1,
                        "warnings": [],
                        "days_by_month": {"II": "29"},
                    }
                ],
            }
        )

        self.assertEqual(schedule["errors"], [])
        self.assertEqual(schedule["rows"][0]["days_by_month"]["2"], [29])

    def test_build_events_aggregates_and_excludes_popiol(self) -> None:
        schedule = normalize_schedule(
            {
                "year": 2026,
                "warnings": [],
                "rows": [
                    {
                        "category_raw": "Papier",
                        "category_key": "papier",
                        "confidence": 1,
                        "warnings": [],
                        "days_by_month": {"I": "8, 29"},
                    },
                    {
                        "category_raw": "Bioodpady",
                        "category_key": "bioodpady",
                        "confidence": 1,
                        "warnings": [],
                        "days_by_month": {"I": "8"},
                    },
                    {
                        "category_raw": "Popiół",
                        "category_key": "popiol",
                        "confidence": 1,
                        "warnings": [],
                        "days_by_month": {"I": "8"},
                    },
                ],
            }
        )

        events = build_pickup_events(schedule)
        self.assertEqual(events[0]["date"], "2026-01-08")
        self.assertEqual(events[0]["categories"], ["Bioodpady", "Papier"])
        self.assertNotIn("Popiół", events[0]["categories"])
        self.assertEqual(next_pickup(schedule, date(2026, 1, 9))["date"], "2026-01-29")

    def test_set_schedule_cell_updates_draft_shape(self) -> None:
        schedule = normalize_schedule(
            {
                "year": 2026,
                "warnings": [],
                "rows": [
                    {
                        "category_raw": "Papier",
                        "category_key": "papier",
                        "confidence": 1,
                        "warnings": [],
                        "days_by_month": {"I": "8"},
                    }
                ],
            }
        )

        updated = set_schedule_cell(schedule, 0, "II", "4, 18")
        self.assertEqual(updated["rows"][0]["days_by_month"]["2"], [4, 18])

    def test_due_pickup_notifications_are_target_specific_and_deduped(self) -> None:
        schedule = normalize_schedule(
            {
                "year": 2026,
                "warnings": [],
                "rows": [
                    {
                        "category_raw": "Papier",
                        "category_key": "papier",
                        "confidence": 1,
                        "warnings": [],
                        "days_by_month": {"I": "8"},
                    }
                ],
            }
        )
        now = datetime(2026, 1, 7, 8, 0)

        due = due_pickup_notifications(
            schedule,
            now,
            time(8, 0),
            time(20, 0),
            ["mobile_app_iphone", "mobile_app_watch"],
        )
        self.assertEqual(len(due), 2)
        due_again = due_pickup_notifications(
            schedule,
            now,
            time(8, 0),
            time(20, 0),
            ["mobile_app_iphone", "mobile_app_watch"],
            sent_keys=[due[0]["key"]],
        )
        self.assertEqual(len(due_again), 1)

    def test_annual_scan_reminder(self) -> None:
        self.assertTrue(annual_scan_reminder_due(datetime(2026, 1, 1, 9, 0), time(9, 0)))
        self.assertFalse(annual_scan_reminder_due(datetime(2026, 1, 1, 9, 1), time(9, 0)))
        self.assertFalse(
            annual_scan_reminder_due(
                datetime(2026, 1, 1, 9, 0),
                time(9, 0),
                sent_keys=["annual-scan|2026"],
            )
        )

    def test_extract_response_text_from_responses_payload(self) -> None:
        payload = {
            "output": [
                {
                    "content": [
                        {
                            "type": "output_text",
                            "text": "{\"year\":2026,\"rows\":[],\"warnings\":[]}",
                        }
                    ]
                }
            ]
        }
        self.assertEqual(extract_response_text(payload), "{\"year\":2026,\"rows\":[],\"warnings\":[]}")


if __name__ == "__main__":
    unittest.main()

