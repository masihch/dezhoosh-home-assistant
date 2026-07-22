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
