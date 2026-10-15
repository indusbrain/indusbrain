import React, { useEffect, useRef } from 'react';

/**
 * Application backdrop: a black field with live film grain and a grid that
 * comes into focus around the cursor.
 *
 * Mounted once at the app root, fixed behind everything (see .backdrop* in
 * index.css):
 *   grain       an SVG noise layer that jitters in steps, like film grain
 *   grid        a faint grid everywhere
 *   grid-focus  the same grid, brighter, visible only inside a soft circle
 *               centred on the cursor (--mx / --my)
 *
 * Moving — or dragging — the pointer slides that circle. It eases toward the
 * pointer in a single requestAnimationFrame loop that stops itself once it has
 * arrived, so an idle page does no work. Only two CSS variables change: no
 * React state, no re-renders.
 *
 * On touch-only devices there is no cursor to follow, so the focus circle stays
 * parked off-screen. Under prefers-reduced-motion the circle snaps instead of
 * easing, and the grain does not jitter.
 */
export const Backdrop: React.FC<{ className?: string }> = ({ className }) => {
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;

    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const target = { x: -400, y: -400 };
    const current = { x: -400, y: -400 };
    let frame = 0;

    const paint = () => {
      root.style.setProperty('--mx', `${current.x.toFixed(1)}px`);
      root.style.setProperty('--my', `${current.y.toFixed(1)}px`);
    };

    const tick = () => {
      const dx = target.x - current.x;
      const dy = target.y - current.y;
      if (reduce || (Math.abs(dx) < 0.4 && Math.abs(dy) < 0.4)) {
        current.x = target.x;
        current.y = target.y;
        paint();
        frame = 0;
        return;
      }
      // Ease toward the pointer: ~18% of the remaining distance per frame.
      current.x += dx * 0.18;
      current.y += dy * 0.18;
      paint();
      frame = requestAnimationFrame(tick);
    };

    const onMove = (event: PointerEvent) => {
      // First move: appear under the cursor instead of sliding in from nowhere.
      if (current.x < 0 && current.y < 0) {
        current.x = event.clientX;
        current.y = event.clientY;
      }
      target.x = event.clientX;
      target.y = event.clientY;
      if (!frame) frame = requestAnimationFrame(tick);
    };

    const onLeave = () => {
      target.x = -400;
      target.y = -400;
      if (!frame) frame = requestAnimationFrame(tick);
    };

    window.addEventListener('pointermove', onMove, { passive: true });
    document.documentElement.addEventListener('pointerleave', onLeave);
    return () => {
      window.removeEventListener('pointermove', onMove);
      document.documentElement.removeEventListener('pointerleave', onLeave);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <div ref={rootRef} aria-hidden="true" className={['backdrop', className].filter(Boolean).join(' ')}>
      <div className="backdrop__noise" />
      <div className="backdrop__grid" />
      <div className="backdrop__grid-focus" />
    </div>
  );
};
