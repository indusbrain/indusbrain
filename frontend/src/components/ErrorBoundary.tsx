import React from 'react';

/**
 * Catches render-time exceptions so one bad component cannot blank the entire
 * application.
 *
 * This is exactly the failure the old chat panel produced: it read a field the
 * API no longer returned, called .map() on undefined, and React unmounted the
 * whole tree — presenting as a blank page with no explanation.
 */
export class ErrorBoundary extends React.Component<
  { children: React.ReactNode; label?: string },
  { error: Error | null }
> {
  state: { error: Error | null } = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[IndusBrain] Render error:', error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div className="flex min-h-[60vh] items-center justify-center p-6">
        <div className="max-w-lg rounded-xl border border-[color-mix(in_srgb,var(--color-danger)_30%,transparent)] bg-[var(--color-danger-soft)] p-6">
          <h2 className="text-[16px] font-semibold text-[var(--color-danger)]">
            This section failed to render
          </h2>
          <p className="mt-2 text-[13.5px] leading-relaxed text-[var(--color-ink-secondary)]">
            {this.props.label ? `The ${this.props.label} view` : 'A component'} hit an unexpected
            error. The rest of the application is still usable.
          </p>
          <pre className="mt-3 max-h-40 overflow-auto rounded-lg border border-[var(--color-line-subtle)] bg-[var(--color-surface-base)] p-3 font-[family-name:var(--font-mono)] text-[11.5px] text-[var(--color-ink-muted)]">
            {this.state.error.message}
          </pre>
          <button
            onClick={() => this.setState({ error: null })}
            className="mt-4 rounded-lg bg-[var(--color-accent)] px-3.5 py-2 text-[13px] font-medium text-white hover:bg-[var(--color-accent-hover)]"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }
}
