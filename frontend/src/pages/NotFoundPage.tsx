import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Button } from '../components/ui/primitives';
import { PageBody } from '../components/AppShell';

/**
 * 404 — "This line terminates here."
 *
 * Drawn as a process line that runs in from the left and ends in a blind
 * flange (the P&ID symbol for a capped pipe). The requested path is shown as
 * the line number, so the user can see exactly what they asked for.
 */
export const NotFoundPage: React.FC = () => {
  const { pathname } = useLocation();

  return (
    <PageBody>
      <div className="grid min-h-[70vh] items-center gap-10 lg:grid-cols-[1.1fr_1fr]">
        <div>
          <p className="eyebrow">
            Error 404
          </p>
          <h1 className="mt-3 text-[length:var(--text-hero-figure)] leading-[0.92] font-semibold tracking-[-0.045em] text-[var(--color-ink-primary)]">
            This line
            <br />
            terminates here.
          </h1>
          <p className="mt-5 max-w-md text-[15px] leading-relaxed text-[var(--color-ink-muted)]">
            There is no page at this address. It may have been renamed, or the link was drawn to
            a pipe that was never installed.
          </p>
          <div className="mt-7 flex flex-wrap gap-2">
            <Link to="/">
              <Button variant="primary">Back to Overview</Button>
            </Link>
            <Link to="/ask">
              <Button variant="secondary">Ask IndusBrain instead</Button>
            </Link>
          </div>
        </div>

        {/* Process line ending in a blind flange */}
        <svg viewBox="0 0 420 160" className="w-full text-[var(--color-ink-primary)]" aria-hidden="true">
          <path
            d="M0 80H300"
            stroke="currentColor"
            strokeWidth="4"
            strokeDasharray="300"
            strokeDashoffset="300"
            style={{ animation: 'draw-line 1.1s var(--ease-valve) 0.2s forwards' }}
          />
          {/* flow arrow */}
          <path d="M140 68l16 12-16 12" stroke="currentColor" strokeWidth="3" fill="none" strokeLinejoin="round" />
          {/* blind flange */}
          <g className="animate-fade-in" style={{ animationDelay: '1.1s' }}>
            <rect x="300" y="44" width="10" height="72" fill="currentColor" />
            <rect x="316" y="44" width="10" height="72" fill="var(--color-danger)" />
          </g>
          <text
            x="0"
            y="140"
            className="font-[family-name:var(--font-mono)]"
            fontSize="12"
            fill="var(--color-ink-muted)"
          >
            {`LINE ${pathname.toUpperCase()} · BLIND FLANGE`}
          </text>
        </svg>
      </div>
    </PageBody>
  );
};
