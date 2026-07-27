from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .system import SystemCommandHandler

_LOGGER = logging.getLogger(__name__)


class DezhooshMQTT:
    """Thin MQTT transport coordinator for Dezhoosh.

    Delegates the system protocol to :class:`~.system.SystemCommandHandler`.
    Device discovery and runtime traffic are owned by the coordinator
    (see :mod:`..devices.coordinator`).
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.system = SystemCommandHandler(hass)

    async def async_start(self) -> None:
        """Start all MQTT subscriptions owned by the transport layer."""

        await self.system.async_start()
        _LOGGER.debug("Dezhoosh MQTT: transport started")

    async def async_stop(self) -> None:
        """Tear down MQTT subscriptions."""

        await self.system.async_stop()
        _LOGGER.debug("Dezhoosh MQTT: transport stopped")
