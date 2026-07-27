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
