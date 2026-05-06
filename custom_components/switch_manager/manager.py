"""Runtime manager for the Switch Manager integration."""

from __future__ import annotations

from dataclasses import replace
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .controller import ControllerRuntime
from .const import SUBENTRY_TYPE_CONTROLLER
from .config_flow import _entry_global_defaults
from .models import ControllerConfig, GlobalConfig

LOGGER = logging.getLogger(__name__)


class SwitchManagerRuntime:
    """Load, own, and reload global settings and controller runtimes."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the runtime manager."""
        self.hass = hass
        self.config_entry = config_entry
        self.global_config = GlobalConfig.from_mapping(_entry_global_defaults(config_entry))
        self.controllers: dict[str, ControllerConfig] = {}
        self._controller_subentries: dict[str, ConfigSubentry] = {}
        self._controller_runtimes: dict[str, ControllerRuntime] = {}

    async def async_setup(self) -> None:
        """Load controllers and start their runtimes."""
        self._controller_subentries = self._build_controller_subentries()
        self.controllers = self._build_controllers(self._controller_subentries)

        for controller in self.controllers.values():
            if not controller.enabled:
                continue
            await self._async_start_controller(controller)

        LOGGER.debug(
            "Switch Manager runtime loaded %s controller(s)",
            len(self._controller_runtimes),
        )

    async def async_unload(self) -> None:
        """Stop all active controller runtimes."""
        for runtime in list(self._controller_runtimes.values()):
            await runtime.async_stop()
        self._controller_runtimes.clear()

    async def async_reload(self) -> None:
        """Reload the runtime state from config entry and storage."""
        new_global_config = GlobalConfig.from_mapping(
            _entry_global_defaults(self.config_entry)
        )
        new_subentries = self._build_controller_subentries()
        new_controllers = self._build_controllers(new_subentries)

        if new_global_config != self.global_config:
            await self.async_unload()
            self.global_config = new_global_config
            self._controller_subentries = new_subentries
            self.controllers = new_controllers
            for controller in self.controllers.values():
                if controller.enabled:
                    await self._async_start_controller(controller)
            return

        previous_controllers = self.controllers
        removed_ids = set(previous_controllers) - set(new_controllers)
        changed_ids = {
            controller_id
            for controller_id, controller in new_controllers.items()
            if previous_controllers.get(controller_id) != controller
        }

        for controller_id in removed_ids | changed_ids:
            runtime = self._controller_runtimes.pop(controller_id, None)
            if runtime is not None:
                await runtime.async_stop()

        self._controller_subentries = new_subentries
        self.controllers = new_controllers
        self.global_config = new_global_config

        for controller_id, controller in self.controllers.items():
            if not controller.enabled:
                continue
            if controller_id in self._controller_runtimes:
                continue
            await self._async_start_controller(controller)

    async def _async_start_controller(self, controller: ControllerConfig) -> None:
        """Create and start one controller runtime."""
        runtime = ControllerRuntime(
            self.hass,
            self.global_config,
            controller,
            self.config_entry.entry_id,
        )
        await runtime.async_start()
        self._controller_runtimes[controller.controller_id] = runtime

    def get_controller(self, controller_id: str) -> ControllerConfig:
        """Return one stored controller or raise a clear error."""
        controller = self.controllers.get(controller_id)
        if controller is None:
            raise HomeAssistantError(f"Unknown controller id: {controller_id}")
        return controller

    async def async_set_controller_enabled(
        self, controller_id: str, enabled: bool
    ) -> None:
        """Persist the enabled state of a controller and reload runtimes."""
        controller = self.get_controller(controller_id)
        subentry = self._get_controller_subentry(controller_id)
        self.hass.config_entries.async_update_subentry(
            self.config_entry,
            subentry,
            data=_subentry_data_from_controller(replace(controller, enabled=enabled)),
        )

    async def async_force_turn_on(self, controller_id: str) -> None:
        """Force a controller target on."""
        controller = self.get_controller(controller_id)
        runtime = self._controller_runtimes.get(controller_id)
        if runtime is None:
            runtime = ControllerRuntime(
                self.hass,
                self.global_config,
                controller,
                self.config_entry.entry_id,
            )
        await runtime.async_force_turn_on()

    async def async_force_turn_off(self, controller_id: str) -> None:
        """Force a controller target off."""
        controller = self.get_controller(controller_id)
        runtime = self._controller_runtimes.get(controller_id)
        if runtime is None:
            runtime = ControllerRuntime(
                self.hass,
                self.global_config,
                controller,
                self.config_entry.entry_id,
            )
        await runtime.async_force_turn_off()

    async def async_reset_controller_timer(self, controller_id: str) -> None:
        """Reset the controller timer for an active runtime."""
        runtime = self._controller_runtimes.get(controller_id)
        if runtime is None:
            raise HomeAssistantError(
                f"Controller {controller_id} is disabled or not running"
            )
        await runtime.async_reset_timer()

    def _get_controller_subentry(self, controller_id: str) -> ConfigSubentry:
        """Return the subentry backing one controller or raise a clear error."""
        subentry = self._controller_subentries.get(controller_id)
        if subentry is None:
            raise HomeAssistantError(f"Unknown controller id: {controller_id}")
        return subentry

    def _build_controller_subentries(self) -> dict[str, ConfigSubentry]:
        """Return the current controller subentries keyed by controller id."""
        return {
            subentry.unique_id: subentry
            for subentry in self.config_entry.subentries.values()
            if subentry.subentry_type == SUBENTRY_TYPE_CONTROLLER
            and subentry.unique_id is not None
        }

    def _build_controllers(
        self, subentries: dict[str, ConfigSubentry]
    ) -> dict[str, ControllerConfig]:
        """Build controller configs from config-entry subentries."""
        controller_configs = [
            ControllerConfig.from_mapping(
                {
                    **dict(subentry.data),
                    "id": controller_id,
                    "name": subentry.title,
                }
            )
            for controller_id, subentry in subentries.items()
        ]
        return {
            controller.controller_id: controller for controller in controller_configs
        }


def _subentry_data_from_controller(controller: ControllerConfig) -> dict[str, object]:
    """Serialize only the fields stored inside controller subentries."""
    return {
        key: value
        for key, value in controller.as_dict().items()
        if key not in {"id", "name"}
    }