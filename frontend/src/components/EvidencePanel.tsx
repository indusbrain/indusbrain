import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import type {
  Citation,
  ConfidenceBand,
  ConfidenceMetadata,
  OrganizationalMemory,
  RetrievalOrigin,
  TraceStep,
} from '../lib/types';
import { Badge, cx, EmptyState, Meter } from './ui/primitives';
import { IconChart, IconClock, IconGraph, IconRoute, IconShield } from './ui/icons';

// ---------------------------------------------------------------------------
// Shared confidence presentation
// ---------------------------------------------------------------------------
export const BAND_TONE: Record<ConfidenceBand, 'success' | 'warning' | 'danger' | 'neutral'> = {
  HIGH: 'success',
  MODERATE: 'warning',
  LOW: 'danger',
  NO_EVIDENCE: 'neutral',
  NOT_APPLICABLE: 'neutral',
};

export const BAND_LABEL: Record<ConfidenceBand, string> = {
  HIGH: 'Strong evidence',
  MODERATE: 'Partial evidence',
  LOW: 'Weak evidence',
  NO_EVIDENCE: 'No evidence',
  NOT_APPLICABLE: 'Not applicable',
};

const ORIGIN_PRESENTATION: Record<RetrievalOrigin, { label: string; tone: 'success' | 'info' | 'accent' | 'neutral'; title: string }> = {
  HYBRID_GRAPH_VECTOR_VERIFIED: {
    label: 'Graph + vector',
    tone: 'success',
    title: 'Found independently by both the vector index and the knowledge graph — the strongest evidence available.',
  },
  VECTOR_PROXIMITY_MATRIX: {
    label: 'Vector',
    tone: 'info',
    title: 'Found by semantic similarity search in ChromaDB.',
  },
  GRAPH_TOPOLOGY_WALK: {
    label: 'Graph',
    tone: 'accent',
    title: 'Found by walking asset relationships in the Neo4j knowledge graph.',
  },
  UNKNOWN: { label: 'Unknown', tone: 'neutral', title: 'Retrieval source not recorded.' },
};

export const ConfidenceReadout: React.FC<{
  score: number;
  band: ConfidenceBand;
  explanation: string;
  compact?: boolean;
}> = ({ score, band, explanation, compact = false }) => {
  const tone = BAND_TONE[band];
  const barTone = tone === 'neutral' ? 'accent' : tone;

  return (
    <div className={compact ? '' : 'space-y-2'}>
      <div className="flex items-center gap-2">
        <span className="text-[13px] text-[var(--color-ink-muted)]">Evidence strength</span>
        <Badge tone={tone}>{BAND_LABEL[band]}</Badge>
        <span className="ml-auto text-[15px] font-semibold tabular-nums text-[var(--color-ink-primary)]">
          {score.toFixed(0)}%
        </span>
      </div>
      {!compact && (
        <>
          <Meter label="" value={score} tone={barTone as 'accent'} suffix="%" />
          <p className="text-[12.5px] leading-relaxed text-[var(--color-ink-muted)]">{explanation}</p>
        </>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------------
type TabKey = 'sources' | 'confidence' | 'memory' | 'trace';

const TABS: Array<{ key: TabKey; label: string; icon: React.FC<{ size?: number; className?: string }> }> = [
  { key: 'sources', label: 'Sources', icon: IconShield },
  { key: 'confidence', label: 'Confidence', icon: IconChart },
  { key: 'memory', label: 'History', icon: IconClock },
  { key: 'trace', label: 'Decision replay', icon: IconRoute },
];

export const EvidencePanel: React.FC<{
  citations: Citation[];
  confidence: ConfidenceMetadata;
  memory: OrganizationalMemory;
  trace: TraceStep[];
  engine: string;
  notice: string | null;
}> = ({ citations, confidence, memory, trace, engine, notice }) => {
  const [tab, setTab] = useState<TabKey>('sources');

  const counts: Record<TabKey, number> = {
    sources: citations.length,
    confidence: 0,
    memory: memory.past_actions.length,
    trace: trace.length,
  };

  return (
    <div className="mt-3 overflow-hidden rounded-lg border border-[var(--color-line-subtle)] bg-[var(--color-surface-base)]">
      {/* Tab bar */}
      <div
        className="flex gap-0.5 overflow-x-auto border-b border-[var(--color-line-subtle)] p-1"
        role="tablist"
        aria-label="Answer evidence"
      >
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={cx(
              'flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[12.5px] transition-colors',
              tab === key
                ? 'bg-[var(--color-surface-overlay)] font-medium text-[var(--color-ink-primary)]'
                : 'text-[var(--color-ink-muted)] hover:text-[var(--color-ink-secondary)]',
            )}
          >
            <Icon size={14} />
            {label}
            {counts[key] > 0 && (
              <span className="text-[11px] tabular-nums text-[var(--color-ink-faint)]">
                {counts[key]}
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="p-4">
        {/* ------------------------------------------------ Sources */}
        {tab === 'sources' && (
          citations.length === 0 ? (
            <EmptyState
              compact
              title="No sources were cited"
              description="Nothing in the indexed documents matched this question, so no citations exist. This is an honest gap, not an error."
            />
          ) : (
            <ol className="space-y-2.5">
              {citations.map((citation, index) => {
                const origin = ORIGIN_PRESENTATION[citation.origin] ?? ORIGIN_PRESENTATION.UNKNOWN;
                return (
                  <li
                    key={`${citation.filename}-${citation.chunk_index}-${index}`}
                    className="rounded-lg border border-[var(--color-line-subtle)] bg-[var(--color-surface-raised)] p-3"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-[var(--color-surface-overlay)] text-[11px] font-semibold text-[var(--color-ink-muted)] tabular-nums">
                        {index + 1}
                      </span>
                      <span
                        className="min-w-0 flex-1 truncate font-[family-name:var(--font-mono)] text-[12.5px] text-[var(--color-ink-primary)]"
                        title={citation.filename}
                      >
                        {citation.filename}
                      </span>
                      <Badge tone={origin.tone} title={origin.title}>
                        {origin.label}
                      </Badge>
                      <Badge tone="neutral" mono title="Cross-encoder relevance score for this question">
                        {citation.relevance.toFixed(3)}
                      </Badge>
                    </div>
                    <blockquote className="mt-2 border-l-2 border-[var(--color-line-default)] pl-3 text-[12.5px] leading-relaxed whitespace-pre-wrap text-[var(--color-ink-secondary)]">
                      {citation.excerpt}
                    </blockquote>
                  </li>
                );
              })}
            </ol>
          )
        )}

        {/* ------------------------------------------------ Confidence */}
        {tab === 'confidence' && (
          <div className="space-y-4">
            <ConfidenceReadout
              score={confidence.score}
              band={confidence.band}
              explanation={confidence.explanation}
            />

            <div className="rounded-lg border border-[var(--color-line-subtle)] bg-[var(--color-surface-raised)] p-3">
              <p className="mb-2.5 text-[12px] font-semibold tracking-wide text-[var(--color-ink-faint)] uppercase">
                How this was measured
              </p>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-[12.5px]">
                {[
                  ['Best passage match', confidence.top_relevance.toFixed(4), 'Cross-encoder score of the single best passage (0–1).'],
                  ['Average match', confidence.mean_relevance.toFixed(4), 'Mean score across all passages used.'],
                  ['Distinct sources', String(confidence.distinct_sources), 'Number of separate documents supporting the answer.'],
                  ['Candidates considered', String(confidence.candidates_considered), 'Passages retrieved before reranking.'],
                  ['From vector index', String(confidence.vector_candidates), 'Retrieved by semantic similarity.'],
                  ['From knowledge graph', String(confidence.graph_candidates), 'Retrieved by asset relationship walk.'],
                ].map(([label, value, hint]) => (
                  <div key={label} title={hint}>
                    <dt className="text-[var(--color-ink-muted)]">{label}</dt>
                    <dd className="font-[family-name:var(--font-mono)] text-[var(--color-ink-primary)] tabular-nums">
                      {value}
                    </dd>
                  </div>
                ))}
              </dl>

              <div className="mt-3 flex items-center gap-2 border-t border-[var(--color-line-subtle)] pt-3">
                <IconGraph size={14} className="text-[var(--color-ink-muted)]" />
                <span className="text-[12.5px] text-[var(--color-ink-muted)]">Graph corroboration</span>
                <Badge tone={confidence.graph_verified ? 'success' : 'neutral'} className="ml-auto">
                  {confidence.graph_verified ? 'Confirmed by graph' : 'Vector only'}
                </Badge>
              </div>
            </div>

            <p className="text-[12px] leading-relaxed text-[var(--color-ink-faint)]">
              This score measures how well the retrieved evidence supports an answer. It is not a
              claim that the answer is correct, and it is capped at 95% — always confirm against the
              cited source before acting.
            </p>

            <Link
              to="/analytics"
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-[var(--color-line-default)] bg-[var(--color-surface-overlay)] px-3.5 py-2 text-[13px] font-medium text-[var(--color-ink-secondary)] transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-ink-primary)]"
            >
              <IconChart size={14} />
              Open full analytics
            </Link>
          </div>
        )}

        {/* ------------------------------------------------ Organizational memory */}
        {tab === 'memory' && (
          !memory.repair_history_found ? (
            <EmptyState
              compact
              title="No maintenance history found"
              description={memory.empty_reason ?? 'No past maintenance events appear in the retrieved passages.'}
            />
          ) : (
            <>
              <p className="mb-3 text-[12px] text-[var(--color-ink-faint)]">
                Quoted directly from your documents. Dates and work orders appear only where the
                source actually records them.
              </p>
              <ol className="relative space-y-3 border-l border-[var(--color-line-default)] pl-4">
                {memory.past_actions.map((event, index) => (
                  <li key={index} className="relative">
                    <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full bg-[var(--color-accent)] ring-2 ring-[var(--color-surface-base)]" />
                    <div className="flex flex-wrap items-center gap-1.5">
                      {event.date_known ? (
                        <Badge tone="neutral" mono>{event.date}</Badge>
                      ) : (
                        <Badge tone="neutral" title="This document does not record a date for this event">
                          date not recorded
                        </Badge>
                      )}
                      {event.asset && <Badge tone="accent" mono>{event.asset}</Badge>}
                      {event.work_order && <Badge tone="info" mono>{event.work_order}</Badge>}
                    </div>
                    <p className="mt-1.5 text-[12.5px] leading-relaxed text-[var(--color-ink-secondary)]">
                      {event.action}
                    </p>
                    <p
                      className="mt-1 truncate font-[family-name:var(--font-mono)] text-[11px] text-[var(--color-ink-faint)]"
                      title={event.source}
                    >
                      {event.source}
                    </p>
                  </li>
                ))}
              </ol>
            </>
          )
        )}

        {/* ------------------------------------------------ Decision replay */}
        {tab === 'trace' && (
          trace.length === 0 ? (
            <EmptyState compact title="No execution trace" description="The reasoning pipeline was not invoked for this message." />
          ) : (
            <>
              <p className="mb-3 text-[12px] text-[var(--color-ink-faint)]">
                Recorded by each node as it executed — not reconstructed afterwards.
              </p>
              <ol className="relative space-y-3.5 border-l border-[var(--color-line-default)] pl-4">
                {trace.map((step) => {
                  const tone =
                    step.status === 'COMPLETED'
                      ? 'success'
                      : step.status === 'REFUSED'
                        ? 'danger'
                        : 'warning';
                  return (
                    <li key={`${step.step}-${step.node}`} className="relative">
                      <span
                        className={cx(
                          'absolute -left-[21px] top-1.5 h-2 w-2 rounded-full ring-2 ring-[var(--color-surface-base)]',
                          tone === 'success' && 'bg-[var(--color-success)]',
                          tone === 'warning' && 'bg-[var(--color-warning)]',
                          tone === 'danger' && 'bg-[var(--color-danger)]',
                        )}
                      />
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[11px] text-[var(--color-ink-faint)] tabular-nums">
                          Step {step.step}
                        </span>
                        <span className="text-[13px] font-medium text-[var(--color-ink-primary)]">
                          {step.title}
                        </span>
                        <Badge tone={tone}>{step.status.replace('_', ' ').toLowerCase()}</Badge>
                      </div>
                      <p className="mt-1 text-[12.5px] leading-relaxed text-[var(--color-ink-secondary)]">
                        {step.detail}
                      </p>
                      {step.metrics && Object.keys(step.metrics).length > 0 && (
                        <div className="mt-1.5 flex flex-wrap gap-1">
                          {Object.entries(step.metrics)
                            .filter(([, v]) => typeof v !== 'object')
                            .map(([key, value]) => (
                              <Badge key={key} tone="neutral" mono>
                                {key.replace(/_/g, ' ')}: {String(value)}
                              </Badge>
                            ))}
                        </div>
                      )}
                    </li>
                  );
                })}
              </ol>
            </>
          )
        )}
      </div>

      {/* Engine footer — always visible so the operator knows what produced the answer */}
      <div className="flex flex-wrap items-center gap-2 border-t border-[var(--color-line-subtle)] bg-[var(--color-surface-raised)] px-4 py-2.5">
        <span className="text-[11.5px] text-[var(--color-ink-faint)]">Answered by</span>
        <span className="font-[family-name:var(--font-mono)] text-[11.5px] text-[var(--color-ink-secondary)]">
          {engine}
        </span>
        {notice && (
          <span className="ml-auto text-[11.5px] text-[var(--color-warning)]">{notice}</span>
        )}
      </div>
    </div>
  );
};
