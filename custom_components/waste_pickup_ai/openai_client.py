"""OpenAI Responses API client for extracting waste pickup schedules."""

from __future__ import annotations

import json
from typing import Any

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

WASTE_SCHEDULE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["year", "rows", "warnings"],
    "properties": {
        "year": {
            "type": "integer",
            "description": "Four digit year printed on the waste pickup schedule.",
        },
        "rows": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "category_raw",
                    "category_key",
                    "days_by_month",
                    "confidence",
                    "warnings",
                ],
                "properties": {
                    "category_raw": {
                        "type": "string",
                        "description": "Waste category exactly as read from the row label.",
                    },
                    "category_key": {
                        "type": "string",
                        "description": "ASCII lowercase category key, e.g. papier, szklo, popiol.",
                    },
                    "days_by_month": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [str(month) for month in range(1, 13)],
                        "properties": {
                            str(month): {
                                "type": "array",
                                "items": {"type": "integer", "minimum": 1, "maximum": 31},
                            }
                            for month in range(1, 13)
                        },
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "warnings": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
        "warnings": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}


class OpenAIExtractionError(RuntimeError):
    """Raised when OpenAI extraction fails."""


class OpenAIWasteScheduleClient:
    """Tiny OpenAI client using Home Assistant's aiohttp session."""

    def __init__(self, session: Any, api_key: str, model: str) -> None:
        self._session = session
        self._api_key = api_key
        self._model = model

    async def extract_schedule(self, image_data_url: str) -> dict[str, Any]:
        """Extract a schedule JSON object from a base64 data URL image."""
        from aiohttp import ClientTimeout

        payload = {
            "model": self._model,
            "reasoning": {"effort": "low"},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "waste_pickup_schedule",
                    "strict": True,
                    "schema": WASTE_SCHEDULE_JSON_SCHEMA,
                },
                "verbosity": "low",
            },
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You extract annual municipal waste pickup schedules from Polish "
                                "table photos. This integration is specifically targeted at annual waste "
                                "pickup schedules used in Gmina Działdowo, Poland. Return all visible waste "
                                "categories, including Popiol/Popiół, but do not invent rows or dates. Month "
                                "columns may be Roman numerals I-XII. Split comma-separated cells into integer "
                                "day arrays. Empty cells are empty arrays. Add a warning if the photo appears "
                                "to be unrelated to a Gmina Działdowo waste schedule."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Read this waste pickup schedule photo. Extract the schedule for manual "
                                "verification in Home Assistant."
                            ),
                        },
                        {"type": "input_image", "image_url": image_data_url},
                    ],
                },
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with self._session.post(
            OPENAI_RESPONSES_URL,
            headers=headers,
            json=payload,
            timeout=ClientTimeout(total=120),
        ) as response:
            body = await response.text()
            if response.status >= 400:
                raise OpenAIExtractionError(
                    f"OpenAI API returned HTTP {response.status}: {body[:500]}"
                )
            try:
                data = json.loads(body)
            except json.JSONDecodeError as err:
                raise OpenAIExtractionError("OpenAI API returned invalid JSON.") from err

        text = extract_response_text(data)
        if not text:
            raise OpenAIExtractionError("OpenAI API response did not contain output text.")
        try:
            result = json.loads(text)
        except json.JSONDecodeError as err:
            raise OpenAIExtractionError("OpenAI output was not valid JSON.") from err
        if not isinstance(result, dict):
            raise OpenAIExtractionError("OpenAI output was not a JSON object.")
        return result


def extract_response_text(response: dict[str, Any]) -> str | None:
    """Extract output text from a Responses API REST response."""
    if isinstance(response.get("output_text"), str):
        return response["output_text"]

    chunks: list[str] = []
    for item in response.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) or []:
            if not isinstance(content, dict):
                continue
            if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                chunks.append(content["text"])
    return "".join(chunks) or None
