"""Config flow for Dezhoosh."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries

from .cloud.client import CloudClient
from .cloud.license import LicenseService
from .const import (
    CLOUD_BASE_URL,
    DOMAIN,
)


class DezhooshConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dezhoosh."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""

        # Allow only one Dezhoosh integration
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors = {}

        if user_input is not None:

            client = CloudClient(CLOUD_BASE_URL)

            license_service = LicenseService(client)

            result = await license_service.activate(
                user_input["license"],
            )

            if result.get("status") == "ok":

                return self.async_create_entry(
                    title="Dezhoosh",
                    data={
                        "license": user_input["license"],
                        "customer": result.get("customer", {}),
                        "license_info": result.get("license", {}),
                        "services": result.get("services", {}),
                    },
                )

            errors["base"] = "invalid_license"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("license"): str,
                }
            ),
            errors=errors,
        )