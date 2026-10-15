import React from 'react';
import { cx } from './ui/primitives';
import { IconChart, IconGraph, IconRoute, IconSearch, IconShield, IconCompose } from './ui/icons';

/**
 * Pipeline progress shown while an answer is being produced.
 *
 * The stage names come from the SERVER's `status` events, so the labels track
 * what the pipeline is actually doing rather than being a decorative loop.
 *
 * This replaces a single static line that sat unchanged for 40-90 seconds during
 * local model inference, which made the app look frozen.
 */

export type PipelineStage =
  | 'supervisor'
  | 'agent'
  | 'retrieving'
  | 'graph'
  | 'ranking'
  | 'reasoning';

// Mirrors the real multi-agent pipeline: the supervisor classifies the question,
// dispatches a specialist, which retrieves from both stores, ranks the evidence,
// then generates a grounded answer.
const STAGES: Array<{ id: PipelineStage; label: string; icon: React.FC<{ size?: number; className?: string }> }> = [
  { id: 'supervisor', label: 'Classifying', icon: IconRoute },
  { id: 'agent', label: 'Dispatching agent', icon: IconShield },
  { id: 'retrieving', label: 'Searching documents', icon: IconSearch },
  { id: 'graph', label: 'Knowledge graph', icon: IconGraph },
  { id: 'ranking', label: 'Ranking evidence', icon: IconChart },
  { id: 'reasoning', label: 'Composing answer', icon: IconCompose },
];

export const ThinkingIndicator: React.FC<{
  stage: PipelineStage;
  message: string;
  elapsedSeconds: number;
}> = ({ stage, message, elapsedSeconds }) => {
  const activeIndex = Math.max(0, STAGES.findIndex((s) => s.id === stage));

  return (
    <div
      className="py-1"
      role="status"
      aria-live="polite"
    >
      {/* Current activity */}
      <div className="flex items-center gap-2.5">
        <span className="flex items-center gap-1" aria-hidden="true">
          <span className="think-dot" />
          <span className="think-dot" />
          <span className="think-dot" />
        </span>
        <span key={message} className="stage-label text-[13.5px] text-[var(--color-ink-secondary)]">
          {message}
        </span>
        {elapsedSeconds >= 3 && (
          <span className="ml-auto shrink-0 font-[family-name:var(--font-mono)] text-[11.5px] text-[var(--color-ink-muted)] tabular-nums">
            {elapsedSeconds}s
          </span>
        )}
      </div>

      {/* Stage track — shows how far through the pipeline the request is */}
      <ol className="mt-3 flex flex-wrap items-center gap-x-1.5 gap-y-2">
        {STAGES.map((entry, index) => {
          const done = index < activeIndex;
          const active = index === activeIndex;
          const Icon = entry.icon;
          return (
            <li key={entry.id} className="flex items-center gap-1.5">
              <span
                className={cx(
                  'flex items-center gap-1.5 text-[12.5px] transition-colors duration-300',
                  active && 'font-medium text-[var(--color-accent)]',
                  done && 'text-[var(--color-success)]',
                  !active && !done && 'text-[var(--color-ink-muted)]',
                )}
              >
                <Icon size={12} />
                {entry.label}
              </span>
              {index < STAGES.length - 1 && (
                <span
                  className={cx(
                    'h-px w-3 transition-colors duration-300',
                    done ? 'bg-[var(--color-success)]' : 'bg-[var(--color-line-subtle)]',
                  )}
                  aria-hidden="true"
                />
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
};
