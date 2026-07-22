import React, { useMemo } from 'react';
import { Link } from 'react-router-dom';
import type { DashboardPayload } from '../lib/types';
import { PageBody, PageHeader } from '../components/AppShell';
import {
  Badge,
  Button,
  Card,
  CardHeader,
  cx,
  EmptyState,
  Metric,
  Meter,
  Skeleton,
  StatusDot,
} from '../components/ui/primitives';
import { IconChart, IconRefresh, IconUpload } from '../components/ui/icons';

/**
 * Analytics — the "Knowledge DNA" view.
 *
 * This page is the real destination that the chat panel's old "View Core
 * Analytics" affordance implied but never had. Charts are plain SVG/CSS so there
 * is no charting dependency to break the build.
 */

const DonutGauge: React.FC<{ value: number; label: string; tone: string }> = ({ value, label, tone }) => {
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const dash = (Math.max(0, Math.min(100, value)) / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <svg width="132" height="132" viewBox="0 0 132 132" role="img" aria-label={`${label}: ${value}%`}>
        <circle cx="66" cy="66" r={radius} fill="none" stroke="var(--color-surface-overlay)" strokeWidth="11" />
        <circle
          cx="66"
          cy="66"
          r={radius}
          fill="none"
          stroke={tone}
          strokeWidth="11"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference}`}
          transform="rotate(-90 66 66)"
          style={{ transition: 'stroke-dasharray 0.7s cubic-bezier(0.22,1,0.36,1)' }}
        />
        <text
          x="66"
          y="62"
          textAnchor="middle"
          className="fill-[var(--color-ink-primary)]"
          style={{ fontSize: 26, fontWeight: 600 }}
        >
          {value}
        </text>
        <text
          x="66"
          y="80"
          textAnchor="middle"
          className="fill-[var(--color-ink-muted)]"
          style={{ fontSize: 11 }}
        >
          out of 100
        </text>
      </svg>
      <p className="mt-1 text-[13px] font-medium text-[var(--color-ink-secondary)]">{label}</p>
    </div>
  );
};

const BarRow: React.FC<{ label: string; value: number; max: number; tone: string; suffix?: string }> = ({
  label,
  value,
  max,
  tone,
  suffix = '',
}) => (
  <div className="flex items-center gap-3">
    <span className="w-[132px] shrink-0 truncate text-[12.5px] text-[var(--color-ink-secondary)]" title={label}>
      {label}
    </span>
    <div className="h-5 min-w-0 flex-1 overflow-hidden rounded bg-[var(--color-surface-overlay)]">
      <div
        className="h-full rounded transition-[width] duration-700"
        style={{ width: `${max > 0 ? (value / max) * 100 : 0}%`, background: tone }}
      />
    </div>
    <span className="w-11 shrink-0 text-right font-[family-name:var(--font-mono)] text-[12.5px] text-[var(--color-ink-primary)] tabular-nums">
      {value}
      {suffix}
    </span>
  </div>
);

export const AnalyticsPage: React.FC<{
  dashboard: DashboardPayload | null;
  loading: boolean;
  onRefresh: () => void;
}> = ({ dashboard, loading, onRefresh }) => {
  const documentBreakdown = useMemo(() => {
    if (!dashboard) return [];
    const counts = new Map<string, number>();
    dashboard.inventory.forEach((doc) => counts.set(doc.status, (counts.get(doc.status) ?? 0) + 1));
    return [...counts.entries()];
  }, [dashboard]);

  const topAssets = useMemo(
    () => (dashboard ? [...dashboard.assets].sort((a, b) => b.mentions - a.mentions).slice(0, 8) : []),
    [dashboard],
  );

  if (!dashboard) {
    return (
      <PageBody>
        <PageHeader title="Analytics" />
        <Skeleton className="h-96" />
      </PageBody>
    );
  }

  const { metrics, score_breakdown, infrastructure } = dashboard;

  if (dashboard.empty_states.no_documents) {
    return (
      <PageBody>
        <PageHeader title="Analytics" description="Knowledge coverage and corpus health." />
        <Card>
          <EmptyState
            icon={<IconChart size={30} />}
            title="Nothing to analyse yet"
            description="Analytics are computed from your indexed corpus. Upload documents to see coverage, asset distribution and knowledge health."
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

  const scoreColour =
    metrics.knowledge_score >= 70
      ? 'var(--color-success)'
      : metrics.knowledge_score >= 40
        ? 'var(--color-warning)'
        : 'var(--color-danger)';

  const maxMentions = Math.max(1, ...topAssets.map((a) => a.mentions));

  return (
    <PageBody>
      <PageHeader
        title="Analytics"
        description="Knowledge DNA — how completely your corpus documents your plant."
        actions={
          <Button variant="secondary" size="sm" onClick={onRefresh} disabled={loading}>
            <IconRefresh size={14} />
            {loading ? 'Refreshing…' : 'Refresh'}
          </Button>
        }
      />

      <div className="grid min-w-0 gap-5 lg:grid-cols-3">
        {/* Knowledge DNA gauge */}
        <Card className="lg:col-span-1">
          <CardHeader title="Knowledge health" description="Composite score" />
          <div className="flex flex-col items-center gap-5 p-5">
            <DonutGauge value={metrics.knowledge_score} label="Knowledge score" tone={scoreColour} />
            <div className="w-full space-y-2 border-t border-[var(--color-line-subtle)] pt-4 text-[13px]">
              <div className="flex justify-between">
                <span className="text-[var(--color-ink-muted)]">Asset completeness</span>
                <span className="font-medium tabular-nums">{score_breakdown.base_asset_completeness}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--color-ink-muted)]">Conflict penalty</span>
                <span className="font-medium tabular-nums text-[var(--color-danger)]">
                  −{score_breakdown.conflict_penalty}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--color-ink-muted)]">Failure penalty</span>
                <span className="font-medium tabular-nums text-[var(--color-warning)]">
                  −{score_breakdown.failure_penalty}
                </span>
              </div>
              <p className="border-t border-[var(--color-line-subtle)] pt-3 font-[family-name:var(--font-mono)] text-[11.5px] leading-relaxed text-[var(--color-ink-faint)]">
                {score_breakdown.formula}
              </p>
            </div>
          </div>
        </Card>

        {/* Coverage */}
        <Card className="lg:col-span-2">
          <CardHeader
            title="Corpus coverage by topic"
            description="Share of indexed passages mentioning each topic"
          />
          <div className="space-y-4 p-5">
            <Meter label="Maintenance records" value={metrics.maintenance_coverage} tone="accent" />
            <Meter label="Safety and compliance" value={metrics.safety_coverage} tone="success" />
            <Meter label="Procedures and SOPs" value={metrics.procedure_coverage} tone="warning" />
            <Meter label="Inspection and testing" value={metrics.inspection_coverage} tone="accent" />

            <div className="grid grid-cols-2 gap-3 border-t border-[var(--color-line-subtle)] pt-4 sm:grid-cols-4">
              <Metric label="Documents" value={metrics.total_documents} />
              <Metric label="Passages" value={metrics.total_chunks} />
              <Metric label="Assets" value={metrics.total_assets} />
              <Metric
                label="Gaps"
                value={metrics.documentation_gaps}
                tone={metrics.documentation_gaps > 0 ? 'warning' : 'success'}
              />
            </div>
          </div>
        </Card>
      </div>

      <div className="mt-5 grid min-w-0 gap-5 lg:grid-cols-2">
        {/* Most referenced assets */}
        <Card>
          <CardHeader title="Most referenced equipment" description="By mentions across the corpus" />
          <div className="space-y-2.5 p-5">
            {topAssets.length === 0 ? (
              <EmptyState compact title="No equipment tags extracted" />
            ) : (
              topAssets.map((asset) => (
                <BarRow
                  key={asset.tag}
                  label={asset.tag}
                  value={asset.mentions}
                  max={maxMentions}
                  tone={
                    asset.missing_coverage.length === 0
                      ? 'var(--color-success)'
                      : 'var(--color-accent)'
                  }
                />
              ))
            )}
          </div>
        </Card>

        {/* Pipeline + infrastructure */}
        <Card>
          <CardHeader title="Pipeline and services" description="Ingestion outcomes and backing systems" />
          <div className="space-y-5 p-5">
            <div>
              <p className="mb-2.5 text-[12px] font-semibold tracking-wide text-[var(--color-ink-faint)] uppercase">
                Ingestion outcomes
              </p>
              <div className="flex flex-wrap gap-2">
                {documentBreakdown.map(([status, count]) => (
                  <Badge
                    key={status}
                    tone={
                      status === 'EMBEDDED'
                        ? 'success'
                        : status === 'FAILED'
                          ? 'danger'
                          : status === 'PENDING'
                            ? 'warning'
                            : 'info'
                    }
                  >
                    {status.toLowerCase()}: {count}
                  </Badge>
                ))}
                {dashboard.metrics.duplicate_documents > 0 && (
                  <Badge tone="warning">duplicates: {dashboard.metrics.duplicate_documents}</Badge>
                )}
              </div>
            </div>

            <div className="border-t border-[var(--color-line-subtle)] pt-4">
              <p className="mb-2.5 text-[12px] font-semibold tracking-wide text-[var(--color-ink-faint)] uppercase">
                Backing services
              </p>
              <ul className="space-y-2">
                {[
                  ['PostgreSQL', infrastructure.postgresql, 'Document and chunk ledger'],
                  ['Neo4j', infrastructure.neo4j, 'Asset knowledge graph'],
                  ['ChromaDB', infrastructure.chromadb, 'Vector index'],
                  ['Ollama', infrastructure.ollama_qwen, 'Local language model'],
                ].map(([name, status, purpose]) => (
                  <li key={name as string} className="flex items-center gap-2.5">
                    <StatusDot online={status !== 'OFFLINE'} degraded={status === 'NO_MODELS'} />
                    <span className="w-[92px] shrink-0 text-[13px] text-[var(--color-ink-primary)]">
                      {name}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-[12.5px] text-[var(--color-ink-muted)]">
                      {purpose}
                    </span>
                    <span
                      className={cx(
                        'text-[12px] font-medium',
                        status === 'OFFLINE'
                          ? 'text-[var(--color-danger)]'
                          : status === 'NO_MODELS'
                            ? 'text-[var(--color-warning)]'
                            : 'text-[var(--color-success)]',
                      )}
                    >
                      {String(status).toLowerCase().replace('_', ' ')}
                    </span>
                  </li>
                ))}
              </ul>
              {infrastructure.ollama_models.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {infrastructure.ollama_models.map((model) => (
                    <Badge key={model} tone="neutral" mono>
                      {model}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Card>
      </div>
    </PageBody>
  );
};
