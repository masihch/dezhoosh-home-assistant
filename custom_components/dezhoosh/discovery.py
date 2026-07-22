"""MQTT discovery parsing for Dezhoosh.

Listens on ``dezhoosh/discovery/+/config`` and converts retained discovery
payloads into :class:`~.models.DezhooshDevice` instances, then hands them to
the coordinator.

Expected discovery payload (JSON), for example a triple-bridge switch::

    {
      "id": "sw_kitchen_01",
      "name": "Kitchen Switch",
      "type": "switch",
      "model": "triple_bridge",
      "sw_version": "1.2.0",
      "state_topic": "dezhoosh/sw_kitchen_01/state",
      "command_topic": "dezhoosh/sw_kitchen_01/set",
      "availability_topic": "dezhoosh/sw_kitchen_01/status",
      "channels": [
        {"key": "l1", "name": "Left"},
        {"key": "l2", "name": "Middle"},
        {"key": "l3", "name": "Right"}
      ],
      "sensors": [
        {"key": "temperature", "name": "Temperature",
         "device_class": "temperature", "unit": "°C"}
      ]
    }

An empty payload on a discovery topic removes the device.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant

from .const import (
    BRIDGE_MODELS,
    DEVICE_TYPE_SENSOR,
    DEVICE_TYPE_SWITCH,
    MODEL_SINGLE_BRIDGE,
    TOPIC_DISCOVERY_WILDCARD,
)
from .models import DezhooshChannel, DezhooshDevice, DezhooshSensor

_LOGGER = logging.getLogger(__name__)


class DezhooshDiscovery:
    """Subscribe to discovery topics and emit normalized devices."""

    def __init__(
        self,
        hass: HomeAssistant,
        on_device: Callable[[DezhooshDevice], Any],
        on_remove: Callable[[str], Any],
    ) -> None:
        self.hass = hass
        self._on_device = on_device
        self._on_remove = on_remove
        self._unsubscribe: Callable[[], None] | None = None

    async def async_start(self) -> None:
        """Subscribe to the discovery wildcard topic."""

        self._unsubscribe = await mqtt.async_subscribe(
            self.hass,
            TOPIC_DISCOVERY_WILDCARD,
            self._async_discovery_received,
            qos=1,
        )

        _LOGGER.debug(
            "Dezhoosh discovery: subscribed to %s",
            TOPIC_DISCOVERY_WILDCARD,
        )

    async def async_stop(self) -> None:
        """Remove the discovery subscription."""

        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    async def _async_discovery_received(self, msg) -> None:
        """Handle a discovery message."""

        device_id = self._device_id_from_topic(msg.topic)
        if device_id is None:
            return

        payload = (msg.payload or "").strip() if isinstance(msg.payload, str) else msg.payload

        if not payload:
            _LOGGER.debug("Dezhoosh discovery: removing %s", device_id)
            await _maybe_await(self._on_remove(device_id))
            return

        try:
            data = json.loads(payload)
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Dezhoosh discovery: invalid JSON on %s", msg.topic
            )
            return

        device = self._parse_device(device_id, data)
        if device is None:
            return

        _LOGGER.debug(
            "Dezhoosh discovery: %s (%s, %s)",
            device.device_id,
            device.device_type,
            device.model,
        )
        await _maybe_await(self._on_device(device))

    @staticmethod
    def _device_id_from_topic(topic: str) -> str | None:
        """Extract ``<device_id>`` from ``dezhoosh/discovery/<id>/config``."""

        parts = topic.split("/")
        # dezhoosh / discovery / <id> / config
        if len(parts) >= 4 and parts[-1] == "config":
            return parts[-2]
        return None

    def _parse_device(
        self, device_id: str, data: dict[str, Any]
    ) -> DezhooshDevice | None:
        """Convert a discovery dict into a :class:`DezhooshDevice`."""

        if not isinstance(data, dict):
            return None

        device_type = data.get("type", DEVICE_TYPE_SWITCH)
        model = data.get("model", MODEL_SINGLE_BRIDGE)
        name = data.get("name") or device_id

        state_topic = data.get("state_topic") or f"dezhoosh/{device_id}/state"
        command_topic = data.get("command_topic") or f"dezhoosh/{device_id}/set"

        channels = self._parse_channels(data, model)
        sensors = self._parse_sensors(data)

        if device_type == DEVICE_TYPE_SWITCH and not channels:
            _LOGGER.warning(
                "Dezhoosh discovery: switch %s has no channels", device_id
            )

        return DezhooshDevice(
            device_id=device_id,
            name=name,
            model=model,
            device_type=device_type,
            state_topic=state_topic,
            command_topic=command_topic,
            availability_topic=data.get("availability_topic"),
            sw_version=data.get("sw_version"),
            channels=channels,
            sensors=sensors,
            raw=data,
        )

    @staticmethod
    def _parse_channels(
        data: dict[str, Any], model: str
    ) -> list[DezhooshChannel]:
        """Parse channels, deriving defaults from the bridge model."""

        raw_channels = data.get("channels")
        channels: list[DezhooshChannel] = []

        if isinstance(raw_channels, list) and raw_channels:
            for index, item in enumerate(raw_channels):
                if not isinstance(item, dict):
                    continue
                key = str(item.get("key") or f"l{index + 1}")
                channels.append(
                    DezhooshChannel(
                        key=key,
                        name=item.get("name") or f"Bridge {index + 1}",
                        index=index,
                    )
                )
            return channels

        # No explicit channels: derive from the model (1/2/3 bridges).
        count = BRIDGE_MODELS.get(model, 0)
        for index in range(count):
            channels.append(
                DezhooshChannel(
                    key=f"l{index + 1}",
                    name=f"Bridge {index + 1}",
                    index=index,
                )
            )
        return channels

    @staticmethod
    def _parse_sensors(data: dict[str, Any]) -> list[DezhooshSensor]:
        """Parse sensor definitions from a discovery payload."""

        raw_sensors = data.get("sensors")
        sensors: list[DezhooshSensor] = []

        if not isinstance(raw_sensors, list):
            return sensors

        for index, item in enumerate(raw_sensors):
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or f"sensor_{index + 1}")
            sensors.append(
                DezhooshSensor(
                    key=key,
                    name=item.get("name") or key,
                    device_class=item.get("device_class"),
                    unit=item.get("unit") or item.get("unit_of_measurement"),
                    icon=item.get("icon"),
                )
            )
        return sensors


async def _maybe_await(result: Any) -> None:
    """Await *result* if it is awaitable."""

    if hasattr(result, "__await__"):
        await result
