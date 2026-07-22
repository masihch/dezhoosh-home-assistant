"""Switch platform for Dezhoosh.

Each discovered switch device exposes one switch entity per bridge/channel.
A single-bridge device produces one entity, double-bridge two, triple-bridge
three - all grouped under a single Home Assistant device so the custom card
can render them together.
"""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN, SIGNAL_ADD_SWITCH
from .device_manager import DezhooshCoordinator
from .models import DezhooshChannel, DezhooshDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dezhoosh switches and listen for future discoveries."""

    coordinator: DezhooshCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]

    known: set[str] = set()

    @callback
    def _add_device(device_id: str) -> None:
        device = coordinator.devices.get(device_id)
        if device is None or not device.is_switch:
            return

        entities: list[DezhooshSwitch] = []
        for channel in device.channels:
            unique = f"{device.device_id}_{channel.key}"
            if unique in known:
                continue
            known.add(unique)
            entities.append(DezhooshSwitch(coordinator, device, channel))

        if entities:
            async_add_entities(entities)

    # Register for future discoveries first.
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_ADD_SWITCH, _add_device)
    )

    # Then add any switches discovered before the platform loaded.
    for device_id in list(coordinator.devices):
        _add_device(device_id)


class DezhooshSwitch(SwitchEntity):
    """A single bridge/channel of a Dezhoosh switch device."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: DezhooshCoordinator,
        device: DezhooshDevice,
        channel: DezhooshChannel,
    ) -> None:
        self._coordinator = coordinator
        self._device_id = device.device_id
        self._channel = channel
        self._attr_unique_id = f"{device.device_id}_{channel.key}"
        self._attr_name = channel.name
        self._attr_device_info = device.device_info()

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
    def is_on(self) -> bool:
        state = self._coordinator.get_state(self._device_id)
        value = state.get(self._channel.key)
        if isinstance(value, str):
            return value.upper() == "ON"
        return bool(value)

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "device_id": self._device_id,
            "channel": self._channel.key,
            "bridge_index": self._channel.index,
        }

    async def async_turn_on(self, **kwargs) -> None:
        await self._coordinator.async_set_channel(
            self._device_id, self._channel.key, True
        )

    async def async_turn_off(self, **kwargs) -> None:
        await self._coordinator.async_set_channel(
            self._device_id, self._channel.key, False
        )
