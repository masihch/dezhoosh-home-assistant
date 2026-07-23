from __future__ import annotations

from dataclasses import dataclass, field

from .models import (
    Customer,
    License,
    Home,
    Services,
    Features,
)


@dataclass(slots=True)
class CloudSession:
    customer: Customer = field(default_factory=Customer)

    license: License = field(default_factory=License)

    home: Home = field(default_factory=Home)

    services: Services = field(default_factory=Services)

    features: Features = field(default_factory=Features)

    version: int = 1