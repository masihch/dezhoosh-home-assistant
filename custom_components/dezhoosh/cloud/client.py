from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class CloudClient:
    """HTTP client for Dezhoosh Cloud."""

    def __init__(
        self,
        base_url: str,
        timeout: int = 10,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def post(
        self,
        endpoint: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Send POST request."""

        url = f"{self._base_url}/{endpoint.lstrip('/')}"

        try:

            timeout = aiohttp.ClientTimeout(
                total=self._timeout,
            )

            async with aiohttp.ClientSession(
                timeout=timeout,
            ) as session:

                async with session.post(
                    url,
                    json=payload,
                ) as response:

                    data = await response.json(content_type=None)

                    _LOGGER.debug(
                        "Cloud POST %s -> %s",
                        url,
                        data,
                    )

                    return data

        except asyncio.TimeoutError:

            _LOGGER.error(
                "Cloud timeout -> %s",
                url,
            )

            return {
                "status": "timeout",
            }

        except Exception as err:

            _LOGGER.exception(err)

            return {
                "status": "error",
                "message": str(err),
            }
