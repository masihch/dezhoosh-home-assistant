from __future__ import annotations

import json
import logging

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant

from .const import (
    TOPIC_SYSTEM_PING,
    TOPIC_SYSTEM_PONG,
    VERSION,
)

_LOGGER = logging.getLogger(__name__)


class DezhooshMQTT:
    """MQTT Manager for Dezhoosh."""

    def __init__(self, hass: HomeAssistant):
        self.hass = hass

    async def async_subscribe(self):
        """Subscribe to Dezhoosh MQTT topics."""

        await mqtt.async_subscribe(
            self.hass,
            TOPIC_SYSTEM_PING,
            self.async_ping_received,
            qos=1,
        )

        _LOGGER.warning(
            "Dezhoosh MQTT: subscribed to %s",
            TOPIC_SYSTEM_PING,
        )

    async def async_ping_received(self, msg):
        """Handle incoming Ping message."""

        _LOGGER.warning(
            "MQTT RX -> topic=%s payload=%s",
            msg.topic,
            msg.payload,
        )

        await self.async_publish_pong()

    async def async_publish_pong(self):
        """Publish Pong response."""

        payload = {
            "status": "ok",
            "integration": "dezhoosh",
            "version": VERSION,
        }

        await mqtt.async_publish(
            self.hass,
            TOPIC_SYSTEM_PONG,
            json.dumps(payload),
            qos=1,
            retain=False,
        )

        _LOGGER.warning(
            "MQTT TX -> topic=%s payload=%s",
            TOPIC_SYSTEM_PONG,
            payload,
        )