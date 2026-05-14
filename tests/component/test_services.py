"""Component tests for switchflow_controller services."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from homeassistant.exceptions import HomeAssistantError
from homeassistant.exceptions import ServiceValidationError

from custom_components.switchflow_controller.const import (
    CONF_CONTROLLER_ID,
    DATA_MANAGER,
    DOMAIN,
    SERVICE_ENABLE_CONTROLLER,
    SERVICE_FORCE_TURN_OFF,
    SERVICE_FORCE_TURN_ON,
    SERVICE_RESET_CONTROLLER_TIMER,
)
from custom_components.switchflow_controller.services import async_setup_services, async_unload_services


@pytest.mark.asyncio
async def test_force_turn_on_service_calls_runtime_manager(hass) -> None:
    """The force_turn_on service should delegate to the runtime manager."""
    manager = AsyncMock()
    hass.data.setdefault(DOMAIN, {})["entry"] = {DATA_MANAGER: manager}
    await async_setup_services(hass)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_FORCE_TURN_ON,
        {CONF_CONTROLLER_ID: "hallway"},
        blocking=True,
    )

    manager.async_force_turn_on.assert_awaited_once_with("hallway")
    await async_unload_services(hass)


@pytest.mark.asyncio
async def test_enable_service_calls_runtime_manager(hass) -> None:
    """The enable service should persist enabled state via the manager."""
    manager = AsyncMock()
    hass.data.setdefault(DOMAIN, {})["entry"] = {DATA_MANAGER: manager}
    await async_setup_services(hass)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ENABLE_CONTROLLER,
        {CONF_CONTROLLER_ID: "bathroom"},
        blocking=True,
    )

    manager.async_set_controller_enabled.assert_awaited_once_with("bathroom", True)
    await async_unload_services(hass)


@pytest.mark.asyncio
async def test_reset_timer_requires_configured_manager(hass) -> None:
    """Service calls should fail clearly when the integration is not loaded."""
    await async_setup_services(hass)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RESET_CONTROLLER_TIMER,
            {CONF_CONTROLLER_ID: "missing"},
            blocking=True,
        )

    await async_unload_services(hass)


@pytest.mark.asyncio
async def test_force_turn_off_service_calls_runtime_manager(hass) -> None:
    """The force_turn_off service should delegate to the runtime manager."""
    manager = AsyncMock()
    hass.data.setdefault(DOMAIN, {})["entry"] = {DATA_MANAGER: manager}
    await async_setup_services(hass)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_FORCE_TURN_OFF,
        {CONF_CONTROLLER_ID: "hallway"},
        blocking=True,
    )

    manager.async_force_turn_off.assert_awaited_once_with("hallway")
    await async_unload_services(hass)


@pytest.mark.asyncio
async def test_invalid_controller_id_is_reported_as_service_validation_error(hass) -> None:
    """Unknown controller ids should surface as service validation errors."""
    manager = AsyncMock()
    manager.async_force_turn_on.side_effect = HomeAssistantError("Unknown controller id: missing")
    hass.data.setdefault(DOMAIN, {})["entry"] = {DATA_MANAGER: manager}
    await async_setup_services(hass)

    with pytest.raises(ServiceValidationError, match="Unknown controller id: missing"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_FORCE_TURN_ON,
            {CONF_CONTROLLER_ID: "missing"},
            blocking=True,
        )

    await async_unload_services(hass)


@pytest.mark.asyncio
async def test_reset_timer_on_disabled_controller_is_a_validation_error(hass) -> None:
    """Resetting a timer for a disabled controller should fail clearly."""
    manager = AsyncMock()
    manager.async_reset_controller_timer.side_effect = HomeAssistantError(
        "Controller hallway is disabled or not running"
    )
    hass.data.setdefault(DOMAIN, {})["entry"] = {DATA_MANAGER: manager}
    await async_setup_services(hass)

    with pytest.raises(
        ServiceValidationError,
        match="Controller hallway is disabled or not running",
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RESET_CONTROLLER_TIMER,
            {CONF_CONTROLLER_ID: "hallway"},
            blocking=True,
        )

    await async_unload_services(hass)