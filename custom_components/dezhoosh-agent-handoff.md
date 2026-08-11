# Dezhoosh Home Assistant Integration — Full Project Handoff

This document is a complete handoff of the `dezhoosh` custom Home Assistant
integration, written for another AI coding agent (or developer) to pick up
development from exactly where it stands today. It contains: the product/
business context, every architecture decision made and *why*, the full
current source code, what has been tested and how, and what's explicitly
still pending. Nothing here is guessed — the source section was generated
directly from the actual project files, and every file listed was verified
minutes before this document was produced by installing a real `homeassistant`
pip package and successfully importing every module.

## 1. What this project is

Dezhoosh is a smart-home hardware brand (Iran-based, related company:
TechnoRobot, technorobot.ir) shipping MQTT-based smart switches (1/2/3-gang
"bridge" switches) and sensors. This repo is the custom Home Assistant
integration (`custom_components/dezhoosh/`) that makes those devices show
up automatically in Home Assistant, with custom glass-morphism Lovelace
cards and a matching theme.

**Distribution model:** deployed manually today (the developer copies the
`dezhoosh` folder via Samba directly into `custom_components/` on a
Raspberry Pi running HAOS — no HACS yet, though HACS publishing was
discussed as a near-term goal; a `hacs.json` was drafted in an earlier
iteration but is not currently part of the repo). No automated update
mechanism exists yet for manual installs — every update means re-copying
files and restarting HA.

## 2. Critical architecture decision: this integration is intentionally hardware-only, license-free, and fully offline-capable

This is the single most important piece of context for continuing work
correctly. Earlier development iterations built a full cloud/license system
into this integration (a `cloud/` sub-package with `CloudManager`,
`LicenseService`, a `check.php` server-side activation endpoint, Config Flow
license-key entry, etc.). **That was deliberately and completely removed.**

The reasoning, decided explicitly with the product owner:

- Requiring an online license just to use locally-owned MQTT hardware hurt
  user trust and added an unnecessary internet dependency to something that
  is fundamentally local (`iot_class: local_push` — devices talk to HA over
  a local MQTT broker, no cloud round-trip needed for basic operation).
- The original reason for wanting license-gated device registration
  (recovering a customer's device list from the vendor's server if their
  Pi/SD card died) was recognized as redundant: Home Assistant's own native
  Backup system (Settings → System → Backups, and the `BackupAgent`
  platform for cloud backup destinations since HA 2025.1) already solves
  that problem natively — no need to duplicate it server-side.
- The product owner also operates in Iran, where reliable internet access
  cannot be assumed, reinforcing the "hardware must work with zero internet
  dependency" requirement. (Separately discussed: HAOS SD card raw-disk
  cloning as an offline deployment strategy for field installs — not part
  of this repo, but relevant operational context.)

**Resulting product split (decided, not yet built for the second half):**

1. **`dezhoosh`** (this repo) — hardware discovery only. No license, no
   cloud dependency, works fully offline once installed. This is what the
   attached source represents.
2. **A second, not-yet-started integration** (working name discussed:
   "DWS" / Dezhoosh Web Services) — will hold everything that is genuinely
   a cloud/subscription service and unrelated to owning Dezhoosh hardware:
   license-key activation, remote access (FRP was the leading candidate;
   NetBird - an open-source WireGuard mesh VPN - was also being researched
   as a possibly-stronger alternative, no decision made yet), Jalali +
   Gregorian calendar, weather, SMS, and **cloud backup implemented via
   HA's official `BackupAgent` platform** (confirmed via HA dev docs to be
   the correct, natively-integrated mechanism - shows up in HA's own
   Settings → Backups UI as a backup destination, no custom UI needed).
   The `cloud/` package code removed from this repo (CloudManager,
   LicenseService, CloudMapper, session/models dataclasses, and a working
   matching `check.php` backend) is the right *starting point* for that
   second integration when work on it begins - it was fully built and
   bug-fixed before being extracted; ask the product owner before reusing
   it if you don't have that historical code, since it isn't included in
   this handoff (this handoff is the discovery-only repo, kept clean of any
   cloud/license traces on purpose).

Do not reintroduce any cloud/license/HTTP-calling code into this repo. If a
task seems to need it, that's a signal it belongs in the future DWS
integration instead.

## 3. Architecture: how a Home Assistant custom integration works here

- `manifest.json` → HA's identification card for the integration:
  `domain: "dezhoosh"`, `config_flow: true`, hard dependencies on `mqtt`,
  `http`, `frontend`, `single_config_entry: true`.
- `config_flow.py` → runs once, only at install time. Currently a single
  zero-input confirmation step (no license, no fields at all) since MQTT
  discovery needs no configuration.
- `__init__.py` → `async_setup_entry` runs on *every* HA startup (not just
  after config_flow). Wires together: frontend registration, the MQTT
  system-command transport, the device coordinator, then forwards to the
  `switch`/`sensor` platforms.
- `devices/` subpackage — everything about *what devices exist and their
  state*: `discovery.py` (parses retained MQTT discovery JSON into
  normalized objects), `models.py` (`DezhooshDevice`/`DezhooshChannel`/
  `DezhooshSensor` dataclasses), `coordinator.py` (`DezhooshCoordinator` -
  owns the device list + live state + dispatches HA entity-add signals).
  These three are grouped together because they're tightly coupled at
  runtime (the coordinator directly owns and drives the discovery
  listener) - splitting them further would have been artificial.
- `mqtt/` subpackage — the system-command protocol (`ping`/`get_info`/
  `list_devices` and any future command), deliberately separate from
  `devices/` because it has zero dependency on devices existing at all:
  `system_commands.py` (pluggable command registry, add a new command by
  adding one `@registry.command("name")` function - the registry also
  exposes a shared `context` dict so command handlers can reach live state,
  e.g. the coordinator, without the transport layer needing to know about
  it), `system.py` (thin MQTT topic router, no business logic),
  `__init__.py` (`DezhooshMQTT` - lifecycle wrapper).
- `switch.py` / `sensor.py` — HA entity platforms, which must stay at the
  integration root (HA's platform-forwarding mechanism imports them
  directly from there - this is a hard HA constraint, not a style choice).
  Listen on dispatcher signals (`SIGNAL_ADD_SWITCH`/`SIGNAL_ADD_SENSOR`) so
  new devices appear live without a restart.
- `frontend.py` — registers the compiled card bundle
  (`www/dezhoosh-cards.js`) as a static path + auto-adds it as a Lovelace
  resource, and installs the "Dezhoosh Aqua" theme by injecting directly
  into `hass.data[DATA_THEMES]` + firing `EVENT_THEMES_UPDATED` (confirmed
  correct via HA core source - no user-facing `configuration.yaml` edit
  ever needed, unlike a plain HACS "Theme"-category repo which *does*
  require the user to add `frontend: themes: !include_dir_merge_named
  themes` themselves - verified by inspecting a real published HACS theme
  repo's structure).
- `themes/dezhoosh.yaml` — the theme as plain YAML, independently usable
  even without the integration. **Known pending gap:** `frontend.py`
  currently has its *own separately hardcoded* Python dict
  (`_dezhoosh_theme()`) instead of reading this YAML file at runtime - the
  two have already drifted slightly out of sync (the YAML has two extra
  keys the Python dict doesn't). The agreed fix (not yet implemented): make
  `frontend.py` dynamically load every `.yaml` file under `themes/` at
  runtime, so `themes/` becomes the single source of truth and multiple
  themes can be added by just dropping in new YAML files with zero Python
  changes. **This is the top-priority next task.**
- `frontend/src/*.ts` — Lit-based Web Components, bundled by Rollup into
  `www/dezhoosh-cards.js` (the only file HA/the browser actually loads -
  the TypeScript source is never executed directly). `styles.ts` holds
  shared glass-morphism CSS all cards import from. `dezhoosh-switch-card.ts`
  renders N bridge channels (1/2/3) as tappable glass tiles in one card -
  confirmed via real screenshots to correctly render 1, 2, and 3-tile
  layouts without hardcoding "always 3". `dezhoosh-sensor-card.ts` groups a
  device's sensor readings. `dezhoosh-strategy.ts` is a Lovelace *view
  strategy* (`strategy: {type: custom:dezhoosh}`) that auto-generates the
  right card for every discovered device with zero manual YAML - confirmed
  working live across all three bridge sizes simultaneously.

### MQTT protocol (as implemented)

| Topic | Direction | Notes |
|---|---|---|
| `dezhoosh/discovery/<device_id>/config` | device → HA | **Must be retained.** Explained in depth to the product owner: without retain, a message published before HA's subscription exists (e.g. on every HA restart, since HA re-subscribes from scratch) is lost forever, since MQTT is fire-and-forget. Retain makes the broker replay the last message to any new subscriber regardless of timing. An **empty retained payload on this same topic removes the device** (confirmed in `discovery.py`'s actual code). |
| `dezhoosh/<device_id>/state` | device → HA | Not required to be retained by the integration, but recommending the device firmware retain it too, so entities show last-known state immediately after an HA restart instead of "Unknown" (coordinator's in-memory state is not persisted across restarts). |
| `dezhoosh/<device_id>/set` | HA → device | Channel commands, published on card tap. |
| `dezhoosh/system/<command>` | either | Routed by `mqtt/system.py` to the `mqtt/system_commands.py` registry. `ping` replies on the legacy `dezhoosh/system/pong` for backwards compatibility; every other command replies on `dezhoosh/system/<command>/response`. |

## 4. What has actually been tested (not just written)

Every claim below was independently verified in this project, not assumed:

- A real `homeassistant` pip package was installed and every single Python
  module in the integration was import-tested end to end (`__init__`,
  `config_flow`, `const`, `frontend`, `switch`, `sensor`, `devices` +
  its 3 submodules, `mqtt` + its 2 submodules) - all pass cleanly.
- The frontend bundle builds cleanly with `npm run build` and type-checks
  cleanly with `npx tsc --noEmit`.
- **Full live end-to-end test performed by the product owner** on a real
  HAOS Raspberry Pi: manually published MQTT discovery + state messages
  (via a phone MQTT app) for a single-bridge, a double-bridge, and a
  triple-bridge+2-sensors device. Confirmed via screenshots: all three
  devices appeared correctly in Devices & Services, entities were created
  correctly, `dezhoosh-switch-card` rendered 1/2/3 tiles correctly for each
  device type respectively (no broken layout for non-3-tile devices), and
  `dezhoosh-sensor-card` rendered both readings correctly.
- **`strategy: {type: custom:dezhoosh}` confirmed working live** across all
  three simultaneously-discovered devices with zero manual per-device card
  configuration.
- A previously-hit real bug (`ModuleNotFoundError` from a bogus
  `from homeassistant.helpers import frontend` import that doesn't exist in
  HA core - this broke the *entire* package's import chain and surfaced in
  the UI only as a generic "Invalid handler specified" error) was found,
  root-caused, fixed, and confirmed fixed via the same real-import-test
  method. **When something breaks in a way that isn't obvious, install real
  `homeassistant` via pip and import-test every module directly - don't
  guess from reading code alone; this method has already caught a bug that
  static reading missed.**

## 5. Explicitly pending / next steps (in the order discussed)

1. **`frontend.py` theme-loading refactor** (see section 3 above) - make
   `themes/*.yaml` the single source of truth instead of a duplicated
   hardcoded Python dict. Agreed but not yet implemented.
2. A standalone theme-only companion repo (mirroring a real published HACS
   "Theme"-category repo's structure - just `themes/*.yaml` + `hacs.json` +
   README, no Python at all) was discussed as a good low-effort way to
   serve users who want only the visual theme without owning hardware -
   not started.
3. Getting this repo ready for real HACS distribution (custom repository,
   not the public default store given the product owner's regional/niche
   audience) - a version-bump-per-GitHub-release workflow was discussed,
   and a critical gotcha was flagged: `www/dezhoosh-cards.js` (the compiled
   bundle) must be committed to the repo before each release, since HACS
   only copies files and never runs `npm run build` itself.
4. A `getEntitySuggestion` static method (a genuinely new-as-of-HA-2026.6
   API, confirmed via HA developer docs) could be added to the card classes
   so `dezhoosh-switch-card`/`dezhoosh-sensor-card` show up as a suggested
   option in HA's own "Add Card" picker when a user manually picks one of
   our entities - discussed as a worthwhile UX improvement, not started.
5. No automated test suite (pytest) exists yet - everything verified so far
   was manual/live testing plus real-package import checks. Recommended
   before the codebase grows much further.
6. The second integration (DWS) has not been started at all beyond the
   architecture decision in section 2.

## 6. Expectations for whoever continues this

The product owner has been explicit and consistent across this project:
they care a lot about correctness ("خیلی حساسم" - "I'm very careful/
sensitive about this") and want real verification, not assumptions. The
standard that's been maintained throughout: don't just read code and
assume it works - install a real `homeassistant` package and actually
import-test changes; run `npm run build`/`tsc --noEmit` for any frontend
change; when adding a new MQTT-facing feature, actually simulate it (e.g.
via `mosquitto_pub`/an MQTT client app) rather than reasoning about it in
the abstract. Explain *why*, not just *what*, when making architecture
decisions - the product owner is learning HA's internals deliberately and
has asked for that reasoning repeatedly throughout this project.

---

## Full source (current, verified state)

Folder structure:
```
__init__.py
config_flow.py
const.py
devices/__init__.py
devices/coordinator.py
devices/discovery.py
devices/models.py
frontend.py
frontend/package.json
frontend/rollup.config.js
frontend/src/dezhoosh-cards.ts
frontend/src/dezhoosh-sensor-card.ts
frontend/src/dezhoosh-strategy.ts
frontend/src/dezhoosh-switch-card.ts
frontend/src/styles.ts
frontend/src/types.ts
frontend/tsconfig.json
manifest.json
mqtt/__init__.py
mqtt/system.py
mqtt/system_commands.py
sensor.py
strings.json
switch.py
themes/dezhoosh.yaml
translations/en.json
translations/fa.json
```

### `__init__.py`

```python
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DATA_COORDINATOR,
    DOMAIN,
    PLATFORMS,
)

from .devices import DezhooshCoordinator
from .frontend import (
    async_register_frontend,
    async_unregister_frontend,
)
from .mqtt import DezhooshMQTT
from .mqtt.system_commands import registry as system_command_registry

_LOGGER = logging.getLogger(__name__)


async def async_setup(
    hass: HomeAssistant,
    config: dict,
) -> bool:
    """Initialize Dezhoosh."""

    hass.data.setdefault(DOMAIN, {})

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up a Dezhoosh config entry."""

    _LOGGER.debug("Starting Dezhoosh integration")

    # ------------------------------------------------------------
    # Frontend
    # ------------------------------------------------------------

    await async_register_frontend(hass)

    # ------------------------------------------------------------
    # MQTT
    # ------------------------------------------------------------

    mqtt_manager = DezhooshMQTT(hass)

    await mqtt_manager.async_start()

    # ------------------------------------------------------------
    # Coordinator
    # ------------------------------------------------------------

    coordinator = DezhooshCoordinator(
        hass,
        entry.entry_id,
    )

    await coordinator.async_start()

    # ------------------------------------------------------------
    # Shared Context
    # ------------------------------------------------------------

    system_command_registry.context["coordinator"] = coordinator

    # ------------------------------------------------------------
    # Runtime Store
    # ------------------------------------------------------------

    hass.data.setdefault(DOMAIN, {})

    hass.data[DOMAIN][entry.entry_id] = {
        "mqtt": mqtt_manager,
        DATA_COORDINATOR: coordinator,
    }

    # ------------------------------------------------------------
    # Platforms
    # ------------------------------------------------------------

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    _LOGGER.debug("Dezhoosh started successfully")

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload Dezhoosh."""

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    runtime = hass.data.get(DOMAIN, {}).pop(
        entry.entry_id,
        None,
    )

    if runtime:

        mqtt_manager = runtime.get("mqtt")

        if mqtt_manager:
            await mqtt_manager.async_stop()

        coordinator = runtime.get(DATA_COORDINATOR)

        if coordinator:
            await coordinator.async_stop()

    system_command_registry.context.pop(
        "coordinator",
        None,
    )

    if not hass.data.get(DOMAIN):
        await async_unregister_frontend(hass)

    return unload_ok

```

### `config_flow.py`

```python
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

```

### `const.py`

```python
"""Constants for Dezhoosh."""

DOMAIN = "dezhoosh"

NAME = "Dezhoosh"

VERSION = "0.1.0"

# ============================================================================
# MQTT
# ============================================================================

MQTT_ROOT = "dezhoosh"

TOPIC_SYSTEM_PREFIX = f"{MQTT_ROOT}/system"

# Wildcard used to route ANY system command (ping, get_info, future
# commands...) through a single subscription.
TOPIC_SYSTEM_COMMAND_WILDCARD = f"{TOPIC_SYSTEM_PREFIX}/+"

TOPIC_SYSTEM_PING = f"{TOPIC_SYSTEM_PREFIX}/ping"

TOPIC_SYSTEM_PONG = f"{TOPIC_SYSTEM_PREFIX}/pong"

# ---------------------------------------------------------------------------
# Platforms
# ---------------------------------------------------------------------------

PLATFORMS = ["switch", "sensor"]

# ---------------------------------------------------------------------------
# MQTT topic structure
# ---------------------------------------------------------------------------

TOPIC_DISCOVERY_PREFIX = f"{MQTT_ROOT}/discovery"

TOPIC_DISCOVERY_WILDCARD = f"{TOPIC_DISCOVERY_PREFIX}/+/config"

TOPIC_DEVICE_AVAILABILITY = f"{MQTT_ROOT}/status"

# ============================================================================
# Discovery
# ============================================================================

DISCOVERY_PROTOCOL_VERSION = 1

# ============================================================================
# Device model / discovery vocabulary
# ============================================================================

MANUFACTURER = "Dezhoosh"

MODEL_SINGLE_BRIDGE = "single_bridge"

MODEL_DOUBLE_BRIDGE = "double_bridge"

MODEL_TRIPLE_BRIDGE = "triple_bridge"

BRIDGE_MODELS = {
    MODEL_SINGLE_BRIDGE: 1,
    MODEL_DOUBLE_BRIDGE: 2,
    MODEL_TRIPLE_BRIDGE: 3,
}

DEVICE_TYPE_SWITCH = "switch"

DEVICE_TYPE_SENSOR = "sensor"

# ============================================================================
# Dispatcher Signals
# ============================================================================

SIGNAL_ADD_SWITCH = f"{DOMAIN}_add_switch"

SIGNAL_ADD_SENSOR = f"{DOMAIN}_add_sensor"

# ============================================================================
# Runtime Data
# ============================================================================

DATA_COORDINATOR = "coordinator"

DATA_DISCOVERY = "discovery"

DATA_MQTT = "mqtt"

```

### `devices/__init__.py`

```python
"""Device discovery, models, and coordination for Dezhoosh.

Groups everything about *what devices exist and what state they're in*:

- ``discovery.py`` - listens on ``dezhoosh/discovery/+/config`` and parses
  retained MQTT discovery payloads into normalized device objects.
- ``models.py`` - the normalized dataclasses those payloads get turned into
  (``DezhooshDevice``, ``DezhooshChannel``, ``DezhooshSensor``).
- ``coordinator.py`` - ties the two together at runtime: owns the list of
  known devices, tracks their live state from ``state`` topics, publishes
  commands to ``set`` topics, and notifies entities when something changes.

Other modules (``__init__.py``, ``switch.py``, ``sensor.py``) should import
from this package directly - e.g. ``from .devices import DezhooshCoordinator``
- rather than reaching into ``devices.coordinator``/``devices.models``
individually.
"""

from .coordinator import DezhooshCoordinator
from .models import DezhooshChannel, DezhooshDevice, DezhooshSensor

__all__ = [
    "DezhooshCoordinator",
    "DezhooshChannel",
    "DezhooshDevice",
    "DezhooshSensor",
]

```

### `devices/coordinator.py`

```python
"""Device coordinator for Dezhoosh.

Owns the lifecycle of discovered devices: keeps their normalized models,
tracks per-channel/sensor runtime state from MQTT ``state`` topics, publishes
commands to ``set`` topics, and notifies the switch/sensor platforms via the
dispatcher when new devices appear.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from ..const import (
    SIGNAL_ADD_SENSOR,
    SIGNAL_ADD_SWITCH,
)
from .discovery import DezhooshDiscovery
from .models import DezhooshDevice

_LOGGER = logging.getLogger(__name__)


class DezhooshCoordinator:
    """Central registry and runtime state for Dezhoosh devices."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id

        self.devices: dict[str, DezhooshDevice] = {}
        # device_id -> {channel_or_sensor_key: value}
        self._state: dict[str, dict[str, Any]] = {}
        # device_id -> list of update listeners
        self._listeners: dict[str, list[Callable[[], None]]] = {}
        # device_id -> mqtt unsubscribe for its state topic
        self._state_unsubs: dict[str, Callable[[], None]] = {}

        self._discovery = DezhooshDiscovery(
            hass,
            on_device=self.async_device_discovered,
            on_remove=self.async_device_removed,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_start(self) -> None:
        await self._discovery.async_start()

    async def async_stop(self) -> None:
        await self._discovery.async_stop()
        for unsub in self._state_unsubs.values():
            unsub()
        self._state_unsubs.clear()

    # ------------------------------------------------------------------
    # Discovery callbacks
    # ------------------------------------------------------------------

    async def async_device_discovered(self, device: DezhooshDevice) -> None:
        """Register (or update) a discovered device and push it to platforms."""

        is_new = device.device_id not in self.devices
        self.devices[device.device_id] = device
        self._state.setdefault(device.device_id, {})

        await self._async_subscribe_state(device)

        if not is_new:
            # Existing device re-announced; refresh listeners.
            self._notify(device.device_id)
            return

        if device.is_switch:
            async_dispatcher_send(
                self.hass, SIGNAL_ADD_SWITCH, device.device_id
            )
        if device.sensors:
            async_dispatcher_send(
                self.hass, SIGNAL_ADD_SENSOR, device.device_id
            )

    async def async_device_removed(self, device_id: str) -> None:
        """Handle removal of a device (empty discovery payload)."""

        self.devices.pop(device_id, None)
        self._state.pop(device_id, None)
        unsub = self._state_unsubs.pop(device_id, None)
        if unsub:
            unsub()
        self._notify(device_id)

    # ------------------------------------------------------------------
    # State handling
    # ------------------------------------------------------------------

    async def _async_subscribe_state(self, device: DezhooshDevice) -> None:
        """Subscribe to a device's state topic (idempotent)."""

        if device.device_id in self._state_unsubs:
            return

        @callback
        def _message(msg) -> None:
            self._handle_state(device.device_id, msg.payload)

        unsub = await mqtt.async_subscribe(
            self.hass,
            device.state_topic,
            _message,
            qos=1,
        )
        self._state_unsubs[device.device_id] = unsub

    def _handle_state(self, device_id: str, payload: Any) -> None:
        """Merge an incoming state payload into the device state."""

        try:
            data = json.loads(payload)
        except (ValueError, TypeError):
            return

        if not isinstance(data, dict):
            return

        self._state.setdefault(device_id, {}).update(data)
        self._notify(device_id)

    def get_state(self, device_id: str) -> dict[str, Any]:
        return self._state.get(device_id, {})

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def async_set_channel(
        self, device_id: str, channel_key: str, value: bool
    ) -> None:
        """Publish a command to set a channel on/off."""

        device = self.devices.get(device_id)
        if device is None:
            return

        payload = {channel_key: "ON" if value else "OFF"}

        await mqtt.async_publish(
            self.hass,
            device.command_topic,
            json.dumps(payload),
            qos=1,
            retain=False,
        )

        # Optimistically update local state.
        self._state.setdefault(device_id, {})[channel_key] = "ON" if value else "OFF"
        self._notify(device_id)

    # ------------------------------------------------------------------
    # Listener registration (used by entities)
    # ------------------------------------------------------------------

    def async_add_listener(
        self, device_id: str, update: Callable[[], None]
    ) -> Callable[[], None]:
        """Register an entity update callback for a device."""

        self._listeners.setdefault(device_id, []).append(update)

        def _remove() -> None:
            listeners = self._listeners.get(device_id)
            if listeners and update in listeners:
                listeners.remove(update)

        return _remove

    def _notify(self, device_id: str) -> None:
        for update in list(self._listeners.get(device_id, [])):
            update()

```

### `devices/discovery.py`

```python
"""MQTT discovery parsing for Dezhoosh.

Listens on ``dezhoosh/discovery/+/config`` and converts retained discovery
payloads into :class:`~.models.DezhooshDevice` instances, then hands them to
the coordinator.

Expected discovery payload (JSON), for example a triple-bridge switch::

    {
      "id": "sw_kitchen_01",
      "name": "Kitchen Switch",
      "type": "switch",
      "model": "triple_bridge",
      "sw_version": "1.2.0",
      "state_topic": "dezhoosh/sw_kitchen_01/state",
      "command_topic": "dezhoosh/sw_kitchen_01/set",
      "availability_topic": "dezhoosh/sw_kitchen_01/status",
      "channels": [
        {"key": "l1", "name": "Left"},
        {"key": "l2", "name": "Middle"},
        {"key": "l3", "name": "Right"}
      ],
      "sensors": [
        {"key": "temperature", "name": "Temperature",
         "device_class": "temperature", "unit": "°C"}
      ]
    }

An empty payload on a discovery topic removes the device.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant

from ..const import (
    BRIDGE_MODELS,
    DEVICE_TYPE_SENSOR,
    DEVICE_TYPE_SWITCH,
    MODEL_SINGLE_BRIDGE,
    TOPIC_DISCOVERY_WILDCARD,
)
from .models import DezhooshChannel, DezhooshDevice, DezhooshSensor

_LOGGER = logging.getLogger(__name__)


class DezhooshDiscovery:
    """Subscribe to discovery topics and emit normalized devices."""

    def __init__(
        self,
        hass: HomeAssistant,
        on_device: Callable[[DezhooshDevice], Any],
        on_remove: Callable[[str], Any],
    ) -> None:
        self.hass = hass
        self._on_device = on_device
        self._on_remove = on_remove
        self._unsubscribe: Callable[[], None] | None = None

    async def async_start(self) -> None:
        """Subscribe to the discovery wildcard topic."""

        self._unsubscribe = await mqtt.async_subscribe(
            self.hass,
            TOPIC_DISCOVERY_WILDCARD,
            self._async_discovery_received,
            qos=1,
        )

        _LOGGER.debug(
            "Dezhoosh discovery: subscribed to %s",
            TOPIC_DISCOVERY_WILDCARD,
        )

    async def async_stop(self) -> None:
        """Remove the discovery subscription."""

        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    async def _async_discovery_received(self, msg) -> None:
        """Handle a discovery message."""

        device_id = self._device_id_from_topic(msg.topic)
        if device_id is None:
            return

        payload = (msg.payload or "").strip() if isinstance(msg.payload, str) else msg.payload

        if not payload:
            _LOGGER.debug("Dezhoosh discovery: removing %s", device_id)
            await _maybe_await(self._on_remove(device_id))
            return

        try:
            data = json.loads(payload)
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Dezhoosh discovery: invalid JSON on %s", msg.topic
            )
            return

        device = self._parse_device(device_id, data)
        if device is None:
            return

        _LOGGER.debug(
            "Dezhoosh discovery: %s (%s, %s)",
            device.device_id,
            device.device_type,
            device.model,
        )
        await _maybe_await(self._on_device(device))

    @staticmethod
    def _device_id_from_topic(topic: str) -> str | None:
        """Extract ``<device_id>`` from ``dezhoosh/discovery/<id>/config``."""

        parts = topic.split("/")
        # dezhoosh / discovery / <id> / config
        if len(parts) >= 4 and parts[-1] == "config":
            return parts[-2]
        return None

    def _parse_device(
        self, device_id: str, data: dict[str, Any]
    ) -> DezhooshDevice | None:
        """Convert a discovery dict into a :class:`DezhooshDevice`."""

        if not isinstance(data, dict):
            return None

        device_type = data.get("type", DEVICE_TYPE_SWITCH)
        model = data.get("model", MODEL_SINGLE_BRIDGE)
        name = data.get("name") or device_id

        state_topic = data.get("state_topic") or f"dezhoosh/{device_id}/state"
        command_topic = data.get("command_topic") or f"dezhoosh/{device_id}/set"

        channels = self._parse_channels(data, model)
        sensors = self._parse_sensors(data)

        if device_type == DEVICE_TYPE_SWITCH and not channels:
            _LOGGER.warning(
                "Dezhoosh discovery: switch %s has no channels", device_id
            )

        return DezhooshDevice(
            device_id=device_id,
            name=name,
            model=model,
            device_type=device_type,
            state_topic=state_topic,
            command_topic=command_topic,
            availability_topic=data.get("availability_topic"),
            sw_version=data.get("sw_version"),
            channels=channels,
            sensors=sensors,
            raw=data,
        )

    @staticmethod
    def _parse_channels(
        data: dict[str, Any], model: str
    ) -> list[DezhooshChannel]:
        """Parse channels, deriving defaults from the bridge model."""

        raw_channels = data.get("channels")
        channels: list[DezhooshChannel] = []

        if isinstance(raw_channels, list) and raw_channels:
            for index, item in enumerate(raw_channels):
                if not isinstance(item, dict):
                    continue
                key = str(item.get("key") or f"l{index + 1}")
                channels.append(
                    DezhooshChannel(
                        key=key,
                        name=item.get("name") or f"Bridge {index + 1}",
                        index=index,
                    )
                )
            return channels

        # No explicit channels: derive from the model (1/2/3 bridges).
        count = BRIDGE_MODELS.get(model, 0)
        for index in range(count):
            channels.append(
                DezhooshChannel(
                    key=f"l{index + 1}",
                    name=f"Bridge {index + 1}",
                    index=index,
                )
            )
        return channels

    @staticmethod
    def _parse_sensors(data: dict[str, Any]) -> list[DezhooshSensor]:
        """Parse sensor definitions from a discovery payload."""

        raw_sensors = data.get("sensors")
        sensors: list[DezhooshSensor] = []

        if not isinstance(raw_sensors, list):
            return sensors

        for index, item in enumerate(raw_sensors):
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or f"sensor_{index + 1}")
            sensors.append(
                DezhooshSensor(
                    key=key,
                    name=item.get("name") or key,
                    device_class=item.get("device_class"),
                    unit=item.get("unit") or item.get("unit_of_measurement"),
                    icon=item.get("icon"),
                )
            )
        return sensors


async def _maybe_await(result: Any) -> None:
    """Await *result* if it is awaitable."""

    if hasattr(result, "__await__"):
        await result

```

### `devices/models.py`

```python
"""Data models for Dezhoosh discovered devices.

These lightweight dataclasses represent the normalized shape of a device once
its MQTT discovery payload has been parsed. Platforms (switch/sensor) consume
these models instead of raw JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..const import (
    BRIDGE_MODELS,
    DEVICE_TYPE_SENSOR,
    DEVICE_TYPE_SWITCH,
    MANUFACTURER,
)


@dataclass
class DezhooshChannel:
    """A single controllable channel (bridge/gang) of a switch device."""

    key: str
    name: str
    index: int


@dataclass
class DezhooshSensor:
    """A single sensor reading exposed by a device."""

    key: str
    name: str
    device_class: str | None = None
    unit: str | None = None
    icon: str | None = None


@dataclass
class DezhooshDevice:
    """Normalized representation of a discovered Dezhoosh device."""

    device_id: str
    name: str
    model: str
    device_type: str
    state_topic: str
    command_topic: str
    availability_topic: str | None = None
    sw_version: str | None = None
    channels: list[DezhooshChannel] = field(default_factory=list)
    sensors: list[DezhooshSensor] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def bridge_count(self) -> int:
        """Number of bridges for a switch model (1/2/3), else 0."""

        return BRIDGE_MODELS.get(self.model, len(self.channels))

    @property
    def is_switch(self) -> bool:
        return self.device_type == DEVICE_TYPE_SWITCH

    @property
    def is_sensor(self) -> bool:
        return self.device_type == DEVICE_TYPE_SENSOR

    def device_info(self) -> dict[str, Any]:
        """Return Home Assistant device registry info for this device."""

        return {
            "identifiers": {("dezhoosh", self.device_id)},
            "name": self.name,
            "manufacturer": MANUFACTURER,
            "model": self.model,
            "sw_version": self.sw_version,
        }

```

### `frontend.py`

```python
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

```

### `frontend/package.json`

```json
{
  "name": "dezhoosh-cards",
  "version": "0.1.0",
  "description": "Glass-morphism Lovelace cards for the Dezhoosh Home Assistant integration.",
  "private": true,
  "type": "module",
  "scripts": {
    "build": "rollup -c",
    "watch": "rollup -c --watch",
    "lint": "tsc --noEmit"
  },
  "devDependencies": {
    "@rollup/plugin-node-resolve": "^15.2.3",
    "@rollup/plugin-typescript": "^11.1.6",
    "rollup": "^4.9.6",
    "tslib": "^2.6.2",
    "typescript": "^5.3.3"
  },
  "dependencies": {
    "custom-card-helpers": "^1.9.0",
    "lit": "^3.1.0"
  }
}

```

### `frontend/rollup.config.js`

```javascript
import resolve from "@rollup/plugin-node-resolve";
import typescript from "@rollup/plugin-typescript";

export default {
  input: "src/dezhoosh-cards.ts",
  output: {
    file: "../www/dezhoosh-cards.js",
    format: "es",
    inlineDynamicImports: true,
    sourcemap: false,
  },
  plugins: [
    resolve(),
    typescript({ tsconfig: "./tsconfig.json", outDir: undefined, declaration: false }),
  ],
};

```

### `frontend/src/dezhoosh-cards.ts`

```typescript
import "./dezhoosh-switch-card";
import "./dezhoosh-sensor-card";
import "./dezhoosh-strategy";

const VERSION = "0.1.0";

window.customCards = window.customCards || [];
window.customCards.push(
  {
    type: "dezhoosh-switch-card",
    name: "Dezhoosh Switch Card",
    description:
      "Glass-morphism control card for single/double/triple bridge Dezhoosh switches.",
    preview: true,
  },
  {
    type: "dezhoosh-sensor-card",
    name: "Dezhoosh Sensor Card",
    description: "Glass sensor card for grouped Dezhoosh sensor readings.",
    preview: true,
  }
);

/* eslint-disable no-console */
console.info(
  `%c DEZHOOSH-CARDS %c v${VERSION} `,
  "color:#04141a;background:#1fd4c3;font-weight:700;border-radius:4px 0 0 4px;padding:2px 6px",
  "color:#1fd4c3;background:#071c22;border-radius:0 4px 4px 0;padding:2px 6px"
);

```

### `frontend/src/dezhoosh-sensor-card.ts`

```typescript
import { LitElement, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { glassStyles } from "./styles";
import type {
  DezhooshSensorCardConfig,
  HomeAssistant,
  SensorReading,
} from "./types";

/** Glass sensor card that groups several Dezhoosh sensor readings. */
@customElement("dezhoosh-sensor-card")
export class DezhooshSensorCard extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;
  @state() private _config?: DezhooshSensorCardConfig;

  static styles = glassStyles;

  public setConfig(config: DezhooshSensorCardConfig): void {
    if (!config || !config.entities || config.entities.length === 0) {
      throw new Error("Specify at least one sensor entity");
    }
    this._config = config;
  }

  public getCardSize(): number {
    return 1;
  }

  private _readings(): SensorReading[] {
    if (!this.hass || !this._config) return [];
    return this._config.entities
      .map((entityId) => {
        const stateObj = this.hass!.states[entityId];
        if (!stateObj) return undefined;
        return {
          entityId,
          name: stateObj.attributes.friendly_name || entityId,
          value: stateObj.state,
          unit: stateObj.attributes.unit_of_measurement || "",
          icon: stateObj.attributes.icon || "mdi:gauge",
        } as SensorReading;
      })
      .filter((r): r is SensorReading => r !== undefined);
  }

  protected render() {
    if (!this._config || !this.hass) return nothing;

    const readings = this._readings();

    return html`
      <ha-card>
        <div class="dz-card">
          <div class="dz-header">
            <div class="dz-badge">
              <ha-icon .icon=${this._config.icon || "mdi:chart-box"}></ha-icon>
            </div>
            <div>
              <div class="dz-title">${this._config.name || "Dezhoosh Sensors"}</div>
              <div class="dz-subtitle">${readings.length} readings</div>
            </div>
          </div>
          ${readings.length === 0
            ? html`<div class="dz-empty">No sensor data yet…</div>`
            : html`
                <div class="dz-sensors">
                  ${readings.map(
                    (reading) => html`
                      <div class="dz-sensor">
                        <div class="dz-icon">
                          <ha-icon .icon=${reading.icon}></ha-icon>
                        </div>
                        <div>
                          <div class="dz-sensor-value">
                            ${reading.value}${reading.unit
                              ? html`<span> ${reading.unit}</span>`
                              : nothing}
                          </div>
                          <div class="dz-sensor-name">${reading.name}</div>
                        </div>
                      </div>
                    `
                  )}
                </div>
              `}
        </div>
      </ha-card>
    `;
  }
}

```

### `frontend/src/dezhoosh-strategy.ts`

```typescript
import type { HomeAssistant } from "./types";

/**
 * View strategy that auto-builds a full Dezhoosh dashboard view: one
 * glass switch-card per discovered single/double/triple-bridge switch
 * device, plus one glass sensor-card grouping the sensors of each device
 * that has them. No manual card setup required - add a view with:
 *
 *   strategy:
 *     type: custom:dezhoosh
 *
 * and it re-generates itself as new devices show up on discovery.
 */
class DezhooshViewStrategy extends HTMLElement {
  static async generate(_config: unknown, hass: HomeAssistant) {
    const switchStates = Object.values(hass.states).filter((s) =>
      s.entity_id.startsWith("switch.")
    );
    const sensorStates = Object.values(hass.states).filter(
      (s) =>
        s.entity_id.startsWith("sensor.") &&
        s.attributes.device_id !== undefined
    );

    const switchDevices = new Map<string, typeof switchStates>();
    for (const stateObj of switchStates) {
      const deviceId = stateObj.attributes.device_id;
      if (!deviceId) continue;
      const list = switchDevices.get(deviceId) ?? [];
      list.push(stateObj);
      switchDevices.set(deviceId, list);
    }

    const sensorDevices = new Map<string, typeof sensorStates>();
    for (const stateObj of sensorStates) {
      const deviceId = stateObj.attributes.device_id;
      const list = sensorDevices.get(deviceId) ?? [];
      list.push(stateObj);
      sensorDevices.set(deviceId, list);
    }

    const deviceName = (entities: typeof switchStates): string => {
      const full = entities[0]?.attributes.friendly_name || "Dezhoosh Device";
      return full.split(" ").slice(0, -1).join(" ") || full;
    };

    const cards: Record<string, unknown>[] = [];

    for (const [deviceId, entities] of switchDevices) {
      const sorted = [...entities].sort(
        (a, b) =>
          (a.attributes.bridge_index ?? 0) - (b.attributes.bridge_index ?? 0)
      );
      cards.push({
        type: "custom:dezhoosh-switch-card",
        device_id: deviceId,
        name: deviceName(sorted),
        entities: sorted.map((s) => s.entity_id),
      });
    }

    for (const [deviceId, entities] of sensorDevices) {
      cards.push({
        type: "custom:dezhoosh-sensor-card",
        name: `${deviceName(entities)} Sensors`,
        entities: entities.map((s) => s.entity_id),
        device_id: deviceId,
      });
    }

    if (cards.length === 0) {
      cards.push({
        type: "markdown",
        content:
          "### Waiting for Dezhoosh devices…\n" +
          "Cards will appear here automatically as soon as a Dezhoosh " +
          "switch or sensor is discovered over MQTT.",
      });
    }

    return { cards };
  }
}

customElements.define("ll-strategy-view-dezhoosh", DezhooshViewStrategy);

```

### `frontend/src/dezhoosh-switch-card.ts`

```typescript
import { LitElement, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { glassStyles } from "./styles";
import type {
  BridgeEntity,
  DezhooshSwitchCardConfig,
  HomeAssistant,
} from "./types";

/**
 * Multi-bridge switch card. Renders every channel of a single/double/triple
 * bridge Dezhoosh switch as tappable glass tiles inside one card.
 */
@customElement("dezhoosh-switch-card")
export class DezhooshSwitchCard extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;
  @state() private _config?: DezhooshSwitchCardConfig;

  static styles = glassStyles;

  public setConfig(config: DezhooshSwitchCardConfig): void {
    if (!config) {
      throw new Error("Invalid configuration");
    }
    if (!config.device_id && (!config.entities || config.entities.length === 0)) {
      throw new Error("Specify a device_id or a list of entities");
    }
    this._config = config;
  }

  public getCardSize(): number {
    return 2;
  }

  private _bridges(): BridgeEntity[] {
    if (!this.hass || !this._config) return [];

    const ids = this._resolveEntities();
    return ids
      .map((entityId, index) => {
        const stateObj = this.hass!.states[entityId];
        if (!stateObj) return undefined;
        return {
          entityId,
          name:
            stateObj.attributes.friendly_name?.split(" ").slice(-1)[0] ||
            `Bridge ${index + 1}`,
          isOn: stateObj.state === "on",
          index,
        } as BridgeEntity;
      })
      .filter((b): b is BridgeEntity => b !== undefined);
  }

  private _resolveEntities(): string[] {
    if (!this.hass || !this._config) return [];
    if (this._config.entities?.length) {
      return this._config.entities;
    }
    // Derive from device_id by matching entity attributes.
    const deviceId = this._config.device_id;
    return Object.keys(this.hass.states)
      .filter((id) => id.startsWith("switch."))
      .filter(
        (id) => this.hass!.states[id].attributes.device_id === deviceId
      )
      .sort((a, b) => {
        const ai = this.hass!.states[a].attributes.bridge_index ?? 0;
        const bi = this.hass!.states[b].attributes.bridge_index ?? 0;
        return ai - bi;
      });
  }

  private _toggle(entityId: string): void {
    if (!this.hass) return;
    this.hass.callService("switch", "toggle", { entity_id: entityId });
  }

  protected render() {
    if (!this._config || !this.hass) return nothing;

    const bridges = this._bridges();
    const count = Math.min(Math.max(bridges.length, 1), 3);
    const activeCount = bridges.filter((b) => b.isOn).length;
    const title = this._config.name || this._deviceName(bridges);

    return html`
      <ha-card>
        <div class="dz-card">
          <div class="dz-header">
            <div class="dz-badge">
              <ha-icon .icon=${this._config.icon || "mdi:light-switch"}></ha-icon>
            </div>
            <div>
              <div class="dz-title">${title}</div>
              <div class="dz-subtitle">
                ${bridges.length} ${bridges.length === 1 ? "bridge" : "bridges"} ·
                ${activeCount} on
              </div>
            </div>
          </div>
          ${bridges.length === 0
            ? html`<div class="dz-empty">Waiting for device…</div>`
            : html`
                <div class="dz-bridges count-${count}">
                  ${bridges.map((bridge) => this._renderBridge(bridge))}
                </div>
              `}
        </div>
      </ha-card>
    `;
  }

  private _renderBridge(bridge: BridgeEntity) {
    return html`
      <div
        class="dz-bridge ${bridge.isOn ? "on" : ""}"
        @click=${() => this._toggle(bridge.entityId)}
        role="button"
        tabindex="0"
      >
        <div class="dz-icon">
          <ha-icon
            .icon=${bridge.isOn ? "mdi:lightbulb-on" : "mdi:lightbulb-outline"}
          ></ha-icon>
        </div>
        <div class="dz-bridge-name">${bridge.name}</div>
        <div class="dz-bridge-state">${bridge.isOn ? "On" : "Off"}</div>
      </div>
    `;
  }

  private _deviceName(bridges: BridgeEntity[]): string {
    if (!this.hass || bridges.length === 0) return "Dezhoosh Switch";
    const first = this.hass.states[bridges[0].entityId];
    const full = first?.attributes.friendly_name || "Dezhoosh Switch";
    return full.split(" ").slice(0, -1).join(" ") || full;
  }
}

```

### `frontend/src/styles.ts`

```typescript
import { css } from "lit";

/**
 * Shared glass-morphism styling for all Dezhoosh cards.
 * Uses the green-blue Dezhoosh Aqua palette with a frosted-glass surface.
 */
export const glassStyles = css`
  :host {
    --dz-glow: rgba(31, 212, 195, 0.55);
    --dz-teal: #1fd4c3;
    --dz-teal-soft: rgba(31, 212, 195, 0.15);
    --dz-blue: #12b6a6;
    --dz-text: var(--primary-text-color, #e6fffb);
    --dz-text-dim: var(--secondary-text-color, #8fd7cf);
    display: block;
  }

  .dz-card {
    position: relative;
    overflow: hidden;
    border-radius: 22px;
    padding: 18px 20px;
    color: var(--dz-text);
    background: linear-gradient(
      145deg,
      rgba(18, 182, 166, 0.22),
      rgba(9, 34, 41, 0.55)
    );
    backdrop-filter: blur(18px) saturate(140%);
    -webkit-backdrop-filter: blur(18px) saturate(140%);
    border: 1px solid rgba(143, 240, 230, 0.18);
    box-shadow:
      0 10px 36px rgba(3, 18, 23, 0.5),
      inset 0 1px 0 rgba(255, 255, 255, 0.08);
  }

  .dz-card::before {
    content: "";
    position: absolute;
    inset: -40% 60% 55% -20%;
    background: radial-gradient(
      circle at top left,
      var(--dz-glow),
      transparent 70%
    );
    opacity: 0.35;
    pointer-events: none;
  }

  .dz-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
    position: relative;
  }

  .dz-title {
    font-size: 1.05rem;
    font-weight: 600;
    letter-spacing: 0.02em;
  }

  .dz-subtitle {
    font-size: 0.78rem;
    color: var(--dz-text-dim);
  }

  .dz-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border-radius: 14px;
    background: var(--dz-teal-soft);
    border: 1px solid rgba(31, 212, 195, 0.3);
    color: var(--dz-teal);
  }

  .dz-bridges {
    display: grid;
    gap: 12px;
  }

  .dz-bridges.count-1 {
    grid-template-columns: 1fr;
  }
  .dz-bridges.count-2 {
    grid-template-columns: repeat(2, 1fr);
  }
  .dz-bridges.count-3 {
    grid-template-columns: repeat(3, 1fr);
  }

  .dz-bridge {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 14px 8px;
    border-radius: 16px;
    cursor: pointer;
    background: rgba(7, 28, 34, 0.4);
    border: 1px solid rgba(143, 240, 230, 0.1);
    transition: transform 0.18s ease, box-shadow 0.25s ease,
      background 0.25s ease, border-color 0.25s ease;
    -webkit-tap-highlight-color: transparent;
  }

  .dz-bridge:hover {
    transform: translateY(-2px);
  }

  .dz-bridge .dz-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 46px;
    height: 46px;
    border-radius: 50%;
    color: var(--dz-text-dim);
    background: rgba(143, 240, 230, 0.08);
    transition: color 0.25s ease, background 0.25s ease,
      box-shadow 0.25s ease;
  }

  .dz-bridge.on {
    background: rgba(31, 212, 195, 0.14);
    border-color: rgba(31, 212, 195, 0.5);
    box-shadow: 0 6px 20px rgba(31, 212, 195, 0.25);
  }

  .dz-bridge.on .dz-icon {
    color: #04141a;
    background: linear-gradient(135deg, var(--dz-teal), var(--dz-blue));
    box-shadow: 0 0 18px var(--dz-glow);
  }

  .dz-bridge-name {
    font-size: 0.82rem;
    text-align: center;
    color: var(--dz-text);
  }

  .dz-bridge-state {
    font-size: 0.7rem;
    color: var(--dz-text-dim);
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .dz-sensors {
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  }

  .dz-sensor {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 14px;
    border-radius: 14px;
    background: rgba(7, 28, 34, 0.4);
    border: 1px solid rgba(143, 240, 230, 0.1);
  }

  .dz-sensor .dz-icon {
    color: var(--dz-teal);
  }

  .dz-sensor-value {
    font-size: 1.1rem;
    font-weight: 600;
  }

  .dz-sensor-name {
    font-size: 0.74rem;
    color: var(--dz-text-dim);
  }

  .dz-empty {
    font-size: 0.85rem;
    color: var(--dz-text-dim);
    text-align: center;
    padding: 8px 0;
  }
`;

```

### `frontend/src/types.ts`

```typescript
import type { HomeAssistant } from "custom-card-helpers";

export interface DezhooshSwitchCardConfig {
  type: string;
  device_id?: string;
  name?: string;
  entities?: string[];
  icon?: string;
}

export interface DezhooshSensorCardConfig {
  type: string;
  name?: string;
  entities: string[];
  icon?: string;
  device_id?: string;
}

export interface BridgeEntity {
  entityId: string;
  name: string;
  isOn: boolean;
  index: number;
}

export interface SensorReading {
  entityId: string;
  name: string;
  value: string;
  unit: string;
  icon: string;
}

export type { HomeAssistant };

declare global {
  interface Window {
    customCards?: Array<{
      type: string;
      name: string;
      description: string;
      preview?: boolean;
    }>;
  }
}

```

### `frontend/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2021",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "lib": ["ES2021", "DOM", "DOM.Iterable"],
    "experimentalDecorators": true,
    "useDefineForClassFields": false,
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "outDir": "../www"
  },
  "include": ["src/**/*.ts"]
}

```

### `manifest.json`

```json
{
    "domain": "dezhoosh",
    "name": "Dezhoosh",
    "version": "0.1.0",
    "documentation": "https://github.com/masihch/dezhoosh-home-assistant",
    "issue_tracker": "https://github.com/masihch/dezhoosh-home-assistant/issues",
    "dependencies": [
        "mqtt",
        "http",
        "frontend"
    ],
    "requirements": [],
    "codeowners": [
        "@masihch"
    ],
    "config_flow": true,
    "iot_class": "local_push",
    "single_config_entry": true
}

```

### `mqtt/__init__.py`

```python
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .system import SystemCommandHandler

_LOGGER = logging.getLogger(__name__)


class DezhooshMQTT:
    """Thin MQTT transport coordinator for Dezhoosh.

    Delegates the system protocol to :class:`~.system.SystemCommandHandler`.
    Device discovery and runtime traffic are owned by the coordinator
    (see :mod:`..devices.coordinator`).
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.system = SystemCommandHandler(hass)

    async def async_start(self) -> None:
        """Start all MQTT subscriptions owned by the transport layer."""

        await self.system.async_start()
        _LOGGER.debug("Dezhoosh MQTT: transport started")

    async def async_stop(self) -> None:
        """Tear down MQTT subscriptions."""

        await self.system.async_stop()
        _LOGGER.debug("Dezhoosh MQTT: transport stopped")

```

### `mqtt/system.py`

```python
"""System command MQTT transport for Dezhoosh.

Subscribes once to the ``dezhoosh/system/+`` wildcard, extracts the command
name from the topic, and hands the parsed payload off to the
:mod:`.system_commands` registry. This file only knows how to route bytes on
a wire to a command name - it has no idea what "ping" or any other command
actually means. See :mod:`.system_commands` to add new commands.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant

from ..const import TOPIC_SYSTEM_COMMAND_WILDCARD, TOPIC_SYSTEM_PREFIX
from .system_commands import registry as system_command_registry

_LOGGER = logging.getLogger(__name__)

# Commands that publish their response on a legacy/fixed topic instead of
# the generic "<command>/response" pattern, for backwards compatibility
# with firmware that already expects e.g. dezhoosh/system/pong.
_LEGACY_RESPONSE_TOPICS = {
    "ping": f"{TOPIC_SYSTEM_PREFIX}/pong",
}


class SystemCommandHandler:
    """Route incoming Dezhoosh system commands to the command registry."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._unsubscribe: Callable[[], None] | None = None

    def register_command(self, name: str, handler) -> None:
        """Register (or override) a system command handler at runtime.

        Kept on the transport class as a convenience so callers don't need
        to import :mod:`.system_commands` directly.
        """

        system_command_registry.register(name, handler)

    async def async_start(self) -> None:
        """Subscribe to the system command wildcard topic."""

        self._unsubscribe = await mqtt.async_subscribe(
            self.hass,
            TOPIC_SYSTEM_COMMAND_WILDCARD,
            self._async_command_received,
            qos=1,
        )

        _LOGGER.debug(
            "Dezhoosh system: subscribed to %s (commands: %s)",
            TOPIC_SYSTEM_COMMAND_WILDCARD,
            ", ".join(system_command_registry.commands),
        )

    async def async_stop(self) -> None:
        """Remove the system command subscription."""

        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    async def _async_command_received(self, msg) -> None:
        """Dispatch an incoming system command to its registered handler."""

        command = self._command_from_topic(msg.topic)
        if command is None:
            return

        # Ignore anything that looks like a response echoing back on the
        # wildcard (e.g. our own "<command>/response" or legacy "pong").
        if command.endswith("/response") or command in (
            t.rsplit("/", 1)[-1] for t in _LEGACY_RESPONSE_TOPICS.values()
        ):
            return

        if not system_command_registry.has(command):
            _LOGGER.debug(
                "Dezhoosh system: no handler for unknown command '%s' (topic=%s)",
                command,
                msg.topic,
            )
            return

        payload = self._parse_payload(msg.payload)

        _LOGGER.debug(
            "Dezhoosh system RX -> topic=%s command=%s payload=%s",
            msg.topic,
            command,
            payload,
        )

        response = await system_command_registry.dispatch(command, payload)
        if response is None:
            return

        response_topic = _LEGACY_RESPONSE_TOPICS.get(
            command, f"{TOPIC_SYSTEM_PREFIX}/{command}/response"
        )

        await mqtt.async_publish(
            self.hass,
            response_topic,
            json.dumps(response),
            qos=1,
            retain=False,
        )

        _LOGGER.debug(
            "Dezhoosh system TX -> topic=%s payload=%s",
            response_topic,
            response,
        )

    @staticmethod
    def _command_from_topic(topic: str) -> str | None:
        """Extract ``<command>`` from ``dezhoosh/system/<command>``."""

        prefix = f"{TOPIC_SYSTEM_PREFIX}/"
        if not topic.startswith(prefix):
            return None
        command = topic[len(prefix) :]
        return command or None

    @staticmethod
    def _parse_payload(raw: Any) -> dict[str, Any]:
        """Best-effort parse of an MQTT payload into a dict."""

        if not raw:
            return {}

        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return {}

        return data if isinstance(data, dict) else {}

```

### `mqtt/system_commands.py`

```python
"""System command definitions for Dezhoosh.

This is the "new architecture" for system-level commands: every command the
Dezhoosh backend/firmware can send to Home Assistant over
``dezhoosh/system/<command>`` is a small, self-contained handler registered
here, in :class:`SystemCommandRegistry`.

The MQTT transport layer (see :mod:`.system`) stays a dumb router: it
extracts ``<command>`` from the topic and calls
``registry.dispatch(command, payload)``. It never needs to know *what* a
command does. Adding a brand new system command (``restart``, ``identify``,
``get_diagnostics``, ...) means adding one function here with the
``@registry.command("name")`` decorator - nothing else changes.

Handlers receive the parsed JSON payload (``{}`` if the message had none or
failed to parse) and return either:

* a ``dict`` - published as the JSON response, or
* ``None`` - no response is published for this command.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from ..const import VERSION

_LOGGER = logging.getLogger(__name__)

CommandHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None]]


@dataclass
class SystemCommandRegistry:
    """Registry mapping a system command name to its async handler."""

    _handlers: dict[str, CommandHandler] = field(default_factory=dict)

    # Optional shared state handlers can read (e.g. {"coordinator": ...}).
    # Set once from __init__.py after the coordinator is created; handlers
    # that don't need it (like ping) simply never touch this.
    context: dict[str, Any] = field(default_factory=dict)

    def command(self, name: str) -> Callable[[CommandHandler], CommandHandler]:
        """Decorator: ``@registry.command("ping")`` registers a handler."""

        def _decorator(func: CommandHandler) -> CommandHandler:
            self.register(name, func)
            return func

        return _decorator

    def register(self, name: str, handler: CommandHandler) -> None:
        """Register (or override) the handler for *name*."""

        self._handlers[name] = handler

    def unregister(self, name: str) -> None:
        self._handlers.pop(name, None)

    def has(self, name: str) -> bool:
        return name in self._handlers

    @property
    def commands(self) -> list[str]:
        return sorted(self._handlers)

    async def dispatch(
        self, name: str, payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Run the handler registered for *name*, if any."""

        handler = self._handlers.get(name)
        if handler is None:
            _LOGGER.debug(
                "Dezhoosh system: no handler registered for command '%s'", name
            )
            return None

        try:
            return await handler(payload)
        except Exception:  # noqa: BLE001 - never let a bad command crash MQTT
            _LOGGER.exception(
                "Dezhoosh system: handler for '%s' raised an error", name
            )
            return None


# Global registry instance shared by the integration.
registry = SystemCommandRegistry()


def _with_correlation_id(
    payload: dict[str, Any], response: dict[str, Any]
) -> dict[str, Any]:
    """Echo back an ``id`` correlation field if the caller supplied one."""

    if isinstance(payload, dict) and "id" in payload:
        response["id"] = payload["id"]
    return response


# ---------------------------------------------------------------------------
# Built-in system commands
# ---------------------------------------------------------------------------


@registry.command("ping")
async def _handle_ping(payload: dict[str, Any]) -> dict[str, Any]:
    """Health handshake: reply with this integration's identity/version."""

    return _with_correlation_id(
        payload,
        {"status": "ok", "integration": "dezhoosh", "version": VERSION},
    )


@registry.command("get_info")
async def _handle_get_info(payload: dict[str, Any]) -> dict[str, Any]:
    """Return basic integration info - handy for firmware diagnostics."""

    return _with_correlation_id(
        payload,
        {"status": "ok", "integration": "dezhoosh", "version": VERSION},
    )


@registry.command("list_devices")
async def _handle_list_devices(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the device_ids currently known to the coordinator.

    Demonstrates a command that needs live integration state: it reads the
    coordinator through ``registry.context`` (set once in ``__init__.py``)
    instead of the transport layer having to know anything about devices.
    """

    coordinator = registry.context.get("coordinator")
    device_ids = sorted(coordinator.devices) if coordinator else []

    return _with_correlation_id(
        payload, {"status": "ok", "devices": device_ids, "count": len(device_ids)}
    )

```

### `sensor.py`

```python
"""Sensor platform for Dezhoosh.

Exposes any sensors declared in a device's discovery payload as sensor
entities grouped under the same Home Assistant device.
"""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN, SIGNAL_ADD_SENSOR
from .devices import DezhooshCoordinator, DezhooshDevice, DezhooshSensor

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dezhoosh sensors and listen for future discoveries."""

    coordinator: DezhooshCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]

    known: set[str] = set()

    @callback
    def _add_device(device_id: str) -> None:
        device = coordinator.devices.get(device_id)
        if device is None or not device.sensors:
            return

        entities: list[DezhooshSensorEntity] = []
        for sensor in device.sensors:
            unique = f"{device.device_id}_{sensor.key}"
            if unique in known:
                continue
            known.add(unique)
            entities.append(DezhooshSensorEntity(coordinator, device, sensor))

        if entities:
            async_add_entities(entities)

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_ADD_SENSOR, _add_device)
    )

    for device_id in list(coordinator.devices):
        _add_device(device_id)


class DezhooshSensorEntity(SensorEntity):
    """A single sensor reading from a Dezhoosh device."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: DezhooshCoordinator,
        device: DezhooshDevice,
        sensor: DezhooshSensor,
    ) -> None:
        self._coordinator = coordinator
        self._device_id = device.device_id
        self._sensor = sensor
        self._attr_unique_id = f"{device.device_id}_{sensor.key}"
        self._attr_name = sensor.name
        self._attr_device_info = device.device_info()
        self._attr_device_class = sensor.device_class
        self._attr_native_unit_of_measurement = sensor.unit
        if sensor.icon:
            self._attr_icon = sensor.icon

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._coordinator.async_add_listener(
                self._device_id, self.async_write_ha_state
            )
        )

    @property
    def available(self) -> bool:
        return self._device_id in self._coordinator.devices

    @property
    def native_value(self):
        state = self._coordinator.get_state(self._device_id)
        return state.get(self._sensor.key)

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "device_id": self._device_id,
            "sensor": self._sensor.key,
        }

```

### `strings.json`

```json
{
    "config": {
        "step": {
            "user": {
                "title": "Dezhoosh",
                "description": "Set up Dezhoosh device discovery. Devices are found automatically over MQTT - no further configuration is needed."
            }
        },
        "abort": {
            "already_configured": "Dezhoosh is already configured."
        }
    }
}

```

### `switch.py`

```python
"""Switch platform for Dezhoosh.

Each discovered switch device exposes one switch entity per bridge/channel.
A single-bridge device produces one entity, double-bridge two, triple-bridge
three - all grouped under a single Home Assistant device so the custom card
can render them together.
"""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN, SIGNAL_ADD_SWITCH
from .devices import DezhooshChannel, DezhooshCoordinator, DezhooshDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dezhoosh switches and listen for future discoveries."""

    coordinator: DezhooshCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]

    known: set[str] = set()

    @callback
    def _add_device(device_id: str) -> None:
        device = coordinator.devices.get(device_id)
        if device is None or not device.is_switch:
            return

        entities: list[DezhooshSwitch] = []
        for channel in device.channels:
            unique = f"{device.device_id}_{channel.key}"
            if unique in known:
                continue
            known.add(unique)
            entities.append(DezhooshSwitch(coordinator, device, channel))

        if entities:
            async_add_entities(entities)

    # Register for future discoveries first.
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_ADD_SWITCH, _add_device)
    )

    # Then add any switches discovered before the platform loaded.
    for device_id in list(coordinator.devices):
        _add_device(device_id)


class DezhooshSwitch(SwitchEntity):
    """A single bridge/channel of a Dezhoosh switch device."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: DezhooshCoordinator,
        device: DezhooshDevice,
        channel: DezhooshChannel,
    ) -> None:
        self._coordinator = coordinator
        self._device_id = device.device_id
        self._channel = channel
        self._attr_unique_id = f"{device.device_id}_{channel.key}"
        self._attr_name = channel.name
        self._attr_device_info = device.device_info()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._coordinator.async_add_listener(
                self._device_id, self.async_write_ha_state
            )
        )

    @property
    def available(self) -> bool:
        return self._device_id in self._coordinator.devices

    @property
    def is_on(self) -> bool:
        state = self._coordinator.get_state(self._device_id)
        value = state.get(self._channel.key)
        if isinstance(value, str):
            return value.upper() == "ON"
        return bool(value)

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "device_id": self._device_id,
            "channel": self._channel.key,
            "bridge_index": self._channel.index,
        }

    async def async_turn_on(self, **kwargs) -> None:
        await self._coordinator.async_set_channel(
            self._device_id, self._channel.key, True
        )

    async def async_turn_off(self, **kwargs) -> None:
        await self._coordinator.async_set_channel(
            self._device_id, self._channel.key, False
        )

```

### `themes/dezhoosh.yaml`

```yaml
# Dezhoosh Aqua - green/blue glass theme for Home Assistant.
#
# To use manually, copy this file into <config>/themes/ and add
#   frontend:
#     themes: !include_dir_merge_named themes
# to configuration.yaml, then pick "Dezhoosh Aqua" from your user profile.
#
# The Dezhoosh integration also registers this theme automatically at runtime.
Dezhoosh Aqua:
  # Base palette
  primary-color: "#12b6a6"
  accent-color: "#1fd4c3"
  dark-primary-color: "#0e8f83"
  light-primary-color: "#8ff0e6"

  # Backgrounds
  primary-background-color: "#071c22"
  secondary-background-color: "#0c2a31"
  card-background-color: "rgba(16, 46, 54, 0.72)"
  ha-card-background: "rgba(16, 46, 54, 0.72)"

  # Text
  primary-text-color: "#e6fffb"
  secondary-text-color: "#8fd7cf"
  text-primary-color: "#04141a"
  disabled-text-color: "#4f7f79"

  # Structure
  divider-color: "rgba(31, 212, 195, 0.16)"
  ha-card-border-radius: "18px"
  ha-card-box-shadow: "0 8px 30px rgba(4, 20, 26, 0.45)"

  # App header / sidebar
  app-header-background-color: "rgba(7, 28, 34, 0.85)"
  app-header-text-color: "#e6fffb"
  sidebar-background-color: "rgba(7, 28, 34, 0.9)"
  sidebar-icon-color: "#8fd7cf"
  sidebar-selected-icon-color: "#1fd4c3"
  sidebar-selected-text-color: "#1fd4c3"

  # States / switches
  switch-checked-color: "#1fd4c3"
  switch-checked-track-color: "#12b6a6"
  paper-item-icon-active-color: "#1fd4c3"
  state-icon-active-color: "#1fd4c3"

  # Badges / tables
  label-badge-background-color: "#0c2a31"
  label-badge-text-color: "#e6fffb"
  table-row-background-color: "#0c2a31"
  table-row-alternative-background-color: "#0e333b"

```

### `translations/en.json`

```json
{
    "config": {
        "step": {
            "user": {
                "title": "Dezhoosh",
                "description": "Set up Dezhoosh device discovery. Devices are found automatically over MQTT - no further configuration is needed."
            }
        },
        "abort": {
            "already_configured": "Dezhoosh is already configured."
        }
    }
}

```

### `translations/fa.json`

```json
{
    "config": {
        "step": {
            "user": {
                "title": "دژهوش",
                "description": "راه‌اندازی شناسایی خودکار دستگاه‌های دژهوش. دستگاه‌ها به‌صورت خودکار از طریق MQTT شناسایی می‌شوند و نیازی به تنظیم دیگری نیست."
            }
        },
        "abort": {
            "already_configured": "دژهوش قبلاً پیکربندی شده است."
        }
    }
}

```

