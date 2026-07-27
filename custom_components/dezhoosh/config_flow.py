"""Config flow for Dezhoosh.

This integration has nothing to configure - it only needs the MQTT
integration (already a hard dependency in manifest.json) and picks up
every device automatically via MQTT discovery. So the flow is just a
single confirmation step: the user clicks "Submit" once to add it, no
license key or any other input required.
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries

from .const import DOMAIN


class DezhooshConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dezhoosh."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Single confirmation step - no user input needed."""

        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="Dezhoosh", data={})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
        )
