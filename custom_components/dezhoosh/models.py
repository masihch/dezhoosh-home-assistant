"""Data models for Dezhoosh discovered devices.

These lightweight dataclasses represent the normalized shape of a device once
its MQTT discovery payload has been parsed. Platforms (switch/sensor) consume
these models instead of raw JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .const import (
    BRIDGE_MODELS,
    DEVICE_TYPE_SENSOR,
    DEVICE_TYPE_SWITCH,
    MANUFACTURER,
)


@dataclass
class DezhooshChannel:
    """A single controllable channel (bridge/gang) of a switch device."""

    key: str
    name: str
    index: int


@dataclass
class DezhooshSensor:
    """A single sensor reading exposed by a device."""

    key: str
    name: str
    device_class: str | None = None
    unit: str | None = None
    icon: str | None = None


@dataclass
class DezhooshDevice:
    """Normalized representation of a discovered Dezhoosh device."""

    device_id: str
    name: str
    model: str
    device_type: str
    state_topic: str
    command_topic: str
    availability_topic: str | None = None
    sw_version: str | None = None
    channels: list[DezhooshChannel] = field(default_factory=list)
    sensors: list[DezhooshSensor] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def bridge_count(self) -> int:
        """Number of bridges for a switch model (1/2/3), else 0."""

        return BRIDGE_MODELS.get(self.model, len(self.channels))

    @property
    def is_switch(self) -> bool:
        return self.device_type == DEVICE_TYPE_SWITCH

    @property
    def is_sensor(self) -> bool:
        return self.device_type == DEVICE_TYPE_SENSOR

    def device_info(self) -> dict[str, Any]:
        """Return Home Assistant device registry info for this device."""

        return {
            "identifiers": {("dezhoosh", self.device_id)},
            "name": self.name,
            "manufacturer": MANUFACTURER,
            "model": self.model,
            "sw_version": self.sw_version,
        }
