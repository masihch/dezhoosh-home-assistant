"""Device discovery, models, and coordination for Dezhoosh.

Groups everything about *what devices exist and what state they're in*:

- ``discovery.py`` - listens on ``dezhoosh/discovery/+/config`` and parses
  retained MQTT discovery payloads into normalized device objects.
- ``models.py`` - the normalized dataclasses those payloads get turned into
  (``DezhooshDevice``, ``DezhooshChannel``, ``DezhooshSensor``).
- ``coordinator.py`` - ties the two together at runtime: owns the list of
  known devices, tracks their live state from ``state`` topics, publishes
  commands to ``set`` topics, and notifies entities when something changes.

Other modules (``__init__.py``, ``switch.py``, ``sensor.py``) should import
from this package directly - e.g. ``from .devices import DezhooshCoordinator``
- rather than reaching into ``devices.coordinator``/``devices.models``
individually.
"""

from .coordinator import DezhooshCoordinator
from .models import DezhooshChannel, DezhooshDevice, DezhooshSensor

__all__ = [
    "DezhooshCoordinator",
    "DezhooshChannel",
    "DezhooshDevice",
    "DezhooshSensor",
]
