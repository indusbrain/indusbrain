import React, { useEffect, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { LogoMark, Wordmark } from '../brand/Logo';
import { EASE_PRESSURE, EASE_VALVE } from './Motion';

/**
 * Start-up loading screen, played once per browser session.
 *
 * Black, noisy, centred on the logo. A counter runs 0 → 100% with a hairline
 * progress bar, then the screen lifts away. It is a brand sequence on a fixed
 * ~2.4 s timeline (the app itself loads behind it), so the copy says
 * "Starting up" rather than pretending to report real network progress.
 *
 * Any key or click skips it. Never shown under prefers-reduced-motion.
 * The percentage is also exposed through role="progressbar" for assistive tech.
 */
const SESSION_KEY = 'indusbrain.intro-played';
const DURATION_MS = 2400;

function alreadyPlayed(): boolean {
  try {
    return sessionStorage.getItem(SESSION_KEY) === '1';
  } catch {
    return false;
  }
}

/** Ease-in-out so the counter lingers a beat at the start and at 100. */
const easeInOut = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);

export const IntroSequence: React.FC = () => {
  const reduce = useReducedMotion();
  const [visible, setVisible] = useState(() => !reduce && !alreadyPlayed());
  const [percent, setPercent] = useState(0);

  useEffect(() => {
    if (!visible) return;
    try {
      sessionStorage.setItem(SESSION_KEY, '1');
    } catch {
      /* ignore — worst case the intro plays again next load */
    }

    let frame = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / DURATION_MS);
      setPercent(Math.round(easeInOut(t) * 100));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);

    // Hold on 100% for a beat, then lift. The timeout also covers a hidden tab
    // where animation frames never fire, so the app is never stuck behind this.
    const done = setTimeout(() => setVisible(false), DURATION_MS + 450);
    const skip = () => setVisible(false);
    window.addEventListener('keydown', skip);
    window.addEventListener('pointerdown', skip);
    return () => {
      cancelAnimationFrame(frame);
      clearTimeout(done);
      window.removeEventListener('keydown', skip);
      window.removeEventListener('pointerdown', skip);
    };
  }, [visible]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          className="noir fixed inset-0 z-[90] flex flex-col items-center justify-center"
          exit={{ y: '-100%', transition: { duration: 0.7, ease: EASE_PRESSURE } }}
          role="progressbar"
          aria-label="Starting IndusBrain"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
        >
          {/* Noise sits under the content; the .noir variant makes it heavier. */}
          <div className="backdrop__noise pointer-events-none absolute inset-0" aria-hidden="true" />

          <div className="relative flex flex-col items-center">
            {/* Dark theme token set so the logo reads light-on-black everywhere */}
            <div data-theme="dark" className="text-[#F3F3F5]">
              <LogoMark size={92} />
            </div>

            <motion.div
              className="mt-7"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: EASE_VALVE, delay: 0.5 }}
            >
              <Wordmark className="!text-[34px]" />
            </motion.div>

            <div className="mt-14 flex w-[min(320px,70vw)] flex-col gap-3">
              <div className="flex items-baseline justify-between text-[12px] text-white/55">
                <span className="tracking-[0.08em] uppercase">Starting up</span>
                <span className="font-[family-name:var(--font-mono)] text-[15px] font-medium text-white tabular-nums">
                  {percent}%
                </span>
              </div>
              <div className="h-px w-full bg-white/15">
                <div
                  className="h-[2px] -translate-y-px origin-left bg-white"
                  style={{ transform: `scaleX(${percent / 100})`, transition: 'transform 80ms linear' }}
                />
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
