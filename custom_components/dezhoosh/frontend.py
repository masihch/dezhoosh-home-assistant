"""Frontend registration for Dezhoosh.

Serves the compiled glass-morphism Lovelace cards as a static URL, registers
them as Lovelace resources, and loads Dezhoosh themes from the themes
directory into Home Assistant's live theme store.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

URL_BASE = "/dezhoosh"
CARD_FILENAME = "dezhoosh-cards.js"
CARD_URL = f"{URL_BASE}/{CARD_FILENAME}"


def _www_path() -> str:
    return os.path.join(os.path.dirname(__file__), "www")


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register the card bundle and themes."""

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
        _LOGGER.debug(
            "Dezhoosh: could not remove Lovelace resource"
        )


async def _async_register_static_path(hass: HomeAssistant) -> None:
    """Expose the bundled www/ directory under /dezhoosh."""

    path = _www_path()

    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    URL_BASE,
                    path,
                    cache_headers=False,
                )
            ]
        )

    except (ImportError, AttributeError):
        # Fallback for older Home Assistant releases.
        hass.http.register_static_path(
            URL_BASE,
            path,
            cache_headers=False,
        )

    _LOGGER.debug(
        "Dezhoosh: static path %s -> %s",
        URL_BASE,
        path,
    )


async def _async_register_lovelace_resource(
    hass: HomeAssistant,
) -> None:
    """Auto-register the card JS as a Lovelace module resource."""

    lovelace = hass.data.get("lovelace")

    if lovelace is None:
        _LOGGER.debug(
            "Dezhoosh: lovelace not ready, skipping resource"
        )
        return

    resources = getattr(lovelace, "resources", None)

    if resources is None:
        return

    if not resources.loaded:
        await resources.async_load()
        resources.loaded = True

    for item in resources.async_items():
        if item.get("url", "").startswith(CARD_URL):
            return

    await resources.async_create_item(
        {
            "res_type": "module",
            "url": CARD_URL,
        }
    )

    _LOGGER.debug(
        "Dezhoosh: registered Lovelace resource %s",
        CARD_URL,
    )


async def _async_register_theme(
    hass: HomeAssistant,
) -> None:
    """Load all Dezhoosh themes into Home Assistant."""

    themes = _load_themes()

    if not themes:
        _LOGGER.warning(
            "Dezhoosh: no valid themes found"
        )
        return

    themes_key, themes_updated_event = _frontend_theme_keys()

    try:
        existing = hass.data.setdefault(
            themes_key,
            {},
        )

        existing.update(themes)

    except Exception:  # noqa: BLE001
        _LOGGER.warning(
            "Dezhoosh: could not register Dezhoosh themes"
        )
        return

    if themes_updated_event is not None:
        hass.bus.async_fire(themes_updated_event)

    _LOGGER.info(
        "Dezhoosh: registered %d theme(s)",
        len(themes),
    )


def _load_themes() -> dict:
    """Load all YAML theme files from the themes directory."""

    themes_path = Path(__file__).parent / "themes"

    if not themes_path.exists():
        _LOGGER.warning(
            "Dezhoosh: themes directory does not exist: %s",
            themes_path,
        )
        return {}

    themes = {}

    # Load both .yaml and .yml files.
    theme_files = sorted(
        [
            *themes_path.glob("*.yaml"),
            *themes_path.glob("*.yml"),
        ]
    )

    for theme_file in theme_files:
        try:
            with theme_file.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = yaml.safe_load(file)

        except Exception as err:  # noqa: BLE001
            _LOGGER.error(
                "Dezhoosh: failed to read theme file %s: %s",
                theme_file,
                err,
            )
            continue

        if not isinstance(data, dict):
            _LOGGER.warning(
                "Dezhoosh: theme file %s does not contain a mapping",
                theme_file,
            )
            continue

        themes.update(data)

        _LOGGER.debug(
            "Dezhoosh: loaded theme file %s",
            theme_file.name,
        )

    return themes


def _frontend_theme_keys():
    """Return the hass.data themes key and the themes-updated event.

    Both are resolved dynamically rather than imported at module load time so
    this integration keeps working across Home Assistant versions that expose
    DATA_THEMES/EVENT_THEMES_UPDATED differently.
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