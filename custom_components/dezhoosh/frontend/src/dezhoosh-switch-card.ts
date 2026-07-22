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
