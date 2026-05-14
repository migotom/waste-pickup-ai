"""Constants for the Waste Pickup AI integration."""

from __future__ import annotations

DOMAIN = "waste_pickup_ai"

PLATFORMS = ("calendar", "sensor")

CONF_OPENAI_API_KEY = "openai_api_key"
CONF_OPENAI_MODEL = "openai_model"
CONF_NOTIFY_TARGETS = "notify_targets"
CONF_MORNING_TIME = "morning_time"
CONF_EVENING_TIME = "evening_time"
CONF_ANNUAL_SCAN_REMINDER_TIME = "annual_scan_reminder_time"

DEFAULT_OPENAI_MODEL = "gpt-5.5"
DEFAULT_MORNING_TIME = "08:00"
DEFAULT_EVENING_TIME = "20:00"
DEFAULT_ANNUAL_SCAN_REMINDER_TIME = "09:00"
MIN_HOME_ASSISTANT_VERSION = "2025.5.0"

STORAGE_KEY = f"{DOMAIN}.schedule"
STORAGE_VERSION = 1

PANEL_URL_PATH = "waste-pickup-ai"
PANEL_STATIC_URL = f"/{DOMAIN}_static"
PANEL_MODULE_URL = f"{PANEL_STATIC_URL}/waste-pickup-ai-panel.js"
PANEL_COMPONENT_NAME = "waste-pickup-ai-panel"

SERVICE_SCAN_IMAGE = "scan_image"
SERVICE_SET_CELL = "set_cell"
SERVICE_ACTIVATE_SCHEDULE = "activate_schedule"
SERVICE_SEND_TEST_NOTIFICATION = "send_test_notification"

ATTR_CATEGORIES = "categories"
ATTR_DATE = "date"
ATTR_DAYS_UNTIL = "days_until"
ATTR_YEAR = "year"

MAX_IMAGE_BYTES = 20 * 1024 * 1024
