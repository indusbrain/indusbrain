import React from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { useLocation } from 'react-router-dom';
import { EASE_VALVE } from './Motion';

/**
 * Page ("sheet") transition.
 *
 * Changing route is treated like turning to the next sheet in a drawing set:
 *   1. a process-blue line pressurises across the top of the canvas (scaleX),
 *   2. the outgoing sheet lifts away, the incoming one settles into place.
 * The line is the signal of *where* attention should go next; it is not
 * decoration. Transform and opacity only.
 */
export const RouteTransition: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const reduce = useReducedMotion();

  if (reduce) return <>{children}</>;

  return (
    <>
      {/* Keyed on the path so it replays on every navigation. */}
      <motion.div
        key={`line-${location.pathname}`}
        aria-hidden="true"
        className="pointer-events-none fixed top-0 right-0 left-0 z-[60] h-[3px] origin-left bg-[var(--color-accent)]"
        initial={{ scaleX: 0, opacity: 1 }}
        animate={{ scaleX: 1, opacity: 0 }}
        transition={{
          scaleX: { duration: 0.55, ease: EASE_VALVE },
          opacity: { duration: 0.3, delay: 0.5 },
        }}
      />
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0, transition: { duration: 0.45, ease: EASE_VALVE } }}
          exit={{ opacity: 0, y: -10, transition: { duration: 0.18, ease: [0.4, 0, 1, 1] } }}
        >
          {children}
        </motion.div>
      </AnimatePresence>
    </>
  );
};
