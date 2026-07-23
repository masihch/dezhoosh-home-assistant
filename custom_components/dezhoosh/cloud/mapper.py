from __future__ import annotations

from .session import CloudSession
from .models import (
    Customer,
    License,
    Home,
    Services,
    Features,
)


class CloudMapper:
    """Convert Cloud API responses into CloudSession objects."""

    @staticmethod
    def from_json(data: dict) -> CloudSession:
        """Create a CloudSession from Cloud API response."""

        return CloudSession(
            version=data.get("version", 1),

            customer=Customer(
                **(data.get("customer") or {})
            ),

            license=License(
                **(data.get("license") or {})
            ),

            home=Home(
                **(data.get("home") or {})
            ),

            services=Services(
                **(data.get("services") or {})
            ),

            features=Features(
                **(data.get("features") or {})
            ),
        )