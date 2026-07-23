from __future__ import annotations

from .client import CloudClient
from .mapper import CloudMapper
from .session import CloudSession

from ..const import API_LICENSE_ACTIVATE


class LicenseService:
    """License cloud service."""

    def __init__(self, client: CloudClient):
        self.client = client

    async def activate(
        self,
        license_key: str,
    ) -> CloudSession | dict:
        """Activate a Dezhoosh license."""

        response = await self.client.post(
            API_LICENSE_ACTIVATE,
            {
                "license": license_key,
            },
        )

        # Connection / server error
        if response.get("status") != "ok":
            return response

        # Convert JSON response into CloudSession
        return CloudMapper.from_json(response)