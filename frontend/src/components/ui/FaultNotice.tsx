import React from 'react';
import './fault.css';

/**
 * FaultNotice — the product's error / warning block.
 *
 * Deliberately quiet. A neutral glass pane like every other container, with a
 * thin line of red light down its left edge, one clean icon, a short title and
 * muted detail. The only motion is a single soft fade-in. Severity is carried
 * by colour, icon and wording — never by motion.
 *
 * Content is always real: `title` / `detail` are the actual error. Nothing
 * here invents an error code or a cause.
 */

export type FaultTone = 'danger' | 'warning';

const FaultIcon: React.FC = () => (
  <svg viewBox="0 0 24 24" className="fault__icon" aria-hidden="true" fill="none">
    <circle cx="12" cy="12" r="9.25" stroke="currentColor" strokeWidth="1.7" />
    <path d="M12 7.4v5.6" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
    <circle cx="12" cy="16.6" r="1.15" fill="currentColor" />
  </svg>
);

export const FaultNotice: React.FC<{
  title: string;
  detail?: string;
  /** Short label above the title, e.g. "Connection lost". */
  kicker?: string;
  tone?: FaultTone;
  onRetry?: () => void;
  retryLabel?: string;
  /** Tighter layout for use inside forms and lists. */
  compact?: boolean;
  /** Skip the fade-in (e.g. for notices that are part of a static page). */
  quiet?: boolean;
  className?: string;
  children?: React.ReactNode;
}> = ({
  title,
  detail,
  kicker,
  tone = 'danger',
  onRetry,
  retryLabel = 'Retry',
  compact = false,
  quiet = false,
  className,
  children,
}) => (
  <div
    role="alert"
    className={[
      'fault',
      tone === 'warning' && 'fault--warning',
      compact && 'fault--compact',
      quiet && 'fault--quiet',
      className,
    ]
      .filter(Boolean)
      .join(' ')}
  >
    <div className="fault__body">
      <FaultIcon />
      <div className="fault__text">
        {kicker && <p className="fault__kicker">{kicker}</p>}
        <h3 className="fault__title">{title}</h3>
        {detail && <p className="fault__detail">{detail}</p>}
        {children}
        {onRetry && (
          <button type="button" className="fault__btn" onClick={onRetry}>
            {retryLabel}
          </button>
        )}
      </div>
    </div>
  </div>
);
