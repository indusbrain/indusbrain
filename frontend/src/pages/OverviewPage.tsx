import React from 'react';
import { Link } from 'react-router-dom';
import type { AssetRecord, DashboardPayload, InventoryDocument } from '../lib/types';
import { PageBody, PageHeader } from '../components/AppShell';
import {
  Badge,
  Button,
  Card,
  cx,
  EmptyState,
  Meter,
  Skeleton,
} from '../components/ui/primitives';
import { IconArrowUpRight, IconRefresh, IconUpload } from '../components/ui/icons';
import { CountUp, Reveal, RevealItem } from '../components/motion/Motion';
import { Gauge } from '../components/viz/Gauge';

/**
 * Sheet 01 — Overview.
 *
 * An asymmetric bento: one hero reading (the knowledge score, drawn as an
 * instrument dial) and supporting tiles of decreasing weight. Every number is
 * a direct value from the dashboard payload; derived sentences (strongest /
 * weakest coverage) are computed from those values, never written by hand.
 */

const STATUS_TONE = {
  EMBEDDED: 'success',
  PARSED: 'info',
  PENDING: 'warning',
  FAILED: 'danger',
} as const;

const STATUS_FILL: Record<InventoryDocument['status'], string> = {
  EMBEDDED: 'bg-[var(--color-pipe)]',
  PARSED: 'bg-[var(--color-info)]',
  PENDING: 'bg-[var(--color-amber)]',
  FAILED: 'bg-[var(--color-danger)]',
};

// ---------------------------------------------------------------------------
// Tile: a bento cell with a title row and an optional "open sheet" arrow
// ---------------------------------------------------------------------------
const Tile: React.FC<{
  title: string;
  to?: string;
  linkLabel?: string;
  className?: string;
  bodyClassName?: string;
  children: React.ReactNode;
}> = ({ title, to, linkLabel, className, bodyClassName, children }) => (
  <Card as="section" className={cx('flex h-full flex-col', className)}>
    <div className="flex items-center justify-between gap-3 px-5 pt-4">
      <h2 className="text-[15px] font-semibold text-[var(--color-ink-primary)]">{title}</h2>
      {to && (
        <Link
          to={to}
          aria-label={linkLabel ?? `Open ${title}`}
          className="pressable -mr-1.5 inline-flex h-8 w-8 items-center justify-center rounded-full text-[var(--color-ink-muted)] hover:bg-[var(--color-surface-overlay)] hover:text-[var(--color-ink-primary)]"
        >
          <IconArrowUpRight size={16} />
        </Link>
      )}
    </div>
    <div className={cx('flex-1 px-5 pt-3 pb-5', bodyClassName)}>{children}</div>
  </Card>
);

/** Small caption above a value. Plain text — never boxed. */
const FieldLabel: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className }) => (
  <p className={cx('eyebrow', className)}>{children}</p>
);

// ---------------------------------------------------------------------------
// Asset tag strip: one cell per tracked asset, filled when fully documented
// ---------------------------------------------------------------------------
const AssetStrip: React.FC<{ assets: AssetRecord[] }> = ({ assets }) => (
  <ul className="flex flex-wrap gap-1" aria-label="Asset documentation status">
    {assets.map((asset, i) => {
      const documented = asset.status === 'Documented';
      return (
        <li
          key={asset.tag}
          title={`${asset.tag} — ${documented ? 'fully documented' : `missing ${asset.missing_coverage.join(', ')}`}`}
          className={cx(
            'animate-fade-rise h-5 w-3.5 rounded-[2px] border',
            documented
              ? 'border-[var(--color-pipe)] bg-[var(--color-pipe)]'
              : 'border-[var(--color-line-default)] bg-transparent',
          )}
          style={{ animationDelay: `${0.3 + i * 0.03}s` }}
        >
          <span className="sr-only">
            {asset.tag}: {documented ? 'documented' : 'has gaps'}
          </span>
        </li>
      );
    })}
  </ul>
);

export const OverviewPage: React.FC<{
  dashboard: DashboardPayload | null;
  loading: boolean;
  onRefresh: () => void;
}> = ({ dashboard, loading, onRefresh }) => {
  if (!dashboard) {
    return (
      <PageBody>
        <PageHeader title="Overview" description="Reading the knowledge base…" />
        <div className="grid min-w-0 gap-4 xl:grid-cols-12">
          <Skeleton className="h-[340px] xl:col-span-7" />
          <div className="grid gap-4 xl:col-span-5">
            <Skeleton className="h-[160px]" />
            <Skeleton className="h-[160px]" />
          </div>
        </div>
        <Skeleton className="mt-4 h-64" />
      </PageBody>
    );
  }

  const { metrics, score_breakdown, conflicts, inventory, knowledge_gaps, empty_states, assets } =
    dashboard;

  if (empty_states.no_documents) {
    return (
      <PageBody>
        <PageHeader title="Overview" description="Your knowledge base is empty." />
        <Card>
          <EmptyState
            icon={<IconUpload size={30} />}
            title="A blank sheet"
            description="Upload equipment manuals, SOPs, maintenance logs or safety standards. IndusBrain will extract the text, build a knowledge graph of your assets, and make everything searchable."
            action={
              <Link to="/documents">
                <Button variant="primary">
                  <IconUpload size={15} />
                  Upload documents
                </Button>
              </Link>
            }
          />
        </Card>
      </PageBody>
    );
  }

  const score = metrics.knowledge_score;
  // Arc fill uses the bright chart colour; the numeral uses the text-safe one.
  const scoreBand =
    score >= 70
      ? { verdict: 'Healthy', arc: 'var(--color-pipe)', text: 'var(--color-success)' }
      : score >= 40
        ? { verdict: 'Needs attention', arc: 'var(--color-amber)', text: 'var(--color-warning)' }
        : { verdict: 'Critical', arc: 'var(--color-danger)', text: 'var(--color-danger)' };

  const coverage = [
    { label: 'Maintenance records', short: 'maintenance', value: metrics.maintenance_coverage, tone: 'warning' as const },
    { label: 'Safety and compliance', short: 'safety', value: metrics.safety_coverage, tone: 'warning' as const },
    { label: 'Procedures and SOPs', short: 'procedures', value: metrics.procedure_coverage, tone: 'warning' as const },
    { label: 'Inspection and testing', short: 'inspection', value: metrics.inspection_coverage, tone: 'warning' as const },
  ];
  const sortedCoverage = [...coverage].sort((a, b) => b.value - a.value);
  const strongest = sortedCoverage[0];
  const weakest = sortedCoverage[sortedCoverage.length - 1];

  const statusCounts = inventory.reduce<Record<string, number>>((acc, doc) => {
    acc[doc.status] = (acc[doc.status] ?? 0) + 1;
    return acc;
  }, {});
  const maxChunks = Math.max(1, ...inventory.map((d) => d.chunk_count));

  return (
    <PageBody>
      <PageHeader
        title="Overview"
        description="Live status of your plant's documented knowledge — what is covered, what contradicts, and what is missing."
        actions={
          <Button variant="secondary" size="sm" onClick={onRefresh} disabled={loading}>
            <IconRefresh size={14} className={loading ? 'animate-spin' : undefined} />
            {loading ? 'Re-reading…' : 'Refresh'}
          </Button>
        }
      />

      <Reveal className="grid min-w-0 gap-4 xl:grid-cols-12">
        {/* ── Hero: the knowledge score as an instrument dial ─────────────── */}
        <RevealItem className="min-w-0 xl:col-span-7 xl:row-span-2">
          <Card as="section" className="h-full p-6 sm:p-8">
            <div className="grid h-full gap-6 sm:grid-cols-[minmax(0,1fr)_minmax(180px,240px)] sm:items-center">
              <div className="flex h-full min-w-0 flex-col">
                <FieldLabel>Knowledge score · {scoreBand.verdict}</FieldLabel>
                <p className="mt-3 flex items-baseline gap-2">
                  <span
                    className="font-display text-[length:var(--text-hero-figure)] leading-[0.85] font-semibold tracking-[-0.05em] tabular-nums"
                    style={{ color: scoreBand.text }}
                  >
                    <CountUp value={score} />
                  </span>
                  <span className="font-[family-name:var(--font-mono)] text-[14px] text-[var(--color-ink-muted)]">/ 100</span>
                </p>
                <p className="mt-4 max-w-md text-[14px] leading-relaxed text-[var(--color-ink-secondary)]">
                  {score_breakdown.explanation}
                </p>

                {/* The score as an equation, so the number is never a black box */}
                <div className="mt-auto pt-6">
                  <FieldLabel className="mb-2">How it adds up</FieldLabel>
                  <p className="flex flex-wrap items-baseline gap-x-2.5 gap-y-1 text-[14px] tabular-nums">
                    <span className="font-semibold text-[var(--color-ink-primary)]">
                      {score_breakdown.base_asset_completeness}
                      <span className="ml-1 text-[12.5px] font-normal text-[var(--color-ink-muted)]">completeness</span>
                    </span>
                    <span className="text-[var(--color-ink-muted)]">−</span>
                    <span className="font-semibold text-[var(--color-danger)]">
                      {score_breakdown.conflict_penalty}
                      <span className="ml-1 text-[12.5px] font-normal opacity-80">conflicts</span>
                    </span>
                    <span className="text-[var(--color-ink-muted)]">−</span>
                    <span className="font-semibold text-[var(--color-warning)]">
                      {score_breakdown.failure_penalty}
                      <span className="ml-1 text-[12.5px] font-normal opacity-80">failures</span>
                    </span>
                    <span className="text-[var(--color-ink-muted)]">=</span>
                    <span className="text-[17px] font-semibold text-[var(--color-ink-primary)]">{score}</span>
                  </p>
                </div>
              </div>

              <Gauge
                value={score}
                label={`Knowledge score ${score} out of 100`}
                color={scoreBand.arc}
                className="mx-auto w-full max-w-[240px]"
              />
            </div>
          </Card>
        </RevealItem>

        {/* ── Conflicts: the one tile allowed to shout ─────────────────────── */}
        <RevealItem className="min-w-0 xl:col-span-5">
          {conflicts.length > 0 ? (
            <Link
              to="/conflicts"
              className="fault fault--quiet sheet-hover group relative flex h-full flex-col overflow-hidden p-5"
            >
              <div className="flex items-start justify-between gap-3">
                <FieldLabel className="!text-[var(--color-danger)]">Unresolved contradictions</FieldLabel>
                <IconArrowUpRight
                  size={17}
                  className="text-[var(--color-danger)] transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                />
              </div>
              <p className="mt-2 font-display text-[length:var(--text-figure)] leading-none font-semibold text-[var(--color-danger)] tabular-nums">
                {conflicts.length}
              </p>
              <p className="mt-3 line-clamp-3 text-[13.5px] leading-relaxed text-[var(--color-ink-primary)]">
                {conflicts[0].conflict_statement}
              </p>
              <p className="mt-auto pt-3 text-[12.5px] font-medium text-[var(--color-danger)]">
                Requires engineering review →
              </p>
            </Link>
          ) : (
            <Tile title="Contradictions" to="/conflicts">
              <p className="font-display text-[length:var(--text-figure)] leading-none font-semibold text-[var(--color-success)]">0</p>
              <p className="mt-2 text-[13.5px] text-[var(--color-ink-muted)]">
                {empty_states.conflicts_reason ?? 'No documents disagree with each other.'}
              </p>
            </Tile>
          )}
        </RevealItem>

        {/* ── Documents + assets, side by side ─────────────────────────────── */}
        <RevealItem className="min-w-0 xl:col-span-5">
          <div className="grid h-full gap-4 sm:grid-cols-2">
            <Tile title="Documents" to="/documents" linkLabel="Open documents">
              <p className="font-display text-[length:var(--text-figure)] leading-none font-semibold tabular-nums">
                <CountUp value={metrics.total_documents} />
              </p>
              <p className="mt-1.5 text-[12.5px] text-[var(--color-ink-muted)]">
                {metrics.total_chunks} searchable passages
              </p>
              {/* Status stack */}
              <div className="mt-4 flex h-2 overflow-hidden rounded-full bg-[var(--color-surface-overlay)]">
                {(Object.keys(STATUS_FILL) as InventoryDocument['status'][]).map((status) =>
                  statusCounts[status] ? (
                    <span
                      key={status}
                      className={cx('animate-extend-x h-full', STATUS_FILL[status])}
                      style={{ width: `${(statusCounts[status] / inventory.length) * 100}%` }}
                      title={`${statusCounts[status]} ${status.toLowerCase()}`}
                    />
                  ) : null,
                )}
              </div>
              <p className="mt-2 font-[family-name:var(--font-mono)] text-[11px] text-[var(--color-ink-muted)]">
                {Object.entries(statusCounts)
                  .map(([status, n]) => `${n} ${status.toLowerCase()}`)
                  .join(' · ')}
              </p>
            </Tile>

            <Tile title="Assets" to="/knowledge" linkLabel="Open knowledge explorer">
              <p className="flex items-baseline gap-1.5">
                <span className="font-display text-[length:var(--text-figure)] leading-none font-semibold tabular-nums">
                  <CountUp value={metrics.documented_assets} />
                </span>
                <span className="font-[family-name:var(--font-mono)] text-[13px] text-[var(--color-ink-muted)]">
                  / {metrics.total_assets}
                </span>
              </p>
              <p className="mt-1.5 mb-4 text-[12.5px] text-[var(--color-ink-muted)]">fully documented</p>
              {assets.length > 0 ? (
                <AssetStrip assets={assets} />
              ) : (
                <p className="text-[12.5px] text-[var(--color-ink-muted)]">No equipment tags recognised yet.</p>
              )}
            </Tile>
          </div>
        </RevealItem>

        {/* ── Coverage bars ────────────────────────────────────────────────── */}
        <RevealItem className="min-w-0 xl:col-span-5">
          <Tile title="Corpus coverage" to="/analytics" linkLabel="Open analytics">
            <p className="mb-4 text-[12.5px] text-[var(--color-ink-muted)]">Share of passages mentioning each topic.</p>
            <div className="space-y-3.5">
              {coverage.map((c) => (
                <Meter key={c.label} label={c.label} value={c.value} tone={c.tone} />
              ))}
            </div>
            <p className="mt-5 border-t border-dashed border-[var(--color-line-default)] pt-3 text-[13px] text-[var(--color-ink-secondary)]">
              Strongest on <strong className="font-semibold text-[var(--color-ink-primary)]">{strongest.short}</strong>,
              thinnest on <strong className="font-semibold text-[var(--color-ink-primary)]">{weakest.short}</strong>.
            </p>
          </Tile>
        </RevealItem>

        {/* ── Gaps as a punch list ─────────────────────────────────────────── */}
        <RevealItem className="min-w-0 xl:col-span-7">
          <Tile
            title={`Documentation gaps · ${knowledge_gaps.length}`}
            to="/knowledge"
            linkLabel="View all gaps"
            bodyClassName="!px-0 !pb-2"
          >
            {knowledge_gaps.length === 0 ? (
              <EmptyState
                compact
                title="No gaps detected"
                description="Every tracked asset has maintenance, safety, procedure and inspection evidence."
              />
            ) : (
              <ol className="max-h-[360px] overflow-y-auto">
                {knowledge_gaps.slice(0, 10).map((gap, i) => (
                  <li
                    key={gap.id}
                    className="grid grid-cols-[2.25rem_minmax(0,1fr)] gap-x-2 border-t border-[var(--color-line-subtle)] px-5 py-3 transition-colors hover:bg-[var(--color-surface-overlay)]"
                  >
                    <span className="pt-0.5 font-[family-name:var(--font-mono)] text-[11px] text-[var(--color-ink-muted)] tabular-nums">
                      {String(i + 1).padStart(2, '0')}
                    </span>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <Badge tone="accent" mono>
                          {gap.asset}
                        </Badge>
                        <Badge tone={gap.severity === 'HIGH' ? 'danger' : 'warning'}>{gap.category}</Badge>
                      </div>
                      <p className="mt-1 text-[13px] leading-relaxed text-[var(--color-ink-muted)]">{gap.statement}</p>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </Tile>
        </RevealItem>

        {/* ── Recent documents ─────────────────────────────────────────────── */}
        <RevealItem className="min-w-0 xl:col-span-12">
          <Tile
            title={`Recently indexed · ${inventory.length} on file`}
            to="/documents"
            linkLabel="Manage documents"
            bodyClassName="!px-0 !pb-0"
          >
            <div className="overflow-x-auto">
              <table className="w-full min-w-[620px] text-[13px]">
                <thead>
                  <tr className="border-b border-[var(--color-line-default)] text-left">
                    {['Document', 'Status', 'Passages', 'Size'].map((h, i) => (
                      <th
                        key={h}
                        className={cx(
                          'eyebrow px-5 py-2',
                          i >= 2 && 'text-right',
                        )}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {inventory.slice(0, 6).map((doc) => (
                    <tr
                      key={doc.id}
                      className="border-b border-[var(--color-line-subtle)] transition-colors last:border-0 hover:bg-[var(--color-surface-overlay)]"
                    >
                      <td className="max-w-[360px] truncate px-5 py-3 font-[family-name:var(--font-mono)] text-[12.5px] text-[var(--color-ink-primary)]">
                        {doc.filename}
                      </td>
                      <td className="px-5 py-3">
                        <Badge tone={STATUS_TONE[doc.status] ?? 'neutral'}>{doc.status.toLowerCase()}</Badge>
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex items-center justify-end gap-2.5">
                          <span className="hidden h-1.5 w-20 overflow-hidden rounded-full bg-[var(--color-surface-overlay)] sm:block">
                            <span
                              className="animate-extend-x block h-full bg-[var(--color-amber)]"
                              style={{ width: `${(doc.chunk_count / maxChunks) * 100}%` }}
                            />
                          </span>
                          <span className="w-8 text-right font-[family-name:var(--font-mono)] tabular-nums text-[var(--color-ink-secondary)]">
                            {doc.chunk_count}
                          </span>
                        </div>
                      </td>
                      <td className="px-5 py-3 text-right font-[family-name:var(--font-mono)] text-[12px] tabular-nums text-[var(--color-ink-muted)]">
                        {(doc.file_size / 1024).toFixed(0)} KB
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Tile>
        </RevealItem>
      </Reveal>
    </PageBody>
  );
};
