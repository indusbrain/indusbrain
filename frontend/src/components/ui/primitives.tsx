import React from 'react';
import { CountUp, useSeen } from '../motion/Motion';
import { FaultNotice } from './FaultNotice';

/**
 * Shared UI primitives — frosted-glass design language.
 *
 * THE RULE: boxes are only for main containers (Card). A status, tag, label or
 * sub-text is never boxed — it is coloured text. `Badge` therefore renders
 * plain coloured text; the colour (red / amber / green / blue) is the signal.
 *
 * All colours, radii and curves come from src/styles/tokens.css. Export names
 * and props are unchanged from earlier designs, so every page keeps working.
 */

/** Tiny class-name joiner (avoids pulling in clsx for one function). */
export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ');
}

// ---------------------------------------------------------------------------
// Card — the glass container. The only boxed element in the product.
// ---------------------------------------------------------------------------
export const Card: React.FC<{
  children: React.ReactNode;
  className?: string;
  as?: 'div' | 'section' | 'article';
}> = ({ children, className, as: Tag = 'div' }) => (
  <Tag
    // `overflow-hidden` keeps wide children (notably tables with a min-width)
    // inside the card so their own overflow-x-auto wrapper scrolls, instead of
    // pushing the whole page sideways on narrow screens.
    // `min-w-0` lets the card shrink below its content width inside a grid.
    className={cx('glass relative min-w-0 overflow-hidden rounded-[var(--radius-sheet)]', className)}
  >
    {children}
  </Tag>
);

export const CardHeader: React.FC<{
  title: string;
  description?: string;
  icon?: React.ReactNode;
  actions?: React.ReactNode;
}> = ({ title, description, icon, actions }) => (
  <div className="flex items-start justify-between gap-4 border-b border-[var(--color-line-subtle)] px-5 py-4">
    <div className="flex min-w-0 items-start gap-3">
      {icon && <span className="mt-0.5 text-[var(--color-ink-muted)]">{icon}</span>}
      <div className="min-w-0">
        <h2 className="truncate text-[16px] leading-snug font-semibold text-[var(--color-ink-primary)]">
          {title}
        </h2>
        {description && (
          <p className="mt-0.5 text-[13px] text-[var(--color-ink-muted)]">{description}</p>
        )}
      </div>
    </div>
    {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
  </div>
);

// ---------------------------------------------------------------------------
// Button — a control, so it may have a surface. Secondary is glass.
// ---------------------------------------------------------------------------
type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md';
};

export const Button: React.FC<ButtonProps> = ({
  variant = 'secondary',
  size = 'md',
  className,
  children,
  ...rest
}) => {
  const base =
    'pressable inline-flex items-center justify-center gap-2 rounded-[var(--radius-control)] font-medium ' +
    'disabled:cursor-not-allowed disabled:opacity-45';

  const sizes = {
    sm: 'px-3 py-1.5 text-[12.5px]',
    md: 'px-4 py-2 text-[13.5px]',
  };

  const variants = {
    primary:
      'bg-[var(--color-accent)] text-[var(--color-on-accent)] shadow-[inset_0_1px_0_rgb(255_255_255/0.25)] ' +
      'hover:bg-[var(--color-accent-hover)] disabled:hover:bg-[var(--color-accent)]',
    secondary:
      'btn-glass text-[var(--color-ink-primary)] hover:bg-[var(--color-surface-hover)]',
    ghost:
      'text-[var(--color-ink-muted)] hover:bg-[var(--color-surface-overlay)] hover:text-[var(--color-ink-primary)]',
    danger:
      'text-[var(--color-danger)] hover:bg-[var(--color-danger-soft)]',
  };

  return (
    <button className={cx(base, sizes[size], variants[variant], className)} {...rest}>
      {children}
    </button>
  );
};

// ---------------------------------------------------------------------------
// Badge — NOT a box. Coloured text only; the colour is the status.
// ---------------------------------------------------------------------------
export type BadgeTone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info';

const BADGE_TONES: Record<BadgeTone, string> = {
  neutral: 'text-[var(--color-ink-secondary)]',
  accent: 'text-[var(--color-accent)]',
  success: 'text-[var(--color-success)]',
  warning: 'text-[var(--color-warning)]',
  danger: 'text-[var(--color-danger)]',
  info: 'text-[var(--color-info)]',
};

export const Badge: React.FC<{
  children: React.ReactNode;
  tone?: BadgeTone;
  mono?: boolean;
  className?: string;
  title?: string;
}> = ({ children, tone = 'neutral', mono = false, className, title }) => (
  <span
    title={title}
    className={cx(
      'inline-flex items-center gap-1 text-[12.5px] font-medium whitespace-nowrap',
      mono && 'font-[family-name:var(--font-mono)] text-[12px] tracking-tight',
      BADGE_TONES[tone],
      className,
    )}
  >
    {children}
  </span>
);

// ---------------------------------------------------------------------------
// Metric tile — a gauge readout. Numbers sweep up to their value on first view.
// ---------------------------------------------------------------------------
export const Metric: React.FC<{
  label: string;
  value: React.ReactNode;
  unit?: string;
  hint?: string;
  tone?: 'default' | 'success' | 'warning' | 'danger';
  icon?: React.ReactNode;
}> = ({ label, value, unit, hint, tone = 'default', icon }) => {
  const valueTone = {
    default: 'text-[var(--color-ink-primary)]',
    success: 'text-[var(--color-success)]',
    warning: 'text-[var(--color-warning)]',
    danger: 'text-[var(--color-danger)]',
  }[tone];

  return (
    <Card className="sheet-hover p-5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[13px] font-medium text-[var(--color-ink-muted)]">{label}</span>
        {icon && <span className="text-[var(--color-ink-muted)]">{icon}</span>}
      </div>
      <div className="mt-3 flex items-baseline gap-1.5">
        <span
          className={cx(
            'font-display text-[length:var(--text-figure)] leading-none font-semibold tabular-nums',
            valueTone,
          )}
        >
          {typeof value === 'number' ? <CountUp value={value} /> : value}
        </span>
        {unit && <span className="text-[13px] text-[var(--color-ink-muted)]">{unit}</span>}
      </div>
      {hint && <p className="mt-2 text-[12.5px] leading-snug text-[var(--color-ink-muted)]">{hint}</p>}
    </Card>
  );
};

// ---------------------------------------------------------------------------
// Stat — a figure with a caption, for use INSIDE a container. Unboxed.
// ---------------------------------------------------------------------------
export const Stat: React.FC<{
  label: string;
  value: number;
  tone?: 'default' | 'success' | 'warning' | 'danger';
}> = ({ label, value, tone = 'default' }) => {
  const valueTone = {
    default: 'text-[var(--color-ink-primary)]',
    success: 'text-[var(--color-success)]',
    warning: 'text-[var(--color-warning)]',
    danger: 'text-[var(--color-danger)]',
  }[tone];
  return (
    <div>
      <p className="eyebrow">{label}</p>
      <p className={cx('mt-1 font-display text-[28px] leading-none font-semibold tabular-nums', valueTone)}>
        <CountUp value={value} />
      </p>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Meter — a labelled proportion bar that fills from zero when first seen
// ---------------------------------------------------------------------------
const METER_FILL = {
  accent: 'bg-[var(--color-accent)]',
  success: 'bg-[var(--color-pipe)]',
  warning: 'bg-[var(--color-amber)]',
  danger: 'bg-[var(--color-danger)]',
} as const;

export const Meter: React.FC<{
  label: string;
  value: number;
  max?: number;
  tone?: 'accent' | 'success' | 'warning' | 'danger';
  suffix?: string;
}> = ({ label, value, max = 100, tone = 'accent', suffix = '%' }) => {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const [ref, seen] = useSeen<HTMLDivElement>();

  return (
    <div ref={ref}>
      <div className="mb-1.5 flex items-baseline justify-between gap-2">
        <span className="text-[13px] text-[var(--color-ink-secondary)]">{label}</span>
        <span className="font-[family-name:var(--font-mono)] text-[12.5px] font-medium tabular-nums text-[var(--color-ink-primary)]">
          {value}
          {suffix}
        </span>
      </div>
      <div
        className="h-2 w-full overflow-hidden rounded-full bg-[var(--color-surface-overlay)]"
        role="meter"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label}
      >
        <div
          className={cx('h-full rounded-full', METER_FILL[tone], seen && 'animate-extend-x')}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Empty state — always states WHY something is empty.
// ---------------------------------------------------------------------------
export const EmptyState: React.FC<{
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  compact?: boolean;
}> = ({ icon, title, description, action, compact = false }) => (
  <div
    className={cx(
      'flex flex-col items-center justify-center text-center',
      compact ? 'gap-2 px-4 py-8' : 'gap-4 px-6 py-14',
    )}
  >
    {icon && <div className="text-[var(--color-ink-muted)]">{icon}</div>}
    <div>
      <p className="font-display text-[16px] font-semibold text-[var(--color-ink-primary)]">{title}</p>
      {description && (
        <p className="mx-auto mt-1.5 max-w-md text-[13.5px] leading-relaxed text-[var(--color-ink-muted)]">
          {description}
        </p>
      )}
    </div>
    {action}
  </div>
);

// ---------------------------------------------------------------------------
// Skeleton loader — a glass pane with a soft sweep
// ---------------------------------------------------------------------------
export const Skeleton: React.FC<{ className?: string }> = ({ className }) => (
  <div
    className={cx(
      'glass relative overflow-hidden rounded-[var(--radius-sheet)] pipe-flow',
      className,
    )}
    aria-hidden="true"
  />
);

// ---------------------------------------------------------------------------
// Inline error — the product's fault notice (see ui/FaultNotice.tsx)
// ---------------------------------------------------------------------------
export const ErrorNotice: React.FC<{
  title: string;
  detail?: string;
  onRetry?: () => void;
}> = ({ title, detail, onRetry }) => (
  <FaultNotice title={title} detail={detail} onRetry={onRetry} kicker="Request failed" compact />
);

// ---------------------------------------------------------------------------
// Status dot
// ---------------------------------------------------------------------------
export const StatusDot: React.FC<{ online: boolean; degraded?: boolean }> = ({
  online,
  degraded = false,
}) => (
  <span
    className={cx(
      'inline-block h-2 w-2 shrink-0 rounded-full',
      online
        ? degraded
          ? 'bg-[var(--color-amber)]'
          : 'bg-[var(--color-pipe)]'
        : 'bg-[var(--color-danger)]',
    )}
  />
);

// ---------------------------------------------------------------------------
// Section heading — title with a hairline leader running to the edge
// ---------------------------------------------------------------------------
export const SectionTitle: React.FC<{
  children: React.ReactNode;
  hint?: string;
  actions?: React.ReactNode;
}> = ({ children, hint, actions }) => (
  <div className="mb-3 flex items-end justify-between gap-4">
    <div className="min-w-0 flex-1">
      <div className="flex items-center gap-3">
        <h2 className="shrink-0 text-[16px] font-semibold text-[var(--color-ink-primary)]">{children}</h2>
        <span aria-hidden="true" className="h-px flex-1 bg-[var(--color-line-default)]" />
      </div>
      {hint && <p className="mt-0.5 text-[13px] text-[var(--color-ink-muted)]">{hint}</p>}
    </div>
    {actions}
  </div>
);
