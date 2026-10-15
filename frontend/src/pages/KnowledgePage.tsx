import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import type { AssetRecord, CoverageCategory, DashboardPayload } from '../lib/types';
import { PageBody, PageHeader } from '../components/AppShell';
import { Badge, Button, Card, cx, EmptyState, Skeleton } from '../components/ui/primitives';
import { IconCheck, IconChevron, IconClose, IconGraph, IconSearch, IconUpload } from '../components/ui/icons';

const COVERAGE_LABELS: Record<CoverageCategory, string> = {
  maintenance: 'Maintenance',
  safety: 'Safety',
  procedure: 'Procedure',
  inspection: 'Inspection',
};

const AssetRow: React.FC<{ asset: AssetRecord }> = ({ asset }) => {
  const [open, setOpen] = useState(false);
  const complete = asset.missing_coverage.length === 0;

  return (
    <li className="border-b border-[var(--color-line-subtle)] last:border-0">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-3 px-5 py-3 text-left transition-colors hover:bg-[var(--color-surface-overlay)]"
      >
        <IconChevron size={15} direction={open ? 'up' : 'down'} className="shrink-0 text-[var(--color-ink-muted)]" />
        <span className="w-[104px] shrink-0 font-[family-name:var(--font-mono)] text-[13px] font-medium text-[var(--color-accent-hover)]">
          {asset.tag}
        </span>
        <span className="hidden min-w-0 flex-1 truncate text-[13px] text-[var(--color-ink-secondary)] sm:block">
          {asset.category}
        </span>
        <span className="hidden text-[12.5px] text-[var(--color-ink-muted)] tabular-nums md:block">
          {asset.document_count} doc{asset.document_count === 1 ? '' : 's'}
        </span>
        <span className="ml-auto shrink-0">
          <Badge tone={complete ? 'success' : 'warning'}>
            {complete ? 'Documented' : `${asset.missing_coverage.length} gap${asset.missing_coverage.length === 1 ? '' : 's'}`}
          </Badge>
        </span>
      </button>

      {open && (
        <div className="animate-fade-in space-y-4 border-t border-[var(--color-line-subtle)] px-5 py-4 sm:pl-[52px]">
          <div>
            <p className="eyebrow mb-2">
              Evidence coverage
            </p>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {(Object.keys(COVERAGE_LABELS) as CoverageCategory[]).map((category) => {
                const present = asset.coverage[category];
                return (
                  <div
                    key={category}
                    className={cx(
                      'flex items-center gap-2 text-[13px]',
                      present ? 'font-medium text-[var(--color-success)]' : 'text-[var(--color-ink-muted)]',
                    )}
                  >
                    {present ? <IconCheck size={13} /> : <IconClose size={13} />}
                    {COVERAGE_LABELS[category]}
                  </div>
                );
              })}
            </div>
          </div>

          <div>
            <p className="eyebrow mb-2">
              Appears in {asset.documents.length} document{asset.documents.length === 1 ? '' : 's'} ·{' '}
              {asset.mentions} mention{asset.mentions === 1 ? '' : 's'}
            </p>
            <ul className="space-y-1">
              {asset.documents.map((filename) => (
                <li
                  key={filename}
                  className="truncate font-[family-name:var(--font-mono)] text-[12.5px] text-[var(--color-ink-secondary)]"
                >
                  {filename}
                </li>
              ))}
            </ul>
          </div>

          <Link to={`/ask?q=${encodeURIComponent(`What do the documents say about ${asset.tag}? Include its specifications, maintenance history and any safety requirements.`)}`}>
            <Button variant="secondary" size="sm">
              Ask about {asset.tag}
            </Button>
          </Link>
        </div>
      )}
    </li>
  );
};

export const KnowledgePage: React.FC<{ dashboard: DashboardPayload | null }> = ({ dashboard }) => {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<'all' | 'gaps' | 'documented'>('all');

  const filteredAssets = useMemo(() => {
    if (!dashboard) return [];
    const term = search.trim().toLowerCase();
    return dashboard.assets.filter((asset) => {
      const matchesSearch =
        !term ||
        asset.tag.toLowerCase().includes(term) ||
        asset.category.toLowerCase().includes(term) ||
        asset.documents.some((d) => d.toLowerCase().includes(term));
      const matchesFilter =
        filter === 'all' ||
        (filter === 'gaps' && asset.missing_coverage.length > 0) ||
        (filter === 'documented' && asset.missing_coverage.length === 0);
      return matchesSearch && matchesFilter;
    });
  }, [dashboard, search, filter]);

  if (!dashboard) {
    return (
      <PageBody>
        <PageHeader title="Knowledge Explorer" />
        <Skeleton className="h-96" />
      </PageBody>
    );
  }

  return (
    <PageBody>
      <PageHeader
        title="Knowledge Explorer"
        description="Equipment discovered in your documents, and how completely each one is documented."
      />

      {dashboard.assets.length === 0 ? (
        <Card>
          <EmptyState
            icon={<IconGraph size={30} />}
            title="No equipment tags found yet"
            description="IndusBrain recognises tags such as PUMP-101 or VALVE-220. Upload manuals or maintenance logs containing equipment references to populate the knowledge graph."
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
      ) : (
        <>
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <IconSearch
                size={15}
                className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-[var(--color-ink-muted)]"
              />
              <label htmlFor="asset-search" className="sr-only">
                Search assets
              </label>
              <input
                id="asset-search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search by tag, category or document…"
                className="btn-glass w-full rounded-[var(--radius-control)] py-2 pr-3 pl-9 text-[13px] text-[var(--color-ink-primary)] placeholder:text-[var(--color-ink-muted)] focus:border-[var(--color-accent)]"
              />
            </div>
            <div
              className="btn-glass flex rounded-[var(--radius-control)] p-0.5"
              role="radiogroup"
              aria-label="Filter assets"
            >
              {(
                [
                  ['all', `All ${dashboard.assets.length}`],
                  ['gaps', 'With gaps'],
                  ['documented', 'Complete'],
                ] as const
              ).map(([value, label]) => (
                <button
                  key={value}
                  role="radio"
                  aria-checked={filter === value}
                  onClick={() => setFilter(value)}
                  className={cx(
                    'rounded-[var(--radius-control)] px-3 py-1.5 text-[12.5px] whitespace-nowrap transition-colors',
                    filter === value
                      ? 'bg-[var(--color-ink-primary)] font-medium text-[var(--color-surface-raised)]'
                      : 'text-[var(--color-ink-muted)] hover:text-[var(--color-ink-primary)]',
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <Card>
            {filteredAssets.length === 0 ? (
              <EmptyState
                compact
                title="No assets match your filters"
                description="Try a different search term or filter."
              />
            ) : (
              <ul>
                {filteredAssets.map((asset) => (
                  <AssetRow key={asset.tag} asset={asset} />
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </PageBody>
  );
};
