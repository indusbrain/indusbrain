import React, { useEffect, useRef, useState } from 'react';
import { motion, useInView, useReducedMotion, type Variants } from 'motion/react';

/**
 * Shared motion vocabulary.
 *
 * One rule drives everything: content arrives the way a reading comes online
 * on an instrument panel — it rises a few pixels into place and settles, in
 * reading order. Durations are short, curves are custom (tokens.css mirrors
 * them for CSS), and only transform + opacity are animated.
 *
 * Every helper here collapses to a static render under prefers-reduced-motion.
 */

/** Mirrors --ease-valve in tokens.css: opens quickly, settles softly. */
export const EASE_VALVE = [0.2, 0.8, 0.2, 1] as const;
/** Mirrors --ease-pressure: symmetric, for things that go and return. */
export const EASE_PRESSURE = [0.65, 0, 0.35, 1] as const;

const containerVariants: Variants = {
  hidden: {},
  shown: (stagger: number = 0.06) => ({ transition: { staggerChildren: stagger } }),
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 14 },
  shown: { opacity: 1, y: 0, transition: { duration: 0.55, ease: EASE_VALVE } },
};

/**
 * Staggered reveal. Children wrapped in <RevealItem> come in one after another
 * the first time the group scrolls into view.
 */
export const Reveal: React.FC<{
  children: React.ReactNode;
  className?: string;
  stagger?: number;
  as?: 'div' | 'section' | 'ul';
}> = ({ children, className, stagger = 0.06, as = 'div' }) => {
  const reduce = useReducedMotion();
  if (reduce) {
    const Tag = as;
    return <Tag className={className}>{children}</Tag>;
  }
  const Component = motion[as];
  return (
    <Component
      className={className}
      variants={containerVariants}
      custom={stagger}
      initial="hidden"
      whileInView="shown"
      viewport={{ once: true, amount: 0.08 }}
    >
      {children}
    </Component>
  );
};

export const RevealItem: React.FC<{
  children: React.ReactNode;
  className?: string;
  as?: 'div' | 'li' | 'section' | 'article';
}> = ({ children, className, as = 'div' }) => {
  const reduce = useReducedMotion();
  if (reduce) {
    const Tag = as;
    return <Tag className={className}>{children}</Tag>;
  }
  const Component = motion[as];
  return (
    <Component className={className} variants={itemVariants}>
      {children}
    </Component>
  );
};

/**
 * Animated numeral: counts from 0 to `value` once it scrolls into view, like a
 * gauge needle sweeping up to its reading. Decimal places follow the input.
 * The final value is always what screen readers get (aria-label), never the
 * intermediate frames.
 */
export const CountUp: React.FC<{
  value: number;
  duration?: number;
  className?: string;
  decimals?: number;
}> = ({ value, duration = 1100, className, decimals }) => {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const places = decimals ?? (Number.isInteger(value) ? 0 : 1);
  // `null` means "show the real value". The sweep only ever overrides it while
  // frames are actually being painted, so a throttled or hidden tab (where
  // requestAnimationFrame never fires) still shows the correct number rather
  // than a misleading 0.
  const [sweep, setSweep] = useState<number | null>(null);

  useEffect(() => {
    if (reduce || !inView) return;
    let frame = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      // ease-out-expo: fast sweep, gentle settle
      const eased = 1 - Math.pow(2, -10 * t);
      if (t < 1) {
        setSweep(value * eased);
        frame = requestAnimationFrame(tick);
      } else {
        setSweep(null);
      }
    };
    frame = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(frame);
      setSweep(null);
    };
  }, [value, duration, inView, reduce]);

  const display = sweep ?? value;
  return (
    <span ref={ref} className={className} aria-label={value.toFixed(places)}>
      <span aria-hidden="true">{display.toFixed(places)}</span>
    </span>
  );
};

/** Hook: true once the element has entered the viewport (for CSS-driven draws). */
export function useSeen<T extends Element>() {
  const ref = useRef<T>(null);
  const seen = useInView(ref, { once: true, amount: 0.2 });
  return [ref, seen] as const;
}
