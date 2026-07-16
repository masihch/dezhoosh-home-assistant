from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Initialize Dezhoosh integration."""

    _LOGGER.warning("Dezhoosh: async_setup()")

    hass.data.setdefault(DOMAIN, {})

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Dezhoosh from a config entry."""

    _LOGGER.warning("Dezhoosh: async_setup_entry()")

    hass.data.setdefault(DOMAIN, {})

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload Dezhoosh."""

    _LOGGER.warning("Dezhoosh: async_unload_entry()")

    return True