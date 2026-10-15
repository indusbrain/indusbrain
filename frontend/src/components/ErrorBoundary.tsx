import React from 'react';
import { FaultNotice } from './ui/FaultNotice';

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
        <div className="w-full max-w-xl">
          <FaultNotice
            kicker="Section crashed"
            title="This section failed to render"
            detail={`${this.props.label ? `The ${this.props.label} view` : 'A component'} hit an unexpected error. The rest of the application is still usable.`}
            onRetry={() => this.setState({ error: null })}
            retryLabel="Try again"
          >
            <pre className="mt-3 max-h-40 overflow-auto font-[family-name:var(--font-mono)] text-[11.5px] text-[var(--color-ink-muted)]">
              {this.state.error.message}
            </pre>
          </FaultNotice>
        </div>
      </div>
    );
  }
}
