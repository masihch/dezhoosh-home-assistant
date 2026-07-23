from __future__ import annotations

from dataclasses import dataclass, field


# =====================================================================
# Customer
# =====================================================================

@dataclass(slots=True)
class Customer:
    id: str = ""
    name: str = ""


# =====================================================================
# License
# =====================================================================

@dataclass(slots=True)
class License:
    key: str = ""
    state: str = ""
    plan: str = ""
    expires: str = ""


# =====================================================================
# Home
# =====================================================================

@dataclass(slots=True)
class Home:
    id: str = ""
    name: str = ""


# =====================================================================
# Services
# =====================================================================

@dataclass(slots=True)
class Services:
    cloud: bool = False
    firmware: bool = False
    sms: bool = False
    notifications: bool = False


# =====================================================================
# Features
# =====================================================================

@dataclass(slots=True)
class Features:
    remote_access: bool = False
    ai: bool = False
    telegram: bool = False