"""Component tests for switch_manager config and options flows."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.switch_manager.config_flow import (
    SwitchManagerConfigFlow,
    SwitchManagerOptionsFlow,
)
from custom_components.switch_manager.const import DOMAIN
from custom_components.switch_manager.models import ControllerConfig


@pytest.mark.asyncio
async def test_user_flow_creates_single_instance_entry(hass) -> None:
    """The user flow should create one config entry and then block duplicates."""
    flow = SwitchManagerConfigFlow()
    flow.hass = hass

    with patch.object(flow, "_async_current_entries", return_value=[]):
        result = await flow.async_step_user({})

    assert result["type"] is FlowResultType.CREATE_ENTRY

    duplicate_flow = SwitchManagerConfigFlow()
    duplicate_flow.hass = hass
    with patch.object(duplicate_flow, "_async_current_entries", return_value=[object()]):
        duplicate = await duplicate_flow.async_step_user()

    assert duplicate["type"] is FlowResultType.ABORT
    assert duplicate["reason"] == "single_instance_allowed"


@pytest.mark.asyncio
async def test_options_flow_adds_controller(hass) -> None:
    """The options flow should persist a new controller."""
    entry = MockConfigEntry(domain=DOMAIN, title="Switch Manager", data={})
    flow = SwitchManagerOptionsFlow(entry)
    flow.hass = hass

    with (
        patch(
            "custom_components.switch_manager.config_flow.SwitchManagerStorage.async_load",
            AsyncMock(return_value=[]),
        ),
        patch(
            "custom_components.switch_manager.config_flow.SwitchManagerStorage.async_upsert",
            AsyncMock(),
        ) as upsert_mock,
        patch.object(hass.config_entries, "async_reload", AsyncMock()),
    ):
        result = await flow.async_step_add_controller(
            {
                "main_entity": "light.hallway",
                "wait_time": 120,
                "enabled": True,
                "activate_on_detection": True,
                "turn_off_when_presence_clears": False,
                "notify_with_alarm": False,
            }
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    stored_controller = upsert_mock.await_args.args[0]
    assert stored_controller.controller_id == "hallway"
    assert stored_controller.name == "Hallway"
    assert stored_controller.main_entity == "light.hallway"


@pytest.mark.asyncio
async def test_options_flow_edits_existing_controller(hass) -> None:
    """The options flow should edit an existing controller record."""
    entry = MockConfigEntry(domain=DOMAIN, title="Switch Manager", data={})
    flow = SwitchManagerOptionsFlow(entry)
    flow.hass = hass
    flow._selected_controller_id = "hallway"
    controller = ControllerConfig.from_mapping(
        {
            "id": "hallway",
            "name": "Hallway",
            "main_entity": "light.hallway",
            "wait_time": 120,
        }
    )

    with (
        patch(
            "custom_components.switch_manager.config_flow.SwitchManagerStorage.async_load",
            AsyncMock(return_value=[controller]),
        ),
        patch(
            "custom_components.switch_manager.config_flow.SwitchManagerStorage.async_upsert",
            AsyncMock(),
        ) as upsert_mock,
        patch.object(hass.config_entries, "async_reload", AsyncMock()),
    ):
        result = await flow.async_step_edit_controller(
            {
                "main_entity": "light.kitchen",
                "wait_time": 180,
                "enabled": True,
                "activate_on_detection": True,
                "turn_off_when_presence_clears": False,
                "notify_with_alarm": False,
            }
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    stored_controller = upsert_mock.await_args.args[0]
    assert stored_controller.controller_id == "hallway"
    assert stored_controller.name == "Kitchen"
    assert stored_controller.main_entity == "light.kitchen"
    assert stored_controller.wait_time == 180