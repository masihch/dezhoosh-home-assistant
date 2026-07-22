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
