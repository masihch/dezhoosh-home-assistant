"""Config flow for Dezhoosh."""

from __future__ import annotations

from dataclasses import asdict

import voluptuous as vol

from homeassistant import config_entries

from .cloud.manager import CloudManager
from .cloud.session import CloudSession
from .const import (
    CLOUD_BASE_URL,
    CONF_CLOUD_VERSION,
    CONF_CUSTOMER,
    CONF_FEATURES,
    CONF_HOME,
    CONF_LICENSE,
    CONF_LICENSE_KEY,
    CONF_SERVICES,
    DOMAIN,
)


class DezhooshConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dezhoosh."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle first setup step."""

        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors = {}

        if user_input is not None:

            cloud = CloudManager(CLOUD_BASE_URL)

            session = await cloud.license.activate(
                user_input["license"]
            )

            if isinstance(session, CloudSession):

                return self.async_create_entry(
                    title="Dezhoosh",
                    data={
                        CONF_LICENSE_KEY: user_input["license"],
                        CONF_CLOUD_VERSION: session.version,
                        CONF_CUSTOMER: asdict(session.customer),
                        CONF_LICENSE: asdict(session.license),
                        CONF_SERVICES: asdict(session.services),
                        CONF_HOME: asdict(session.home),
                        CONF_FEATURES: asdict(session.features),
                    },
                )

            status = session.get("status")

            if status in ("timeout", "error"):
                errors["base"] = "cannot_connect"
            else:
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