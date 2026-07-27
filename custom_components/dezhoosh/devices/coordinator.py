"""Device coordinator for Dezhoosh.

Owns the lifecycle of discovered devices: keeps their normalized models,
tracks per-channel/sensor runtime state from MQTT ``state`` topics, publishes
commands to ``set`` topics, and notifies the switch/sensor platforms via the
dispatcher when new devices appear.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from ..const import (
    SIGNAL_ADD_SENSOR,
    SIGNAL_ADD_SWITCH,
)
from .discovery import DezhooshDiscovery
from .models import DezhooshDevice

_LOGGER = logging.getLogger(__name__)


class DezhooshCoordinator:
    """Central registry and runtime state for Dezhoosh devices."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id

        self.devices: dict[str, DezhooshDevice] = {}
        # device_id -> {channel_or_sensor_key: value}
        self._state: dict[str, dict[str, Any]] = {}
        # device_id -> list of update listeners
        self._listeners: dict[str, list[Callable[[], None]]] = {}
        # device_id -> mqtt unsubscribe for its state topic
        self._state_unsubs: dict[str, Callable[[], None]] = {}

        self._discovery = DezhooshDiscovery(
            hass,
            on_device=self.async_device_discovered,
            on_remove=self.async_device_removed,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_start(self) -> None:
        await self._discovery.async_start()

    async def async_stop(self) -> None:
        await self._discovery.async_stop()
        for unsub in self._state_unsubs.values():
            unsub()
        self._state_unsubs.clear()

    # ------------------------------------------------------------------
    # Discovery callbacks
    # ------------------------------------------------------------------

    async def async_device_discovered(self, device: DezhooshDevice) -> None:
        """Register (or update) a discovered device and push it to platforms."""

        is_new = device.device_id not in self.devices
        self.devices[device.device_id] = device
        self._state.setdefault(device.device_id, {})

        await self._async_subscribe_state(device)

        if not is_new:
            # Existing device re-announced; refresh listeners.
            self._notify(device.device_id)
            return

        if device.is_switch:
            async_dispatcher_send(
                self.hass, SIGNAL_ADD_SWITCH, device.device_id
            )
        if device.sensors:
            async_dispatcher_send(
                self.hass, SIGNAL_ADD_SENSOR, device.device_id
            )

    async def async_device_removed(self, device_id: str) -> None:
        """Handle removal of a device (empty discovery payload)."""

        self.devices.pop(device_id, None)
        self._state.pop(device_id, None)
        unsub = self._state_unsubs.pop(device_id, None)
        if unsub:
            unsub()
        self._notify(device_id)

    # ------------------------------------------------------------------
    # State handling
    # ------------------------------------------------------------------

    async def _async_subscribe_state(self, device: DezhooshDevice) -> None:
        """Subscribe to a device's state topic (idempotent)."""

        if device.device_id in self._state_unsubs:
            return

        @callback
        def _message(msg) -> None:
            self._handle_state(device.device_id, msg.payload)

        unsub = await mqtt.async_subscribe(
            self.hass,
            device.state_topic,
            _message,
            qos=1,
        )
        self._state_unsubs[device.device_id] = unsub

    def _handle_state(self, device_id: str, payload: Any) -> None:
        """Merge an incoming state payload into the device state."""

        try:
            data = json.loads(payload)
        except (ValueError, TypeError):
            return

        if not isinstance(data, dict):
            return

        self._state.setdefault(device_id, {}).update(data)
        self._notify(device_id)

    def get_state(self, device_id: str) -> dict[str, Any]:
        return self._state.get(device_id, {})

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def async_set_channel(
        self, device_id: str, channel_key: str, value: bool
    ) -> None:
        """Publish a command to set a channel on/off."""

        device = self.devices.get(device_id)
        if device is None:
            return

        payload = {channel_key: "ON" if value else "OFF"}

        await mqtt.async_publish(
            self.hass,
            device.command_topic,
            json.dumps(payload),
            qos=1,
            retain=False,
        )

        # Optimistically update local state.
        self._state.setdefault(device_id, {})[channel_key] = "ON" if value else "OFF"
        self._notify(device_id)

    # ------------------------------------------------------------------
    # Listener registration (used by entities)
    # ------------------------------------------------------------------

    def async_add_listener(
        self, device_id: str, update: Callable[[], None]
    ) -> Callable[[], None]:
        """Register an entity update callback for a device."""

        self._listeners.setdefault(device_id, []).append(update)

        def _remove() -> None:
            listeners = self._listeners.get(device_id)
            if listeners and update in listeners:
                listeners.remove(update)

        return _remove

    def _notify(self, device_id: str) -> None:
        for update in list(self._listeners.get(device_id, [])):
            update()
