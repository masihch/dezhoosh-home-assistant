from __future__ import annotations

from .client import CloudClient


class LicenseService:
    """License cloud service."""

    def __init__(
        self,
        client: CloudClient,
    ):
        self.client = client

    async def activate(
        self,
        license_key: str,
    ) -> dict:

        return await self.client.post(
            "check.php",
            {
                "license": license_key,
            },
        )