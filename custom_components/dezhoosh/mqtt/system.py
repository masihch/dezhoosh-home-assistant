"""System command MQTT transport for Dezhoosh.

Subscribes once to the ``dezhoosh/system/+`` wildcard, extracts the command
name from the topic, and hands the parsed payload off to the
:mod:`.system_commands` registry. This file only knows how to route bytes on
a wire to a command name - it has no idea what "ping" or any other command
actually means. See :mod:`.system_commands` to add new commands.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant

from ..const import TOPIC_SYSTEM_COMMAND_WILDCARD, TOPIC_SYSTEM_PREFIX
from .system_commands import registry as system_command_registry

_LOGGER = logging.getLogger(__name__)

# Commands that publish their response on a legacy/fixed topic instead of
# the generic "<command>/response" pattern, for backwards compatibility
# with firmware that already expects e.g. dezhoosh/system/pong.
_LEGACY_RESPONSE_TOPICS = {
    "ping": f"{TOPIC_SYSTEM_PREFIX}/pong",
}


class SystemCommandHandler:
    """Route incoming Dezhoosh system commands to the command registry."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._unsubscribe: Callable[[], None] | None = None

    def register_command(self, name: str, handler) -> None:
        """Register (or override) a system command handler at runtime.

        Kept on the transport class as a convenience so callers don't need
        to import :mod:`.system_commands` directly.
        """

        system_command_registry.register(name, handler)

    async def async_start(self) -> None:
        """Subscribe to the system command wildcard topic."""

        self._unsubscribe = await mqtt.async_subscribe(
            self.hass,
            TOPIC_SYSTEM_COMMAND_WILDCARD,
            self._async_command_received,
            qos=1,
        )

        _LOGGER.debug(
            "Dezhoosh system: subscribed to %s (commands: %s)",
            TOPIC_SYSTEM_COMMAND_WILDCARD,
            ", ".join(system_command_registry.commands),
        )

    async def async_stop(self) -> None:
        """Remove the system command subscription."""

        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    async def _async_command_received(self, msg) -> None:
        """Dispatch an incoming system command to its registered handler."""

        command = self._command_from_topic(msg.topic)
        if command is None:
            return

        # Ignore anything that looks like a response echoing back on the
        # wildcard (e.g. our own "<command>/response" or legacy "pong").
        if command.endswith("/response") or command in (
            t.rsplit("/", 1)[-1] for t in _LEGACY_RESPONSE_TOPICS.values()
        ):
            return

        if not system_command_registry.has(command):
            _LOGGER.debug(
                "Dezhoosh system: no handler for unknown command '%s' (topic=%s)",
                command,
                msg.topic,
            )
            return

        payload = self._parse_payload(msg.payload)

        _LOGGER.debug(
            "Dezhoosh system RX -> topic=%s command=%s payload=%s",
            msg.topic,
            command,
            payload,
        )

        response = await system_command_registry.dispatch(command, payload)
        if response is None:
            return

        response_topic = _LEGACY_RESPONSE_TOPICS.get(
            command, f"{TOPIC_SYSTEM_PREFIX}/{command}/response"
        )

        await mqtt.async_publish(
            self.hass,
            response_topic,
            json.dumps(response),
            qos=1,
            retain=False,
        )

        _LOGGER.debug(
            "Dezhoosh system TX -> topic=%s payload=%s",
            response_topic,
            response,
        )

    @staticmethod
    def _command_from_topic(topic: str) -> str | None:
        """Extract ``<command>`` from ``dezhoosh/system/<command>``."""

        prefix = f"{TOPIC_SYSTEM_PREFIX}/"
        if not topic.startswith(prefix):
            return None
        command = topic[len(prefix) :]
        return command or None

    @staticmethod
    def _parse_payload(raw: Any) -> dict[str, Any]:
        """Best-effort parse of an MQTT payload into a dict."""

        if not raw:
            return {}

        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return {}

        return data if isinstance(data, dict) else {}
