"""System command definitions for Dezhoosh.

This is the "new architecture" for system-level commands: every command the
Dezhoosh backend/firmware can send to Home Assistant over
``dezhoosh/system/<command>`` is a small, self-contained handler registered
here, in :class:`SystemCommandRegistry`.

The MQTT transport layer (see :mod:`.system`) stays a dumb router: it
extracts ``<command>`` from the topic and calls
``registry.dispatch(command, payload)``. It never needs to know *what* a
command does. Adding a brand new system command (``restart``, ``identify``,
``get_diagnostics``, ...) means adding one function here with the
``@registry.command("name")`` decorator - nothing else changes.

Handlers receive the parsed JSON payload (``{}`` if the message had none or
failed to parse) and return either:

* a ``dict`` - published as the JSON response, or
* ``None`` - no response is published for this command.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from ..const import VERSION

_LOGGER = logging.getLogger(__name__)

CommandHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None]]


@dataclass
class SystemCommandRegistry:
    """Registry mapping a system command name to its async handler."""

    _handlers: dict[str, CommandHandler] = field(default_factory=dict)

    # Optional shared state handlers can read (e.g. {"coordinator": ...}).
    # Set once from __init__.py after the coordinator is created; handlers
    # that don't need it (like ping) simply never touch this.
    context: dict[str, Any] = field(default_factory=dict)

    def command(self, name: str) -> Callable[[CommandHandler], CommandHandler]:
        """Decorator: ``@registry.command("ping")`` registers a handler."""

        def _decorator(func: CommandHandler) -> CommandHandler:
            self.register(name, func)
            return func

        return _decorator

    def register(self, name: str, handler: CommandHandler) -> None:
        """Register (or override) the handler for *name*."""

        self._handlers[name] = handler

    def unregister(self, name: str) -> None:
        self._handlers.pop(name, None)

    def has(self, name: str) -> bool:
        return name in self._handlers

    @property
    def commands(self) -> list[str]:
        return sorted(self._handlers)

    async def dispatch(
        self, name: str, payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Run the handler registered for *name*, if any."""

        handler = self._handlers.get(name)
        if handler is None:
            _LOGGER.debug(
                "Dezhoosh system: no handler registered for command '%s'", name
            )
            return None

        try:
            return await handler(payload)
        except Exception:  # noqa: BLE001 - never let a bad command crash MQTT
            _LOGGER.exception(
                "Dezhoosh system: handler for '%s' raised an error", name
            )
            return None


# Global registry instance shared by the integration.
registry = SystemCommandRegistry()


def _with_correlation_id(
    payload: dict[str, Any], response: dict[str, Any]
) -> dict[str, Any]:
    """Echo back an ``id`` correlation field if the caller supplied one."""

    if isinstance(payload, dict) and "id" in payload:
        response["id"] = payload["id"]
    return response


# ---------------------------------------------------------------------------
# Built-in system commands
# ---------------------------------------------------------------------------


@registry.command("ping")
async def _handle_ping(payload: dict[str, Any]) -> dict[str, Any]:
    """Health handshake: reply with this integration's identity/version."""

    return _with_correlation_id(
        payload,
        {"status": "ok", "integration": "dezhoosh", "version": VERSION},
    )


@registry.command("get_info")
async def _handle_get_info(payload: dict[str, Any]) -> dict[str, Any]:
    """Return basic integration info - handy for firmware diagnostics."""

    return _with_correlation_id(
        payload,
        {"status": "ok", "integration": "dezhoosh", "version": VERSION},
    )


@registry.command("list_devices")
async def _handle_list_devices(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the device_ids currently known to the coordinator.

    Demonstrates a command that needs live integration state: it reads the
    coordinator through ``registry.context`` (set once in ``__init__.py``)
    instead of the transport layer having to know anything about devices.
    """

    coordinator = registry.context.get("coordinator")
    device_ids = sorted(coordinator.devices) if coordinator else []

    return _with_correlation_id(
        payload, {"status": "ok", "devices": device_ids, "count": len(device_ids)}
    )
