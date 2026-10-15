import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError } from '../lib/api';
import type { ConflictFinding, DashboardPayload } from '../lib/types';
import { PageBody, PageHeader } from '../components/AppShell';
import { FaultNotice } from '../components/ui/FaultNotice';
import { Badge, Button, Card, EmptyState, ErrorNotice, Skeleton } from '../components/ui/primitives';
import { IconChat, IconCheck, IconRefresh, IconShield } from '../components/ui/icons';

/**
 * Builds the question sent to the chat when an engineer asks about a conflict.
 *
 * It carries every fact the assistant needs — asset tag, parameter, both values
 * with units, and both source filenames — so the engineer never copies anything
 * by hand.
 *
 * Deliberately worded WITHOUT the words "conflict" or "contradiction". Those
 * route the supervisor to the deterministic conflict engine, which would simply
 * restate the list the user is already looking at. Phrasing it as a question
 * about the limit routes it to the retrieval agents instead, which is what
 * surfaces the governing preconditions and any outstanding work.
 */
function buildConflictQuestion(finding: ConflictFinding): string {
  return (
    `${finding.asset_tag}: ${finding.parameter.toLowerCase()} is recorded as ` +
    `${finding.low_value} ${finding.unit} in "${finding.low_source}" but ` +
    `${finding.high_value} ${finding.unit} in "${finding.high_source}". ` +
    `Which limit currently applies, what preconditions govern the higher value, ` +
    `and is any required work still outstanding for this asset?`
  );
}

const ConflictCard: React.FC<{ finding: ConflictFinding }> = ({ finding }) => (
  <Card className="overflow-hidden">
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-[var(--color-line-subtle)] px-5 py-3.5">
      <Badge tone={finding.severity === 'CRITICAL' ? 'danger' : 'warning'}>
        {finding.severity.toLowerCase()}
      </Badge>
      <Badge tone="accent" mono>
        {finding.asset_tag}
      </Badge>
      <span className="text-[13.5px] font-medium text-[var(--color-ink-primary)]">
        {finding.parameter}
      </span>
      <span className="ml-auto font-[family-name:var(--font-mono)] text-[12.5px] text-[var(--color-ink-muted)]">
        Δ {finding.variance} {finding.unit}
      </span>
    </div>

    <div className="p-5">
      <p className="text-[13.5px] leading-relaxed text-[var(--color-ink-secondary)]">
        {finding.conflict_statement}
      </p>

      {/* Side-by-side comparison of the two conflicting statements */}
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {[
          { label: 'Lower value', value: finding.low_value, source: finding.low_source, context: finding.low_context, controlling: true },
          { label: 'Higher value', value: finding.high_value, source: finding.high_source, context: finding.high_context, controlling: false },
        ].map((side) => (
          <div
            key={side.label}
            // Not a box: a hairline and a coloured value carry the distinction.
            className={
              side.controlling
                ? 'border-t-2 border-[var(--color-success)] pt-3'
                : 'border-t-2 border-[var(--color-line-default)] pt-3'
            }
          >
            <div className="flex items-center justify-between gap-2">
              <span className="eyebrow">{side.label}</span>
              {side.controlling && (
                <Badge tone="success" title="The conservative limit that applies until an engineer resolves the conflict">
                  controlling
                </Badge>
              )}
            </div>
            <p className="mt-1 font-[family-name:var(--font-mono)] text-[21px] font-semibold text-[var(--color-ink-primary)] tabular-nums">
              {side.value} <span className="text-[14px] text-[var(--color-ink-muted)]">{finding.unit}</span>
            </p>
            <p
              className="mt-1.5 truncate font-[family-name:var(--font-mono)] text-[11.5px] text-[var(--color-ink-muted)]"
              title={side.source}
            >
              {side.source}
            </p>
            <blockquote className="mt-2 border-l-2 border-[var(--color-line-default)] pl-2.5 text-[12px] leading-relaxed text-[var(--color-ink-muted)]">
              {side.context}
            </blockquote>
          </div>
        ))}
      </div>

      <div className="mt-5 flex items-start gap-2.5">
        <IconShield size={16} className="mt-0.5 shrink-0 text-[var(--color-info)]" />
        <div>
          <p className="eyebrow !text-[var(--color-info)]">Recommended action</p>
          <p className="mt-0.5 text-[13px] leading-relaxed text-[var(--color-ink-secondary)]">
            {finding.recommended_action}
          </p>
        </div>
      </div>

      <div className="mt-4">
        <Link to={`/ask?q=${encodeURIComponent(buildConflictQuestion(finding))}`}>
          <Button variant="primary" size="sm">
            <IconChat size={14} />
            Ask IndusBrain about this conflict
          </Button>
        </Link>
        <p className="mt-1.5 text-[11.5px] text-[var(--color-ink-muted)]">
          Opens a new conversation with the asset, both values and both source documents
          already included.
        </p>
      </div>
    </div>
  </Card>
);

export const ConflictsPage: React.FC<{
  dashboard: DashboardPayload | null;
  onDataChanged: () => void;
}> = ({ dashboard, onDataChanged }) => {
  const [rescanning, setRescanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scannedCount, setScannedCount] = useState<number | null>(null);

  const rescan = async () => {
    setRescanning(true);
    setError(null);
    try {
      const result = await api.scanConflicts();
      setScannedCount(result.chunks_scanned);
      onDataChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'The conflict scan failed.');
    } finally {
      setRescanning(false);
    }
  };

  if (!dashboard) {
    return (
      <PageBody>
        <PageHeader title="Conflicts" />
        <Skeleton className="h-64" />
      </PageBody>
    );
  }

  const conflicts = dashboard.conflicts;

  return (
    <PageBody>
      <PageHeader
        title="Conflict detection"
        description="Contradictions found between two different documents describing the same equipment parameter."
        actions={
          <Button variant="secondary" size="sm" onClick={rescan} disabled={rescanning}>
            <IconRefresh size={14} />
            {rescanning ? 'Scanning…' : 'Rescan corpus'}
          </Button>
        }
      />

      {error && (
        <div className="mb-4">
          <ErrorNotice title="Scan failed" detail={error} onRetry={rescan} />
        </div>
      )}

      {scannedCount !== null && !error && (
        <p className="mb-4 text-[13px] text-[var(--color-ink-muted)]">
          Scanned {scannedCount} passages across {dashboard.metrics.total_documents} documents.
        </p>
      )}

      {conflicts.length === 0 ? (
        <Card>
          <EmptyState
            icon={<IconCheck size={30} />}
            title="No contradictions found"
            description={
              dashboard.empty_states.conflicts_reason ??
              'No two documents state materially different values for the same parameter on the same asset.'
            }
          />
        </Card>
      ) : (
        <>
          <div className="mb-5">
            <FaultNotice
              kicker="Needs review"
              title={`${conflicts.length} contradiction${conflicts.length === 1 ? '' : 's'} require review`}
              detail="Until each is formally resolved, apply the lower (more conservative) value as the controlling limit."
              quiet
            />
          </div>

          <div className="space-y-4">
            {conflicts.map((finding, index) => (
              <ConflictCard key={`${finding.asset_tag}-${finding.unit}-${index}`} finding={finding} />
            ))}
          </div>
        </>
      )}
    </PageBody>
  );
};
