from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DATA_COORDINATOR,
    DOMAIN,
    PLATFORMS,
)

from .devices import DezhooshCoordinator
from .frontend import (
    async_register_frontend,
    async_unregister_frontend,
)
from .mqtt import DezhooshMQTT
from .mqtt.system_commands import registry as system_command_registry

_LOGGER = logging.getLogger(__name__)


async def async_setup(
    hass: HomeAssistant,
    config: dict,
) -> bool:
    """Initialize Dezhoosh."""

    hass.data.setdefault(DOMAIN, {})

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up a Dezhoosh config entry."""

    _LOGGER.debug("Starting Dezhoosh integration")

    # ------------------------------------------------------------
    # Frontend
    # ------------------------------------------------------------

    await async_register_frontend(hass)

    # ------------------------------------------------------------
    # MQTT
    # ------------------------------------------------------------

    mqtt_manager = DezhooshMQTT(hass)

    await mqtt_manager.async_start()

    # ------------------------------------------------------------
    # Coordinator
    # ------------------------------------------------------------

    coordinator = DezhooshCoordinator(
        hass,
        entry.entry_id,
    )

    await coordinator.async_start()

    # ------------------------------------------------------------
    # Shared Context
    # ------------------------------------------------------------

    system_command_registry.context["coordinator"] = coordinator

    # ------------------------------------------------------------
    # Runtime Store
    # ------------------------------------------------------------

    hass.data.setdefault(DOMAIN, {})

    hass.data[DOMAIN][entry.entry_id] = {
        "mqtt": mqtt_manager,
        DATA_COORDINATOR: coordinator,
    }

    # ------------------------------------------------------------
    # Platforms
    # ------------------------------------------------------------

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    _LOGGER.debug("Dezhoosh started successfully")

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload Dezhoosh."""

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    runtime = hass.data.get(DOMAIN, {}).pop(
        entry.entry_id,
        None,
    )

    if runtime:

        mqtt_manager = runtime.get("mqtt")

        if mqtt_manager:
            await mqtt_manager.async_stop()

        coordinator = runtime.get(DATA_COORDINATOR)

        if coordinator:
            await coordinator.async_stop()

    system_command_registry.context.pop(
        "coordinator",
        None,
    )

    if not hass.data.get(DOMAIN):
        await async_unregister_frontend(hass)

    return unload_ok
