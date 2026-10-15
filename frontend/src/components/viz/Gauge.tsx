import React from 'react';
import { useSeen } from '../motion/Motion';

/**
 * Instrument dial — a 270° pressure-gauge arc with graduation ticks.
 *
 * On first view the reading sweeps from zero to its value (stroke-dashoffset
 * only, via the `gauge-sweep` keyframes in index.css). Without the animation
 * — hidden tab, reduced motion — the arc simply renders at its value.
 *
 * The value is exposed as role="meter", so screen readers announce the reading,
 * not the drawing.
 */
const R = 80;
const ARC = 2 * Math.PI * R * 0.75; // visible arc length (270°)

export const Gauge: React.FC<{
  value: number;
  max?: number;
  label: string;
  /** CSS colour for the reading arc, e.g. 'var(--color-amber)'. */
  color?: string;
  className?: string;
}> = ({ value, max = 100, label, color = 'var(--color-accent)', className }) => {
  const [ref, seen] = useSeen<SVGSVGElement>();
  const pct = Math.max(0, Math.min(1, value / max));
  const offset = ARC * (1 - pct);

  // Graduation ticks every 10%, major every 50%. 135° → 405° (clockwise).
  const ticks = Array.from({ length: 11 }, (_, i) => {
    const angle = ((135 + i * 27) * Math.PI) / 180;
    const major = i % 5 === 0;
    const r1 = major ? 92 : 94;
    const r2 = 100;
    return {
      i,
      major,
      x1: 110 + r1 * Math.cos(angle),
      y1: 110 + r1 * Math.sin(angle),
      x2: 110 + r2 * Math.cos(angle),
      y2: 110 + r2 * Math.sin(angle),
    };
  });

  return (
    <svg
      ref={ref}
      viewBox="0 0 220 200"
      className={className}
      role="meter"
      aria-label={label}
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={max}
    >
      {ticks.map((t) => (
        <line
          key={t.i}
          x1={t.x1}
          y1={t.y1}
          x2={t.x2}
          y2={t.y2}
          stroke={t.major ? 'var(--color-ink-primary)' : 'var(--color-ink-faint)'}
          strokeWidth={t.major ? 2 : 1.2}
        />
      ))}
      {/* Track */}
      <circle
        cx="110"
        cy="110"
        r={R}
        fill="none"
        stroke="var(--color-surface-overlay)"
        strokeWidth="14"
        strokeDasharray={`${ARC} ${2 * Math.PI * R}`}
        transform="rotate(135 110 110)"
      />
      {/* Reading */}
      <circle
        cx="110"
        cy="110"
        r={R}
        fill="none"
        stroke={color}
        strokeWidth="14"
        strokeDasharray={`${ARC} ${2 * Math.PI * R}`}
        strokeDashoffset={offset}
        transform="rotate(135 110 110)"
        className={seen ? 'gauge-sweep' : undefined}
        style={{ ['--gauge-from' as string]: ARC }}
      />
      {/* Scale labels */}
      <text x="38" y="190" fontSize="10" fill="var(--color-ink-muted)" className="font-[family-name:var(--font-mono)]">
        0
      </text>
      <text x="170" y="190" fontSize="10" fill="var(--color-ink-muted)" className="font-[family-name:var(--font-mono)]">
        {max}
      </text>
    </svg>
  );
};
