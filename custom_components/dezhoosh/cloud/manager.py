from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..const import LICENSE_STATE_ACTIVE
from .client import CloudClient
from .license import LicenseService
from .mapper import CloudMapper
from .session import CloudSession


class CloudManager:
    """Main Cloud Manager."""

    def __init__(self, base_url: str, hass: HomeAssistant | None = None):
        # Reuse Home Assistant's shared aiohttp session when available
        # (normal runtime use); fall back to a private one otherwise
        # (e.g. standalone scripts/tests outside of HA).
        session = async_get_clientsession(hass) if hass is not None else None

        self.client = CloudClient(base_url, session=session)

        self.license = LicenseService(self.client)

        self.session: CloudSession | None = None

    # ---------------------------------------------------------------------
    # Session
    # ---------------------------------------------------------------------

    async def restore(self, entry: ConfigEntry) -> None:
        """Restore CloudSession from Home Assistant ConfigEntry."""

        self.session = CloudMapper.from_json(
            {
                "version": entry.data.get("cloud_version", 1),
                "customer": entry.data.get("customer", {}),
                "license": entry.data.get("license", {}),
                "services": entry.data.get("services", {}),
                "home": entry.data.get("home", {}),
                "features": entry.data.get("features", {}),
            }
        )

    # ---------------------------------------------------------------------
    # Properties
    # ---------------------------------------------------------------------

    @property
    def customer(self):
        """Return customer information."""
        return self.session.customer if self.session else None

    @property
    def license_info(self):
        """Return license information."""
        return self.session.license if self.session else None

    @property
    def services(self):
        """Return enabled cloud services."""
        return self.session.services if self.session else None

    @property
    def home(self):
        """Return home information."""
        return self.session.home if self.session else None

    @property
    def features(self):
        """Return enabled features."""
        return self.session.features if self.session else None

    @property
    def version(self):
        """Return cloud protocol version."""
        return self.session.version if self.session else None

    @property
    def is_authenticated(self) -> bool:
        """Return True only if a currently-active license session exists.

        A CloudSession object existing is NOT enough on its own - restore()
        always produces one, even from empty/missing config-entry data. A
        license is only actually usable if it has a key AND the cloud
        reported its state as active.
        """
        if self.session is None:
            return False

        return bool(self.session.license.key) and (
            self.session.license.state == LICENSE_STATE_ACTIVE
        )
