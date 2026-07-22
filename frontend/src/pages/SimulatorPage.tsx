import React, { useState } from 'react';
import { api, ApiError } from '../lib/api';
import type { DashboardPayload, SimulationResult } from '../lib/types';
import { PageBody, PageHeader } from '../components/AppShell';
import { Badge, Button, Card, CardHeader, cx, EmptyState, ErrorNotice } from '../components/ui/primitives';
import { IconAlert, IconFlask, IconShield } from '../components/ui/icons';

const PRESET_SCENARIOS = [
  'Delay the scheduled maintenance outage by one week',
  'Increase operating pressure above the rated limit',
  'Reduce inspection frequency to cut costs',
  'Skip the scheduled calibration this quarter',
];

export const SimulatorPage: React.FC<{ dashboard: DashboardPayload | null }> = ({ dashboard }) => {
  const [scenario, setScenario] = useState(PRESET_SCENARIOS[0]);
  const [assetTag, setAssetTag] = useState('SELECT ASSET');
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = async () => {
    if (!scenario.trim()) return;
    setRunning(true);
    setError(null);
    try {
      setResult(await api.simulate(scenario, assetTag));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'The simulation failed.');
    } finally {
      setRunning(false);
    }
  };

  const assets = dashboard?.assets ?? [];

  return (
    <PageBody>
      <PageHeader
        title="Impact Simulator"
        description="Model the operational consequences of a maintenance or operating decision before you commit to it."
      />

      {/* This tool is rule-based, and says so. Presenting heuristics as predictive
          modelling would be the same category of dishonesty we removed elsewhere. */}
      <div className="mb-5 flex items-start gap-3 rounded-xl border border-[color-mix(in_srgb,var(--color-info)_26%,transparent)] bg-[var(--color-info-soft)] px-4 py-3">
        <IconShield size={16} className="mt-0.5 shrink-0 text-[var(--color-info)]" />
        <p className="text-[13px] leading-relaxed text-[var(--color-ink-secondary)]">
          <span className="font-medium text-[var(--color-info)]">How this works:</span> the simulator
          applies engineering heuristics to the wording of your scenario. It is a structured
          what-if aid for discussion — not a physics model or a prediction derived from your
          documents. Always validate against the equipment manual and your plant's safety case.
        </p>
      </div>

      <div className="grid min-w-0 gap-5 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <CardHeader title="Scenario" description="Describe the decision to evaluate" />
          <div className="space-y-4 p-5">
            <div>
              <label htmlFor="sim-asset" className="mb-1.5 block text-[13px] text-[var(--color-ink-secondary)]">
                Target asset
              </label>
              <select
                id="sim-asset"
                value={assetTag}
                onChange={(event) => setAssetTag(event.target.value)}
                className="w-full rounded-lg border border-[var(--color-line-default)] bg-[var(--color-surface-overlay)] px-3 py-2 text-[13px] text-[var(--color-ink-primary)] focus:border-[var(--color-accent)]"
              >
                <option value="SELECT ASSET">No specific asset</option>
                {assets.map((asset) => (
                  <option key={asset.tag} value={asset.tag}>
                    {asset.tag} — {asset.category}
                  </option>
                ))}
              </select>
              {assets.length === 0 && (
                <p className="mt-1.5 text-[12px] text-[var(--color-ink-faint)]">
                  No assets indexed yet — the simulation will run against a generic asset.
                </p>
              )}
            </div>

            <div>
              <label htmlFor="sim-scenario" className="mb-1.5 block text-[13px] text-[var(--color-ink-secondary)]">
                Scenario description
              </label>
              <textarea
                id="sim-scenario"
                rows={3}
                value={scenario}
                onChange={(event) => setScenario(event.target.value)}
                className="w-full resize-none rounded-lg border border-[var(--color-line-default)] bg-[var(--color-surface-overlay)] px-3 py-2 text-[13px] text-[var(--color-ink-primary)] placeholder:text-[var(--color-ink-faint)] focus:border-[var(--color-accent)]"
                placeholder="e.g. Defer the bearing replacement until the next planned outage"
              />
            </div>

            <div>
              <p className="mb-2 text-[12px] font-semibold tracking-wide text-[var(--color-ink-faint)] uppercase">
                Common scenarios
              </p>
              <div className="space-y-1.5">
                {PRESET_SCENARIOS.map((preset) => (
                  <button
                    key={preset}
                    onClick={() => setScenario(preset)}
                    className={cx(
                      'w-full rounded-lg border px-3 py-2 text-left text-[12.5px] transition-colors',
                      scenario === preset
                        ? 'border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-ink-primary)]'
                        : 'border-[var(--color-line-subtle)] bg-[var(--color-surface-overlay)] text-[var(--color-ink-muted)] hover:text-[var(--color-ink-primary)]',
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
              {running ? 'Running…' : 'Run simulation'}
            </Button>
          </div>
        </Card>

        <div className="space-y-5 lg:col-span-3">
          {error && <ErrorNotice title="Simulation failed" detail={error} onRetry={runSimulation} />}

          {!result && !error ? (
            <Card className="h-full">
              <EmptyState
                icon={<IconFlask size={30} />}
                title="No simulation run yet"
                description="Choose an asset and describe a scenario to see modelled production, risk, compliance and reliability impacts."
              />
            </Card>
          ) : result ? (
            <>
              <Card>
                <CardHeader
                  title="Modelled impact"
                  description={result.target_asset}
                  actions={<Badge tone="accent" mono>{result.target_asset}</Badge>}
                />
                <div className="grid gap-4 p-5 sm:grid-cols-2">
                  {[
                    {
                      label: 'Production output',
                      value: `${result.metrics.production_impact_pct >= 0 ? '+' : ''}${result.metrics.production_impact_pct}%`,
                      tone: result.metrics.production_impact_pct >= 0 ? 'success' : 'danger',
                      bar: Math.min(100, Math.abs(result.metrics.production_impact_pct) * 5),
                      hint: 'Short-term change in throughput',
                    },
                    {
                      label: 'Failure risk multiplier',
                      value: `${result.metrics.risk_multiplier_factor}×`,
                      tone: result.metrics.risk_multiplier_factor > 2 ? 'danger' : 'warning',
                      bar: Math.min(100, (result.metrics.risk_multiplier_factor / 4) * 100),
                      hint: 'Relative increase in likelihood of failure',
                    },
                    {
                      label: 'Compliance exposure',
                      value: `${result.metrics.compliance_vulnerability_index}/100`,
                      tone: result.metrics.compliance_vulnerability_index > 70 ? 'danger' : 'warning',
                      bar: result.metrics.compliance_vulnerability_index,
                      hint: 'Regulatory risk introduced by this decision',
                    },
                    {
                      label: 'Reliability degradation',
                      value: `${result.metrics.reliability_degradation_pct}%`,
                      tone: result.metrics.reliability_degradation_pct > 40 ? 'danger' : 'warning',
                      bar: result.metrics.reliability_degradation_pct,
                      hint: 'Accelerated component wear',
                    },
                  ].map((metric) => (
                    <div
                      key={metric.label}
                      className="rounded-lg border border-[var(--color-line-subtle)] bg-[var(--color-surface-overlay)] p-4"
                    >
                      <p className="text-[12.5px] text-[var(--color-ink-muted)]">{metric.label}</p>
                      <p
                        className={cx(
                          'mt-1 text-[24px] leading-none font-semibold tabular-nums',
                          metric.tone === 'success' && 'text-[var(--color-success)]',
                          metric.tone === 'warning' && 'text-[var(--color-warning)]',
                          metric.tone === 'danger' && 'text-[var(--color-danger)]',
                        )}
                      >
                        {metric.value}
                      </p>
                      <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-[var(--color-surface-base)]">
                        <div
                          className={cx(
                            'h-full rounded-full transition-[width] duration-700',
                            metric.tone === 'success' && 'bg-[var(--color-success)]',
                            metric.tone === 'warning' && 'bg-[var(--color-warning)]',
                            metric.tone === 'danger' && 'bg-[var(--color-danger)]',
                          )}
                          style={{ width: `${metric.bar}%` }}
                        />
                      </div>
                      <p className="mt-1.5 text-[11.5px] text-[var(--color-ink-faint)]">{metric.hint}</p>
                    </div>
                  ))}
                </div>
              </Card>

              <Card>
                <CardHeader title="Engineering assessment" icon={<IconAlert size={16} />} />
                <div className="p-5">
                  <p className="text-[13.5px] leading-relaxed text-[var(--color-ink-secondary)]">
                    {result.mitigation_directive}
                  </p>
                  <p className="mt-4 border-t border-[var(--color-line-subtle)] pt-3 text-[12px] text-[var(--color-ink-faint)]">
                    Scenario evaluated: “{result.scenario}”
                  </p>
                </div>
              </Card>
            </>
          ) : null}
        </div>
      </div>
    </PageBody>
  );
};
