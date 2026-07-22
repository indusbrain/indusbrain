import React from 'react';
import { Link } from 'react-router-dom';
import type { DashboardPayload } from '../lib/types';
import { PageBody, PageHeader } from '../components/AppShell';
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  Metric,
  Meter,
  Skeleton,
} from '../components/ui/primitives';
import {
  IconAlert,
  IconChevron,
  IconDocs,
  IconGraph,
  IconRefresh,
  IconUpload,
} from '../components/ui/icons';

const STATUS_TONE = {
  EMBEDDED: 'success',
  PARSED: 'info',
  PENDING: 'warning',
  FAILED: 'danger',
} as const;

export const OverviewPage: React.FC<{
  dashboard: DashboardPayload | null;
  loading: boolean;
  onRefresh: () => void;
}> = ({ dashboard, loading, onRefresh }) => {
  if (!dashboard) {
    return (
      <PageBody>
        <PageHeader title="Overview" description="Loading knowledge base status…" />
        <div className="grid min-w-0 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-[112px]" />
          ))}
        </div>
        <Skeleton className="mt-4 h-64" />
      </PageBody>
    );
  }

  const { metrics, score_breakdown, conflicts, inventory, knowledge_gaps, empty_states } =
    dashboard;

  const scoreTone =
    metrics.knowledge_score >= 70 ? 'success' : metrics.knowledge_score >= 40 ? 'warning' : 'danger';

  if (empty_states.no_documents) {
    return (
      <PageBody>
        <PageHeader title="Overview" description="Your knowledge base is empty." />
        <Card>
          <EmptyState
            icon={<IconUpload size={30} />}
            title="No documents indexed yet"
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

  return (
    <PageBody>
      <PageHeader
        title="Overview"
        description="Live status of your industrial knowledge base."
        actions={
          <Button variant="secondary" size="sm" onClick={onRefresh} disabled={loading}>
            <IconRefresh size={14} />
            {loading ? 'Refreshing…' : 'Refresh'}
          </Button>
        }
      />

      {/* Unresolved contradictions — static, not animated. Severity is carried by
          colour, icon and wording rather than motion. */}
      {conflicts.length > 0 && (
        <Link
          to="/conflicts"
          className="mb-5 flex items-start gap-3 rounded-xl border border-[color-mix(in_srgb,var(--color-danger)_32%,transparent)] bg-[var(--color-danger-soft)] px-4 py-3.5 transition-colors hover:bg-[color-mix(in_srgb,var(--color-danger)_14%,transparent)]"
        >
          <IconAlert size={19} className="mt-0.5 shrink-0 text-[var(--color-danger)]" />
          <div className="min-w-0 flex-1">
            <p className="text-[14px] font-medium text-[var(--color-danger)]">
              {conflicts.length} unresolved contradiction{conflicts.length === 1 ? '' : 's'} between
              documents
            </p>
            <p className="mt-0.5 text-[13px] text-[var(--color-ink-secondary)]">
              {conflicts[0].conflict_statement}
            </p>
          </div>
          <IconChevron direction="right" size={16} className="mt-1 shrink-0 text-[var(--color-danger)]" />
        </Link>
      )}

      {/* Headline metrics */}
      <div className="grid min-w-0 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          label="Knowledge score"
          value={metrics.knowledge_score}
          unit="/ 100"
          tone={scoreTone}
          hint={score_breakdown.formula}
        />
        <Metric
          label="Documents indexed"
          value={metrics.total_documents}
          hint={`${metrics.total_chunks} searchable passages`}
          icon={<IconDocs size={16} />}
        />
        <Metric
          label="Assets tracked"
          value={metrics.total_assets}
          hint={`${metrics.documented_assets} fully documented`}
          icon={<IconGraph size={16} />}
        />
        <Metric
          label="Open conflicts"
          value={metrics.open_conflicts}
          tone={metrics.open_conflicts > 0 ? 'danger' : 'success'}
          hint={metrics.open_conflicts > 0 ? 'Requires engineering review' : 'No contradictions found'}
          icon={<IconAlert size={16} />}
        />
      </div>

      <div className="mt-5 grid min-w-0 gap-5 lg:grid-cols-3">
        {/* Score explanation */}
        <Card className="lg:col-span-2">
          <CardHeader
            title="How the knowledge score is calculated"
            description="Every input is a direct count from your data."
          />
          <div className="space-y-4 p-5">
            <p className="text-[13.5px] leading-relaxed text-[var(--color-ink-secondary)]">
              {score_breakdown.explanation}
            </p>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-lg border border-[var(--color-line-subtle)] bg-[var(--color-surface-overlay)] p-3">
                <p className="text-[12px] text-[var(--color-ink-muted)]">Asset completeness</p>
                <p className="mt-1 text-[19px] font-semibold tabular-nums text-[var(--color-ink-primary)]">
                  {score_breakdown.base_asset_completeness}%
                </p>
              </div>
              <div className="rounded-lg border border-[var(--color-line-subtle)] bg-[var(--color-surface-overlay)] p-3">
                <p className="text-[12px] text-[var(--color-ink-muted)]">Conflict penalty</p>
                <p className="mt-1 text-[19px] font-semibold tabular-nums text-[var(--color-danger)]">
                  −{score_breakdown.conflict_penalty}
                </p>
              </div>
              <div className="rounded-lg border border-[var(--color-line-subtle)] bg-[var(--color-surface-overlay)] p-3">
                <p className="text-[12px] text-[var(--color-ink-muted)]">Ingestion failures</p>
                <p className="mt-1 text-[19px] font-semibold tabular-nums text-[var(--color-warning)]">
                  −{score_breakdown.failure_penalty}
                </p>
              </div>
            </div>

            <div className="space-y-3 border-t border-[var(--color-line-subtle)] pt-4">
              <p className="text-[12px] font-semibold tracking-wide text-[var(--color-ink-faint)] uppercase">
                Corpus coverage — passages mentioning each topic
              </p>
              <Meter label="Maintenance records" value={metrics.maintenance_coverage} tone="accent" />
              <Meter label="Safety and compliance" value={metrics.safety_coverage} tone="success" />
              <Meter label="Procedures and SOPs" value={metrics.procedure_coverage} tone="warning" />
              <Meter label="Inspection and testing" value={metrics.inspection_coverage} tone="accent" />
            </div>
          </div>
        </Card>

        {/* Documentation gaps */}
        <Card>
          <CardHeader
            title="Documentation gaps"
            description={`${knowledge_gaps.length} found`}
            actions={
              <Link to="/knowledge">
                <Button variant="ghost" size="sm">
                  View all
                </Button>
              </Link>
            }
          />
          <div className="max-h-[420px] overflow-y-auto p-3">
            {knowledge_gaps.length === 0 ? (
              <EmptyState
                compact
                title="No gaps detected"
                description="Every tracked asset has maintenance, safety, procedure and inspection evidence."
              />
            ) : (
              <ul className="space-y-2">
                {knowledge_gaps.slice(0, 10).map((gap) => (
                  <li
                    key={gap.id}
                    className="rounded-lg border border-[var(--color-line-subtle)] bg-[var(--color-surface-overlay)] p-3"
                  >
                    <div className="flex items-center gap-2">
                      <Badge tone="accent" mono>
                        {gap.asset}
                      </Badge>
                      <Badge tone={gap.severity === 'HIGH' ? 'danger' : 'warning'}>
                        {gap.category}
                      </Badge>
                    </div>
                    <p className="mt-1.5 text-[12.5px] leading-relaxed text-[var(--color-ink-muted)]">
                      {gap.statement}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Card>
      </div>

      {/* Recent documents */}
      <Card className="mt-5">
        <CardHeader
          title="Recently indexed documents"
          description={`${inventory.length} in the knowledge base`}
          actions={
            <Link to="/documents">
              <Button variant="ghost" size="sm">
                Manage
              </Button>
            </Link>
          }
        />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-[13px]">
            <thead>
              <tr className="border-b border-[var(--color-line-subtle)] text-left text-[12px] text-[var(--color-ink-muted)]">
                <th className="px-5 py-2.5 font-medium">Document</th>
                <th className="px-5 py-2.5 font-medium">Status</th>
                <th className="px-5 py-2.5 text-right font-medium">Passages</th>
                <th className="px-5 py-2.5 text-right font-medium">Size</th>
              </tr>
            </thead>
            <tbody>
              {inventory.slice(0, 6).map((doc) => (
                <tr
                  key={doc.id}
                  className="border-b border-[var(--color-line-subtle)] last:border-0 hover:bg-[var(--color-surface-overlay)]"
                >
                  <td className="max-w-[320px] truncate px-5 py-2.5 font-[family-name:var(--font-mono)] text-[12.5px] text-[var(--color-ink-primary)]">
                    {doc.filename}
                  </td>
                  <td className="px-5 py-2.5">
                    <Badge tone={STATUS_TONE[doc.status] ?? 'neutral'}>{doc.status.toLowerCase()}</Badge>
                  </td>
                  <td className="px-5 py-2.5 text-right tabular-nums text-[var(--color-ink-secondary)]">
                    {doc.chunk_count}
                  </td>
                  <td className="px-5 py-2.5 text-right tabular-nums text-[var(--color-ink-muted)]">
                    {(doc.file_size / 1024).toFixed(0)} KB
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </PageBody>
  );
};
