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
