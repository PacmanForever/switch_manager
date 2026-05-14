"""Service registration for the SwitchFlow Controller integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.exceptions import ServiceValidationError

from .const import (
    CONF_CONTROLLER_ID,
    DATA_MANAGER,
    DOMAIN,
    SERVICE_DISABLE_CONTROLLER,
    SERVICE_ENABLE_CONTROLLER,
    SERVICE_FORCE_TURN_OFF,
    SERVICE_FORCE_TURN_ON,
    SERVICE_RESET_CONTROLLER_TIMER,
)
from .manager import SwitchManagerRuntime

SERVICE_CONTROLLER_SCHEMA = vol.Schema({vol.Required(CONF_CONTROLLER_ID): str})


def _get_manager(hass: HomeAssistant) -> SwitchManagerRuntime:
    """Return the active runtime manager for the single supported config entry."""
    domain_data = hass.data.get(DOMAIN, {})
    if not domain_data:
        raise ServiceValidationError("SwitchFlow Controller is not configured")
    first_entry = next(iter(domain_data.values()))
    return first_entry[DATA_MANAGER]


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services."""
    if hass.services.has_service(DOMAIN, SERVICE_ENABLE_CONTROLLER):
        return

    async def _run_manager_call(call) -> None:
        try:
            await call
        except HomeAssistantError as err:
            raise ServiceValidationError(str(err)) from err

    async def async_enable_controller(service_call) -> None:
        manager = _get_manager(hass)
        await _run_manager_call(
            manager.async_set_controller_enabled(
                service_call.data[CONF_CONTROLLER_ID],
                True,
            )
        )

    async def async_disable_controller(service_call) -> None:
        manager = _get_manager(hass)
        await _run_manager_call(
            manager.async_set_controller_enabled(
                service_call.data[CONF_CONTROLLER_ID],
                False,
            )
        )

    async def async_reset_controller_timer(service_call) -> None:
        manager = _get_manager(hass)
        await _run_manager_call(
            manager.async_reset_controller_timer(service_call.data[CONF_CONTROLLER_ID])
        )

    async def async_force_turn_on(service_call) -> None:
        manager = _get_manager(hass)
        await _run_manager_call(
            manager.async_force_turn_on(service_call.data[CONF_CONTROLLER_ID])
        )

    async def async_force_turn_off(service_call) -> None:
        manager = _get_manager(hass)
        await _run_manager_call(
            manager.async_force_turn_off(service_call.data[CONF_CONTROLLER_ID])
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_ENABLE_CONTROLLER,
        async_enable_controller,
        schema=SERVICE_CONTROLLER_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DISABLE_CONTROLLER,
        async_disable_controller,
        schema=SERVICE_CONTROLLER_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_CONTROLLER_TIMER,
        async_reset_controller_timer,
        schema=SERVICE_CONTROLLER_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_FORCE_TURN_ON,
        async_force_turn_on,
        schema=SERVICE_CONTROLLER_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_FORCE_TURN_OFF,
        async_force_turn_off,
        schema=SERVICE_CONTROLLER_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload integration services."""
    hass.services.async_remove(DOMAIN, SERVICE_ENABLE_CONTROLLER)
    hass.services.async_remove(DOMAIN, SERVICE_DISABLE_CONTROLLER)
    hass.services.async_remove(DOMAIN, SERVICE_RESET_CONTROLLER_TIMER)
    hass.services.async_remove(DOMAIN, SERVICE_FORCE_TURN_ON)
    hass.services.async_remove(DOMAIN, SERVICE_FORCE_TURN_OFF)