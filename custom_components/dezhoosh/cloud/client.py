from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class CloudClient:
    """HTTP client for Dezhoosh Cloud.

    When a Home Assistant-managed aiohttp session is supplied (the normal
    case - see CloudManager), requests share HA's connection pool instead
    of opening a fresh TCP/TLS connection per call, and that session is
    never closed here (HA owns its lifecycle). If no session is supplied,
    falls back to a private, self-closing session per request - useful
    for standalone use/tests outside of a running Home Assistant.
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 10,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = session

    async def post(
        self,
        endpoint: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a POST request. Always returns a dict, never raises."""

        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        timeout = aiohttp.ClientTimeout(total=self._timeout)

        try:
            if self._session is not None:
                async with self._session.post(
                    url, json=payload, timeout=timeout
                ) as response:
                    return await self._parse(response, url)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as response:
                    return await self._parse(response, url)

        except asyncio.TimeoutError:
            _LOGGER.error("Cloud timeout -> %s", url)
            return {"status": "timeout"}

        except Exception as err:  # noqa: BLE001 - never let a bad response crash the caller
            _LOGGER.exception("Cloud request failed -> %s", url)
            return {"status": "error", "message": str(err)}

    @staticmethod
    async def _parse(response: aiohttp.ClientResponse, url: str) -> dict[str, Any]:
        """Parse a response, guaranteeing a dict is always returned."""

        data = await response.json(content_type=None)

        _LOGGER.debug("Cloud POST %s -> %s", url, data)

        if not isinstance(data, dict):
            _LOGGER.warning(
                "Cloud POST %s returned a non-object JSON response: %r", url, data
            )
            return {"status": "error", "message": "non-object response"}

        return data
