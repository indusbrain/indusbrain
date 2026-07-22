import React from 'react';

/** Tiny class-name joiner (avoids pulling in clsx for one function). */
export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ');
}

// ---------------------------------------------------------------------------
// Card
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
    className={cx(
      'min-w-0 overflow-hidden rounded-xl border border-[var(--color-line-subtle)] bg-[var(--color-surface-raised)]',
      className,
    )}
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
        <h2 className="truncate text-[15px] font-semibold text-[var(--color-ink-primary)]">{title}</h2>
        {description && (
          <p className="mt-0.5 text-[13px] text-[var(--color-ink-muted)]">{description}</p>
        )}
      </div>
    </div>
    {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
  </div>
);

// ---------------------------------------------------------------------------
// Button
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
    'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors ' +
    'disabled:cursor-not-allowed disabled:opacity-45';

  const sizes = {
    sm: 'px-2.5 py-1.5 text-[12px]',
    md: 'px-3.5 py-2 text-[13px]',
  };

  const variants = {
    primary:
      'bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)] disabled:hover:bg-[var(--color-accent)]',
    secondary:
      'border border-[var(--color-line-default)] bg-[var(--color-surface-overlay)] text-[var(--color-ink-secondary)] ' +
      'hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-ink-primary)]',
    ghost:
      'text-[var(--color-ink-muted)] hover:bg-[var(--color-surface-overlay)] hover:text-[var(--color-ink-primary)]',
    danger:
      'border border-[color-mix(in_srgb,var(--color-danger)_35%,transparent)] bg-[var(--color-danger-soft)] ' +
      'text-[var(--color-danger)] hover:bg-[color-mix(in_srgb,var(--color-danger)_18%,transparent)]',
  };

  return (
    <button className={cx(base, sizes[size], variants[variant], className)} {...rest}>
      {children}
    </button>
  );
};

// ---------------------------------------------------------------------------
// Badge
// ---------------------------------------------------------------------------
export type BadgeTone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info';

const BADGE_TONES: Record<BadgeTone, string> = {
  neutral:
    'border-[var(--color-line-default)] bg-[var(--color-surface-overlay)] text-[var(--color-ink-secondary)]',
  accent:
    'border-[color-mix(in_srgb,var(--color-accent)_35%,transparent)] bg-[var(--color-accent-soft)] text-[var(--color-accent-hover)]',
  success:
    'border-[color-mix(in_srgb,var(--color-success)_35%,transparent)] bg-[var(--color-success-soft)] text-[var(--color-success)]',
  warning:
    'border-[color-mix(in_srgb,var(--color-warning)_35%,transparent)] bg-[var(--color-warning-soft)] text-[var(--color-warning)]',
  danger:
    'border-[color-mix(in_srgb,var(--color-danger)_35%,transparent)] bg-[var(--color-danger-soft)] text-[var(--color-danger)]',
  info: 'border-[color-mix(in_srgb,var(--color-info)_35%,transparent)] bg-[var(--color-info-soft)] text-[var(--color-info)]',
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
      'inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-medium whitespace-nowrap',
      mono && 'font-[family-name:var(--font-mono)] tracking-tight',
      BADGE_TONES[tone],
      className,
    )}
  >
    {children}
  </span>
);

// ---------------------------------------------------------------------------
// Metric tile
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
    <Card className="p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[12px] font-medium text-[var(--color-ink-muted)]">{label}</span>
        {icon && <span className="text-[var(--color-ink-faint)]">{icon}</span>}
      </div>
      <div className="mt-2 flex items-baseline gap-1">
        <span className={cx('text-[26px] leading-none font-semibold tabular-nums', valueTone)}>
          {value}
        </span>
        {unit && <span className="text-[13px] text-[var(--color-ink-muted)]">{unit}</span>}
      </div>
      {hint && <p className="mt-1.5 text-[12px] leading-snug text-[var(--color-ink-faint)]">{hint}</p>}
    </Card>
  );
};

// ---------------------------------------------------------------------------
// Meter — a labelled proportion bar
// ---------------------------------------------------------------------------
export const Meter: React.FC<{
  label: string;
  value: number;
  max?: number;
  tone?: 'accent' | 'success' | 'warning' | 'danger';
  suffix?: string;
}> = ({ label, value, max = 100, tone = 'accent', suffix = '%' }) => {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const barTone = {
    accent: 'bg-[var(--color-accent)]',
    success: 'bg-[var(--color-success)]',
    warning: 'bg-[var(--color-warning)]',
    danger: 'bg-[var(--color-danger)]',
  }[tone];

  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between gap-2">
        <span className="text-[13px] text-[var(--color-ink-secondary)]">{label}</span>
        <span className="text-[13px] font-medium tabular-nums text-[var(--color-ink-primary)]">
          {value}
          {suffix}
        </span>
      </div>
      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-[var(--color-surface-overlay)]"
        role="meter"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label}
      >
        <div className={cx('h-full rounded-full transition-[width] duration-500', barTone)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Empty state — always states WHY something is empty
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
      compact ? 'gap-2 px-4 py-8' : 'gap-3 px-6 py-14',
    )}
  >
    {icon && <div className="text-[var(--color-ink-faint)]">{icon}</div>}
    <div>
      <p className="text-[14px] font-medium text-[var(--color-ink-secondary)]">{title}</p>
      {description && (
        <p className="mx-auto mt-1 max-w-md text-[13px] leading-relaxed text-[var(--color-ink-muted)]">
          {description}
        </p>
      )}
    </div>
    {action}
  </div>
);

// ---------------------------------------------------------------------------
// Skeleton loader
// ---------------------------------------------------------------------------
export const Skeleton: React.FC<{ className?: string }> = ({ className }) => (
  <div
    className={cx(
      'relative overflow-hidden rounded-md bg-[var(--color-surface-overlay)] progress-indeterminate',
      className,
    )}
    aria-hidden="true"
  />
);

// ---------------------------------------------------------------------------
// Inline error
// ---------------------------------------------------------------------------
export const ErrorNotice: React.FC<{
  title: string;
  detail?: string;
  onRetry?: () => void;
}> = ({ title, detail, onRetry }) => (
  <div className="flex items-start gap-3 rounded-lg border border-[color-mix(in_srgb,var(--color-danger)_30%,transparent)] bg-[var(--color-danger-soft)] px-4 py-3">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="mt-0.5 shrink-0 text-[var(--color-danger)]">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" />
      <path d="M12 7v6M12 16.5v.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
    <div className="min-w-0 flex-1">
      <p className="text-[13px] font-medium text-[var(--color-danger)]">{title}</p>
      {detail && <p className="mt-0.5 text-[12px] text-[var(--color-ink-secondary)]">{detail}</p>}
    </div>
    {onRetry && (
      <Button size="sm" variant="ghost" onClick={onRetry}>
        Retry
      </Button>
    )}
  </div>
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
      'inline-block h-1.5 w-1.5 shrink-0 rounded-full',
      online
        ? degraded
          ? 'bg-[var(--color-warning)]'
          : 'bg-[var(--color-success)]'
        : 'bg-[var(--color-danger)]',
    )}
  />
);

// ---------------------------------------------------------------------------
// Section heading
// ---------------------------------------------------------------------------
export const SectionTitle: React.FC<{
  children: React.ReactNode;
  hint?: string;
  actions?: React.ReactNode;
}> = ({ children, hint, actions }) => (
  <div className="mb-3 flex items-end justify-between gap-4">
    <div>
      <h2 className="text-[15px] font-semibold text-[var(--color-ink-primary)]">{children}</h2>
      {hint && <p className="mt-0.5 text-[13px] text-[var(--color-ink-muted)]">{hint}</p>}
    </div>
    {actions}
  </div>
);
