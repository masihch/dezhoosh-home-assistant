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
