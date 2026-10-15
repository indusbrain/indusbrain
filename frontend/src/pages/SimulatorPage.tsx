import React, { useState } from 'react';
import Markdown from 'markdown-to-jsx';
import { api, ApiError } from '../lib/api';
import type { DashboardPayload, EvidenceStatement, SimulationAssessment } from '../lib/types';
import { PageBody, PageHeader } from '../components/AppShell';
import { Badge, Button, Card, CardHeader, cx, EmptyState, ErrorNotice } from '../components/ui/primitives';
import { IconAlert, IconClock, IconFlask, IconShield } from '../components/ui/icons';

const PRESET_SCENARIOS = [
  'Delay the scheduled maintenance outage by one week',
  'Increase discharge pressure to 380 PSI without resetting the relief valve',
  'Reduce the inspection frequency to cut costs',
  'Skip the scheduled calibration this quarter',
];

const EvidenceList: React.FC<{
  title: string;
  items: EvidenceStatement[];
  tone: 'neutral' | 'warning' | 'danger';
  icon: React.ReactNode;
  emptyText: string;
}> = ({ title, items, tone, icon, emptyText }) => (
  <div>
    <div className="mb-2 flex items-center gap-2">
      <span
        className={cx(
          tone === 'danger' && 'text-[var(--color-danger)]',
          tone === 'warning' && 'text-[var(--color-warning)]',
          tone === 'neutral' && 'text-[var(--color-ink-muted)]',
        )}
      >
        {icon}
      </span>
      <p className="eyebrow">{title}</p>
      {items.length > 0 && <Badge tone={tone === 'neutral' ? 'neutral' : tone}>{items.length}</Badge>}
    </div>
    {items.length === 0 ? (
      <p className="text-[12.5px] text-[var(--color-ink-muted)]">{emptyText}</p>
    ) : (
      <ul className="space-y-2">
        {items.map((item, index) => (
          <li
            key={index}
            className={cx(
              'border-l-2 py-1 pl-3',
              tone === 'danger'
                ? 'border-[var(--color-danger)]'
                : tone === 'warning'
                  ? 'border-[var(--color-warning)]'
                  : 'border-[var(--color-line-default)]',
            )}
          >
            <p className="text-[12.5px] leading-relaxed text-[var(--color-ink-secondary)]">
              {item.statement}
            </p>
            <p
              className="mt-1 truncate font-[family-name:var(--font-mono)] text-[11px] text-[var(--color-ink-muted)]"
              title={item.source}
            >
              {item.source}
            </p>
          </li>
        ))}
      </ul>
    )}
  </div>
);

export const SimulatorPage: React.FC<{ dashboard: DashboardPayload | null }> = ({ dashboard }) => {
  const [scenario, setScenario] = useState(PRESET_SCENARIOS[0]);
  const [assetTag, setAssetTag] = useState('SELECT ASSET');
  const [result, setResult] = useState<SimulationAssessment | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = async () => {
    if (!scenario.trim()) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.simulate(scenario, assetTag));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'The assessment failed.');
    } finally {
      setRunning(false);
    }
  };

  const assets = dashboard?.assets ?? [];

  return (
    <PageBody>
      <PageHeader
        title="Impact Assessment"
        description="Assess a proposed operational decision against what your documents actually say."
      />

      {/* States plainly what this tool does and does not do. It previously emitted
          invented figures such as "+8.5% production impact"; those are gone. */}
      <div className="mb-6 flex max-w-3xl items-start gap-3">
        <IconShield size={16} className="mt-0.5 shrink-0 text-[var(--color-info)]" />
        <p className="text-[13px] leading-relaxed text-[var(--color-ink-secondary)]">
          <span className="font-medium text-[var(--color-info)]">Evidence-based:</span> this
          assessment is built only from limits, warnings and open actions found in your indexed
          documents, each traceable to its source. It does not estimate percentages, risk
          multipliers or failure rates — if your documentation does not quantify an impact, it says
          so rather than supplying a number.
        </p>
      </div>

      <div className="grid min-w-0 gap-5 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <CardHeader title="Proposed decision" description="Describe the change to assess" />
          <div className="space-y-4 p-5">
            <div>
              <label htmlFor="sim-asset" className="mb-1.5 block text-[13px] font-medium text-[var(--color-ink-secondary)]">
                Target asset
              </label>
              <select
                id="sim-asset"
                value={assetTag}
                onChange={(event) => setAssetTag(event.target.value)}
                className="btn-glass w-full rounded-[var(--radius-control)] px-3 py-2 text-[13.5px] text-[var(--color-ink-primary)] focus:border-[var(--color-accent)]"
              >
                <option value="SELECT ASSET">No specific asset</option>
                {assets.map((asset) => (
                  <option key={asset.tag} value={asset.tag}>
                    {asset.tag} — {asset.category}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="sim-scenario" className="mb-1.5 block text-[13px] text-[var(--color-ink-secondary)]">
                What are you considering?
              </label>
              <textarea
                id="sim-scenario"
                rows={3}
                value={scenario}
                onChange={(event) => setScenario(event.target.value)}
                className="w-full resize-none rounded-[var(--radius-control)] border border-[var(--color-line-default)] bg-[var(--color-surface-overlay)] px-3 py-2 text-[13px] text-[var(--color-ink-primary)] placeholder:text-[var(--color-ink-muted)] focus:border-[var(--color-accent)]"
                placeholder="e.g. Defer the bearing replacement until the next planned outage"
              />
            </div>

            <div>
              <p className="eyebrow mb-2">
                Common decisions
              </p>
              <div className="space-y-1.5">
                {PRESET_SCENARIOS.map((preset) => (
                  <button
                    key={preset}
                    onClick={() => setScenario(preset)}
                    className={cx(
                      'w-full border-l-2 py-1.5 pl-3 text-left text-[13px] transition-colors',
                      scenario === preset
                        ? 'border-[var(--color-accent)] font-medium text-[var(--color-ink-primary)]'
                        : 'border-[var(--color-line-subtle)] text-[var(--color-ink-muted)] hover:border-[var(--color-line-default)] hover:text-[var(--color-ink-primary)]',
                    )}
                  >
                    {preset}
                  </button>
                ))}
              </div>
            </div>

            <Button
              variant="primary"
              className="w-full"
              onClick={runSimulation}
              disabled={running || !scenario.trim()}
            >
              <IconFlask size={15} />
              {running ? 'Assessing…' : 'Assess impact'}
            </Button>
          </div>
        </Card>

        <div className="min-w-0 space-y-5 lg:col-span-3">
          {error && <ErrorNotice title="Assessment failed" detail={error} onRetry={runSimulation} />}

          {!result && !error && (
            <Card className="h-full">
              <EmptyState
                icon={<IconFlask size={30} />}
                title={running ? 'Searching your documents…' : 'No assessment yet'}
                description={
                  running
                    ? 'Retrieving the limits, warnings and maintenance records relevant to this decision.'
                    : 'Describe a proposed change to see what your documents say about it.'
                }
              />
            </Card>
          )}

          {/* Honest refusal — no metrics, an explicit reason, and what to do next */}
          {result && !result.has_sufficient_evidence && (
            <Card>
              <div className="p-6">
                <div className="flex items-start gap-3">
                  <IconAlert size={20} className="mt-0.5 shrink-0 text-[var(--color-warning)]" />
                  <div>
                    <h2 className="text-[15px] font-semibold text-[var(--color-ink-primary)]">
                      {result.refusal_reason}
                    </h2>
                    {result.guidance && (
                      <p className="mt-1.5 text-[13.5px] leading-relaxed text-[var(--color-ink-secondary)]">
                        {result.guidance}
                      </p>
                    )}
                    <p className="mt-4 border-t border-[var(--color-line-subtle)] pt-3 text-[12px] text-[var(--color-ink-muted)]">
                      No engineering figures are shown because none could be derived from your
                      documents. This tool will not estimate an impact it cannot evidence.
                    </p>
                  </div>
                </div>
              </div>
            </Card>
          )}

          {result && result.has_sufficient_evidence && (
            <>
              <Card>
                <CardHeader
                  title="Assessment"
                  description={result.target_asset}
                  actions={
                    <Badge tone="success">
                      evidence {((result.evidence_strength ?? 0) * 100).toFixed(0)}%
                    </Badge>
                  }
                />
                <div className="p-5">
                  <div className="answer-prose text-[var(--color-ink-secondary)]">
                    <Markdown options={{ forceBlock: true }}>{result.assessment ?? ''}</Markdown>
                  </div>
                  <p className="mt-4 border-t border-[var(--color-line-subtle)] pt-3 font-[family-name:var(--font-mono)] text-[11.5px] text-[var(--color-ink-muted)]">
                    {result.engine}
                  </p>
                </div>
              </Card>

              <Card>
                <CardHeader
                  title="Supporting evidence"
                  description="Quoted directly from your indexed documents"
                />
                <div className="space-y-5 p-5">
                  <EvidenceList
                    title="Open actions affecting this decision"
                    items={result.open_actions}
                    tone="danger"
                    icon={<IconClock size={15} />}
                    emptyText="No incomplete work was recorded against this asset."
                  />
                  <EvidenceList
                    title="Safety warnings"
                    items={result.safety_warnings}
                    tone="warning"
                    icon={<IconAlert size={15} />}
                    emptyText="No warnings were found in the retrieved passages."
                  />
                  <EvidenceList
                    title="Applicable limits"
                    items={result.applicable_limits}
                    tone="neutral"
                    icon={<IconShield size={15} />}
                    emptyText="No numeric limits were found in the retrieved passages."
                  />
                </div>
              </Card>
            </>
          )}
        </div>
      </div>
    </PageBody>
  );
};
