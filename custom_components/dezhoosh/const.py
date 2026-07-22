"""Constants for Dezhoosh."""

DOMAIN = "dezhoosh"

NAME = "Dezhoosh"

VERSION = "0.0.1"

MQTT_ROOT = "dezhoosh"

TOPIC_SYSTEM_PREFIX = f"{MQTT_ROOT}/system"

# Wildcard used to route ANY system command (ping, get_info, future
# commands...) through a single subscription. See system_commands.py for
# the registry of what each command name actually does.
TOPIC_SYSTEM_COMMAND_WILDCARD = f"{TOPIC_SYSTEM_PREFIX}/+"

# Kept for backwards compatibility / documentation - the ping/pong handshake
# is still the first command implemented in system_commands.py.
TOPIC_SYSTEM_PING = f"{TOPIC_SYSTEM_PREFIX}/ping"

TOPIC_SYSTEM_PONG = f"{TOPIC_SYSTEM_PREFIX}/pong"

CLOUD_BASE_URL = "https://lab.masihch.com/haos"

# ---------------------------------------------------------------------------
# Platforms
# ---------------------------------------------------------------------------

PLATFORMS = ["switch", "sensor"]

# ---------------------------------------------------------------------------
# MQTT topic structure
# ---------------------------------------------------------------------------
#
# System (integration <-> Dezhoosh) commands - generic router:
#   dezhoosh/system/<command>            <- request
#   dezhoosh/system/<command>/response   -> response
#   (the built-in "ping" command replies on dezhoosh/system/pong instead,
#    for backwards compatibility with existing firmware)
#
# Device discovery (device -> integration):
#   dezhoosh/discovery/<device_id>/config   (retained JSON describing the device)
#
# Device runtime topics (per device, referenced inside the discovery payload):
#   dezhoosh/<device_id>/state             (device -> integration)
#   dezhoosh/<device_id>/set               (integration -> device)
#
# The discovery topic uses a "+" wildcard on the device id segment.

TOPIC_DISCOVERY_PREFIX = f"{MQTT_ROOT}/discovery"

TOPIC_DISCOVERY_WILDCARD = f"{TOPIC_DISCOVERY_PREFIX}/+/config"

TOPIC_DEVICE_AVAILABILITY = f"{MQTT_ROOT}/status"

# ---------------------------------------------------------------------------
# Device model / discovery vocabulary
# ---------------------------------------------------------------------------

MANUFACTURER = "Dezhoosh"

# Supported switch models keyed by number of gangs (bridges).
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

# ---------------------------------------------------------------------------
# Dispatcher signals (used to push newly discovered entities to platforms)
# ---------------------------------------------------------------------------

SIGNAL_ADD_SWITCH = f"{DOMAIN}_add_switch"

SIGNAL_ADD_SENSOR = f"{DOMAIN}_add_sensor"

# Key under which the runtime store lives in hass.data[DOMAIN][entry_id]
DATA_COORDINATOR = "coordinator"
