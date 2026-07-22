"""Sensor platform for Dezhoosh.

Exposes any sensors declared in a device's discovery payload as sensor
entities grouped under the same Home Assistant device.
"""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN, SIGNAL_ADD_SENSOR
from .device_manager import DezhooshCoordinator
from .models import DezhooshDevice, DezhooshSensor

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dezhoosh sensors and listen for future discoveries."""

    coordinator: DezhooshCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]

    known: set[str] = set()

    @callback
    def _add_device(device_id: str) -> None:
        device = coordinator.devices.get(device_id)
        if device is None or not device.sensors:
            return

        entities: list[DezhooshSensorEntity] = []
        for sensor in device.sensors:
            unique = f"{device.device_id}_{sensor.key}"
            if unique in known:
                continue
            known.add(unique)
            entities.append(DezhooshSensorEntity(coordinator, device, sensor))

        if entities:
            async_add_entities(entities)

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_ADD_SENSOR, _add_device)
    )

    for device_id in list(coordinator.devices):
        _add_device(device_id)


class DezhooshSensorEntity(SensorEntity):
    """A single sensor reading from a Dezhoosh device."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: DezhooshCoordinator,
        device: DezhooshDevice,
        sensor: DezhooshSensor,
    ) -> None:
        self._coordinator = coordinator
        self._device_id = device.device_id
        self._sensor = sensor
        self._attr_unique_id = f"{device.device_id}_{sensor.key}"
        self._attr_name = sensor.name
        self._attr_device_info = device.device_info()
        self._attr_device_class = sensor.device_class
        self._attr_native_unit_of_measurement = sensor.unit
        if sensor.icon:
            self._attr_icon = sensor.icon

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._coordinator.async_add_listener(
                self._device_id, self.async_write_ha_state
            )
        )

    @property
    def available(self) -> bool:
        return self._device_id in self._coordinator.devices

    @property
    def native_value(self):
        state = self._coordinator.get_state(self._device_id)
        return state.get(self._sensor.key)

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "device_id": self._device_id,
            "sensor": self._sensor.key,
        }
