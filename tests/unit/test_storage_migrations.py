"""Unit tests for switch_manager storage normalization and migration."""

from __future__ import annotations

import pytest

from custom_components.switch_manager.storage import SwitchManagerStorage


def test_normalize_payload_migrates_legacy_list() -> None:
    """A legacy top-level list should migrate into the current payload shape."""
    payload, migrated = SwitchManagerStorage._normalize_payload(
        [
            {
                "id": "hallway",
                "name": "Hallway",
                "main_entity": "light.hallway",
                "wait_time": 120,
            }
        ]
    )

    assert migrated is True
    assert payload["version"] == 1
    assert len(payload["controllers"]) == 1


def test_normalize_payload_marks_missing_version_for_save() -> None:
    """A dict without version should still be normalized to the current schema."""
    payload, migrated = SwitchManagerStorage._normalize_payload(
        {
            "controllers": [
                {
                    "id": "bathroom",
                    "name": "Bathroom",
                    "main_entity": "light.bathroom",
                    "wait_time": 60,
                }
            ]
        }
    )

    assert migrated is True
    assert payload["version"] == 1


def test_normalize_payload_rejects_invalid_types() -> None:
    """Unsupported payload types should fail loudly."""
    with pytest.raises(ValueError, match="Invalid storage payload type"):
        SwitchManagerStorage._normalize_payload("invalid")