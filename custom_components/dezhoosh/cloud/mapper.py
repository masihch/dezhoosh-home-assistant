"""Convert raw Cloud API JSON into CloudSession dataclasses.

Deliberately defensive: the whole point of a mapper layer is to isolate
the rest of the integration from whatever the server actually sends. A
stray/renamed field on the server side degrades gracefully (the field is
ignored and logged) instead of crashing the entire license-activation
flow with a raw TypeError.
"""

from __future__ import annotations

import logging
from dataclasses import fields
from typing import Any, TypeVar

from .models import Customer, Features, Home, License, Services
from .session import CloudSession

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


def _instantiate(cls: type[T], data: Any) -> T:
    """Build *cls* from *data*, tolerating unknown/missing/malformed input.

    - Unknown keys are dropped (and logged) rather than raising.
    - A non-dict value (None, a list, a string, ...) falls back to an
      all-defaults instance instead of raising.
    """

    if not isinstance(data, dict):
        if data is not None:
            _LOGGER.warning(
                "Dezhoosh cloud: expected an object for %s, got %s - using defaults",
                cls.__name__,
                type(data).__name__,
            )
        data = {}

    known = {f.name for f in fields(cls)}
    unexpected = set(data) - known
    if unexpected:
        _LOGGER.warning(
            "Dezhoosh cloud: ignoring unexpected field(s) %s in the %s response",
            ", ".join(sorted(unexpected)),
            cls.__name__,
        )

    filtered = {key: value for key, value in data.items() if key in known}

    try:
        return cls(**filtered)
    except TypeError as err:
        # A known key had a value of a completely wrong shape/type.
        _LOGGER.warning(
            "Dezhoosh cloud: could not build %s from cloud response (%s) - using defaults",
            cls.__name__,
            err,
        )
        return cls()


class CloudMapper:
    """Convert Cloud API responses into CloudSession objects."""

    @staticmethod
    def from_json(data: dict) -> CloudSession:
        """Create a CloudSession from a Cloud API response.

        Never raises - any malformed/unexpected input falls back to safe
        defaults for the affected section instead of aborting the whole
        activation/restore flow.
        """

        if not isinstance(data, dict):
            data = {}

        try:
            version = int(data.get("version", 1))
        except (TypeError, ValueError):
            version = 1

        return CloudSession(
            version=version,
            customer=_instantiate(Customer, data.get("customer")),
            license=_instantiate(License, data.get("license")),
            home=_instantiate(Home, data.get("home")),
            services=_instantiate(Services, data.get("services")),
            features=_instantiate(Features, data.get("features")),
        )
