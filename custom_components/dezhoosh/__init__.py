from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DATA_COORDINATOR, DOMAIN, PLATFORMS
from .device_manager import DezhooshCoordinator
from .mqtt import DezhooshMQTT
from .frontend import async_register_frontend, async_unregister_frontend
from .system_commands import registry as system_command_registry

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Initialize Dezhoosh."""

    _LOGGER.debug("Dezhoosh: async_setup()")

    hass.data.setdefault(DOMAIN, {})

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Dezhoosh."""

    _LOGGER.debug("Dezhoosh: async_setup_entry()")

    # Register the glass-morphism Lovelace cards + Dezhoosh theme.
    await async_register_frontend(hass)

    # Thin MQTT transport (owns the system ping/pong handshake).
    mqtt_manager = DezhooshMQTT(hass)
    await mqtt_manager.async_start()

    # Device coordinator (owns discovery + runtime state).
    coordinator = DezhooshCoordinator(hass, entry.entry_id)
    await coordinator.async_start()

    # Let system commands (e.g. "list_devices") reach the coordinator
    # without the MQTT transport layer needing to know it exists.
    system_command_registry.context["coordinator"] = coordinator

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "mqtt": mqtt_manager,
        DATA_COORDINATOR: coordinator,
        "license": entry.data.get("license"),
        "customer": entry.data.get("customer", {}),
        "license_info": entry.data.get("license_info", {}),
        "services": entry.data.get("services", {}),
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload Dezhoosh and clean up its MQTT subscription."""

    _LOGGER.debug("Dezhoosh: async_unload_entry()")

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )

    entry_data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    if entry_data:
        mqtt_manager = entry_data.get("mqtt")
        if mqtt_manager:
            await mqtt_manager.async_stop()

        coordinator = entry_data.get(DATA_COORDINATOR)
        if coordinator:
            await coordinator.async_stop()
            system_command_registry.context.pop("coordinator", None)

    if not hass.data.get(DOMAIN):
        await async_unregister_frontend(hass)

    return unload_ok
