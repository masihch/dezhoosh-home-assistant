"""Frontend registration for Dezhoosh.

Serves the compiled glass-morphism Lovelace cards as a static URL, registers
them as Lovelace resources (so users don't have to add them manually), and
installs the Dezhoosh green-blue theme into Home Assistant's theme registry.
"""

from __future__ import annotations

import logging
import os

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

URL_BASE = "/dezhoosh"
CARD_FILENAME = "dezhoosh-cards.js"
CARD_URL = f"{URL_BASE}/{CARD_FILENAME}"

THEME_NAME = "Dezhoosh Aqua"


def _www_path() -> str:
    return os.path.join(os.path.dirname(__file__), "www")


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register the card bundle and theme."""

    await _async_register_static_path(hass)
    await _async_register_lovelace_resource(hass)
    await _async_register_theme(hass)


async def async_unregister_frontend(hass: HomeAssistant) -> None:
    """Best-effort removal of the registered Lovelace resource."""

    try:
        resources = hass.data["lovelace"].resources
        if resources is None:
            return
        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True
        for item in list(resources.async_items()):
            if item.get("url", "").startswith(CARD_URL):
                await resources.async_delete_item(item["id"])
    except Exception:  # noqa: BLE001 - frontend cleanup is best effort
        _LOGGER.debug("Dezhoosh: could not remove Lovelace resource")


async def _async_register_static_path(hass: HomeAssistant) -> None:
    """Expose the bundled www/ directory under /dezhoosh."""

    path = _www_path()

    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(URL_BASE, path, cache_headers=False)]
        )
    except (ImportError, AttributeError):
        # Fallback for older Home Assistant releases.
        hass.http.register_static_path(URL_BASE, path, cache_headers=False)

    _LOGGER.debug("Dezhoosh: static path %s -> %s", URL_BASE, path)


async def _async_register_lovelace_resource(hass: HomeAssistant) -> None:
    """Auto-register the card JS as a Lovelace module resource."""

    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        _LOGGER.debug("Dezhoosh: lovelace not ready, skipping resource")
        return

    resources = getattr(lovelace, "resources", None)
    if resources is None:
        return

    if not resources.loaded:
        await resources.async_load()
        resources.loaded = True

    for item in resources.async_items():
        if item.get("url", "").startswith(CARD_URL):
            return  # already registered

    await resources.async_create_item(
        {"res_type": "module", "url": CARD_URL}
    )
    _LOGGER.debug("Dezhoosh: registered Lovelace resource %s", CARD_URL)


async def _async_register_theme(hass: HomeAssistant) -> None:
    """Register the Dezhoosh Aqua theme in Home Assistant's live theme store.

    Home Assistant keeps installed themes in ``hass.data[DATA_THEMES]`` (key
    ``"frontend_themes"``), populated by the ``frontend`` integration from
    ``configuration.yaml`` on startup. There is no public "install a theme"
    service, so we merge our theme dict directly into that store and fire
    ``EVENT_THEMES_UPDATED`` - the same event the frontend integration fires
    itself after ``frontend.reload_themes`` - so it shows up in the theme
    picker immediately, without a restart.

    ``frontend`` is a hard dependency in ``manifest.json``, so by the time
    this integration's ``async_setup_entry`` runs, the frontend component
    has already initialized ``hass.data[DATA_THEMES]``.
    """

    themes = _dezhoosh_theme()

    themes_key, themes_updated_event = _frontend_theme_keys()

    try:
        existing = hass.data.setdefault(themes_key, {})
        existing.update(themes)
    except Exception:  # noqa: BLE001 - never block setup on theme injection
        _LOGGER.warning("Dezhoosh: could not register the Dezhoosh Aqua theme")
        return

    if themes_updated_event is not None:
        hass.bus.async_fire(themes_updated_event)

    _LOGGER.debug("Dezhoosh: registered theme '%s'", THEME_NAME)


def _frontend_theme_keys():
    """Return the ``hass.data`` themes key and the themes-updated event.

    Both are resolved dynamically (rather than imported at module load
    time) so this integration keeps working across the HA versions that
    expose ``DATA_THEMES``/``EVENT_THEMES_UPDATED`` as plain strings and the
    newer versions that expose them as ``HassKey`` objects.
    """

    try:
        from homeassistant.components.frontend import DATA_THEMES
    except ImportError:
        DATA_THEMES = "frontend_themes"

    try:
        from homeassistant.const import EVENT_THEMES_UPDATED
    except ImportError:
        EVENT_THEMES_UPDATED = None

    return DATA_THEMES, EVENT_THEMES_UPDATED


def _dezhoosh_theme() -> dict:
    """Return the Dezhoosh Aqua theme definition (green-blue glass)."""

    return {
        THEME_NAME: {
            "primary-color": "#12b6a6",
            "accent-color": "#1fd4c3",
            "dark-primary-color": "#0e8f83",
            "light-primary-color": "#8ff0e6",
            "primary-background-color": "#071c22",
            "secondary-background-color": "#0c2a31",
            "card-background-color": "rgba(16, 46, 54, 0.72)",
            "primary-text-color": "#e6fffb",
            "secondary-text-color": "#8fd7cf",
            "text-primary-color": "#04141a",
            "divider-color": "rgba(31, 212, 195, 0.16)",
            "app-header-background-color": "rgba(7, 28, 34, 0.85)",
            "app-header-text-color": "#e6fffb",
            "sidebar-background-color": "rgba(7, 28, 34, 0.9)",
            "sidebar-icon-color": "#8fd7cf",
            "sidebar-selected-icon-color": "#1fd4c3",
            "sidebar-selected-text-color": "#1fd4c3",
            "switch-checked-color": "#1fd4c3",
            "switch-checked-track-color": "#12b6a6",
            "paper-item-icon-active-color": "#1fd4c3",
            "state-icon-active-color": "#1fd4c3",
            "ha-card-border-radius": "18px",
            "ha-card-box-shadow": "0 8px 30px rgba(4, 20, 26, 0.45)",
            "label-badge-background-color": "#0c2a31",
            "label-badge-text-color": "#e6fffb",
            "table-row-background-color": "#0c2a31",
            "table-row-alternative-background-color": "#0e333b",
        }
    }
