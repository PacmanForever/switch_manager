"""The Switch Manager integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DATA_MANAGER, DOMAIN
from .manager import SwitchManagerRuntime
from .services import async_setup_services, async_unload_services

SwitchManagerConfigEntry = ConfigEntry


async def async_setup_entry(
    hass: HomeAssistant, config_entry: SwitchManagerConfigEntry
) -> bool:
    """Set up Switch Manager from a config entry."""
    manager = SwitchManagerRuntime(hass, config_entry)
    await manager.async_setup()

    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = {
        DATA_MANAGER: manager,
    }

    await async_setup_services(hass)
    config_entry.async_on_unload(config_entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(
    hass: HomeAssistant, config_entry: SwitchManagerConfigEntry
) -> bool:
    """Unload a Switch Manager config entry."""
    entry_data = hass.data.get(DOMAIN, {}).pop(config_entry.entry_id, None)
    if entry_data is not None:
        manager: SwitchManagerRuntime = entry_data[DATA_MANAGER]
        await manager.async_unload()

    if not hass.data.get(DOMAIN):
        hass.data.pop(DOMAIN, None)
        await async_unload_services(hass)

    return True


async def _async_update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle config-entry updates by reloading the runtime manager."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    manager: SwitchManagerRuntime = entry_data[DATA_MANAGER]
    await manager.async_reload()