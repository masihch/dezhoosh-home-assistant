from __future__ import annotations

from homeassistant.config_entries import ConfigEntry

from .client import CloudClient
from .license import LicenseService
from .mapper import CloudMapper
from .session import CloudSession


class CloudManager:
    """Main Cloud Manager."""

    def __init__(self, base_url: str):
        self.client = CloudClient(base_url)

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
        """Return True if a valid cloud session exists."""
        return self.session is not None