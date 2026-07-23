from __future__ import annotations

from ..const import API_LICENSE_ACTIVATE
from .client import CloudClient
from .mapper import CloudMapper
from .session import CloudSession


class LicenseService:
    """License cloud service."""

    def __init__(self, client: CloudClient):
        self.client = client

    async def activate(
        self,
        license_key: str,
    ) -> CloudSession | dict:
        """Activate a Dezhoosh license.

        Returns a CloudSession on success, or the raw response dict
        (always containing a "status" key) on failure.
        """

        response = await self.client.post(
            API_LICENSE_ACTIVATE,
            {
                "license": license_key,
            },
        )

        # CloudClient.post() always returns a dict, but stay defensive in
        # case that contract ever changes.
        if not isinstance(response, dict):
            return {"status": "error", "message": "invalid response from server"}

        # Connection / server error / rejected license
        if response.get("status") != "ok":
            return response

        # Convert JSON response into CloudSession
        return CloudMapper.from_json(response)
