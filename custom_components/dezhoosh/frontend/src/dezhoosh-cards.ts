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
