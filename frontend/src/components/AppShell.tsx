import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import type { DashboardPayload, PermissionId, RoleId } from '../lib/types';
import { useRole } from '../lib/RoleContext';
import { cx, StatusDot } from './ui/primitives';
import {
  IconAlert,
  IconChart,
  IconChat,
  IconDocs,
  IconFlask,
  IconGauge,
  IconGraph,
  IconMenu,
} from './ui/icons';

interface NavEntry {
  to: string;
  label: string;
  icon: React.FC<{ size?: number; className?: string }>;
  badge?: number;
  permission?: PermissionId;
}

/**
 * Role switcher.
 *
 * Labelled as role simulation, not sign-in. The backend enforces permissions,
 * but it does not verify identity — presenting this as authentication would
 * imply a security guarantee the system does not provide.
 */
const RoleSwitcher: React.FC = () => {
  const { role, setRole, roles, authNotice } = useRole();
  const activeDefinition = roles.find((r) => r.id === role);

  return (
    <div className="border-t border-[var(--color-line-subtle)] px-4 py-3.5">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-[11px] font-semibold tracking-wide text-[var(--color-ink-faint)] uppercase">
          Active role
        </p>
        {authNotice && (
          <span
            title={authNotice}
            className="cursor-help text-[10px] text-[var(--color-warning)]"
          >
            demo mode
          </span>
        )}
      </div>

      <div
        className="flex rounded-lg border border-[var(--color-line-default)] bg-[var(--color-surface-overlay)] p-0.5"
        role="radiogroup"
        aria-label="Active role"
      >
        {(['engineer', 'manager'] as RoleId[]).map((candidate) => (
          <button
            key={candidate}
            role="radio"
            aria-checked={role === candidate}
            onClick={() => setRole(candidate)}
            className={cx(
              'flex-1 rounded-md px-2 py-1.5 text-[12px] capitalize transition-colors',
              role === candidate
                ? 'bg-[var(--color-accent)] font-medium text-white'
                : 'text-[var(--color-ink-muted)] hover:text-[var(--color-ink-primary)]',
            )}
          >
            {candidate}
          </button>
        ))}
      </div>

      {activeDefinition && (
        <p className="mt-2 text-[11.5px] leading-snug text-[var(--color-ink-faint)]">
          {activeDefinition.description}
        </p>
      )}
    </div>
  );
};

export const AppShell: React.FC<{
  dashboard: DashboardPayload | null;
  connectionError: string | null;
  children: React.ReactNode;
}> = ({ dashboard, connectionError, children }) => {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const { can } = useRole();

  // The drawer is closed by the nav links themselves (see closeMobileNav below)
  // rather than by an effect watching the pathname. Setting state synchronously
  // inside an effect triggers a second render pass on every navigation.
  const closeMobileNav = () => setMobileNavOpen(false);

  const openConflicts = dashboard?.metrics.open_conflicts ?? 0;

  const primaryNav: NavEntry[] = [
    { to: '/', label: 'Overview', icon: IconGauge },
    { to: '/ask', label: 'Ask IndusBrain', icon: IconChat },
    { to: '/knowledge', label: 'Knowledge Explorer', icon: IconGraph },
    { to: '/conflicts', label: 'Conflicts', icon: IconAlert, badge: openConflicts },
  ];

  // Documents is the only corpus-mutating area, so it is gated on the upload
  // permission. Everything else is available to both roles: an engineer
  // diagnosing a fault must be able to see conflicts and coverage gaps.
  const secondaryNav: NavEntry[] = [
    { to: '/analytics', label: 'Analytics', icon: IconChart },
    { to: '/simulator', label: 'Impact Simulator', icon: IconFlask },
    { to: '/documents', label: 'Documents', icon: IconDocs, permission: 'upload_documents' },
  ];

  const services = dashboard
    ? [
        { name: 'PostgreSQL', status: dashboard.infrastructure.postgresql },
        { name: 'Neo4j', status: dashboard.infrastructure.neo4j },
        { name: 'ChromaDB', status: dashboard.infrastructure.chromadb },
        { name: 'Ollama', status: dashboard.infrastructure.ollama_qwen },
      ]
    : [];

  const offlineCount = services.filter((s) => s.status === 'OFFLINE').length;

  const renderNavGroup = (label: string, entries: NavEntry[]) => {
    // Filter against the SERVER's permission list, so navigation can never offer
    // a destination the API would reject.
    const visible = entries.filter((entry) => !entry.permission || can(entry.permission));
    if (visible.length === 0) return null;

    return (
    <div className="mb-6">
      <p className="mb-2 px-3 text-[11px] font-semibold tracking-wide text-[var(--color-ink-faint)] uppercase">
        {label}
      </p>
      <nav className="flex flex-col gap-0.5">
        {visible.map(({ to, label: navLabel, icon: Icon, badge }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            onClick={closeMobileNav}
            className={({ isActive }) =>
              cx(
                'group flex items-center gap-3 rounded-lg px-3 py-2 text-[13.5px] transition-colors',
                isActive
                  ? 'bg-[var(--color-accent-soft)] font-medium text-[var(--color-ink-primary)]'
                  : 'text-[var(--color-ink-secondary)] hover:bg-[var(--color-surface-overlay)] hover:text-[var(--color-ink-primary)]',
              )
            }
          >
            {({ isActive }) => (
              <>
                <Icon
                  size={17}
                  className={
                    isActive ? 'text-[var(--color-accent-hover)]' : 'text-[var(--color-ink-muted)]'
                  }
                />
                <span className="flex-1 truncate">{navLabel}</span>
                {badge !== undefined && badge > 0 && (
                  <span className="rounded-full bg-[var(--color-danger-soft)] px-1.5 py-0.5 text-[10px] font-semibold text-[var(--color-danger)] tabular-nums">
                    {badge}
                  </span>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </div>
    );
  };

  const sidebarContent = (
    <>
      <div className="flex items-center gap-2.5 px-3 py-5">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--color-accent)]">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M12 3a4 4 0 0 0-4 4v1a3 3 0 0 0 0 6v1a4 4 0 0 0 8 0v-1a3 3 0 0 0 0-6V7a4 4 0 0 0-4-4Z"
              stroke="white"
              strokeWidth="1.7"
              strokeLinejoin="round"
            />
            <path d="M12 3v18" stroke="white" strokeWidth="1.7" />
          </svg>
        </div>
        <div className="min-w-0">
          <p className="truncate text-[15px] leading-tight font-semibold text-[var(--color-ink-primary)]">
            IndusBrain
          </p>
          <p className="truncate text-[11.5px] text-[var(--color-ink-muted)]">
            Industrial Knowledge OS
          </p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2">
        {renderNavGroup('Workspace', primaryNav)}
        {renderNavGroup('Insight', secondaryNav)}
      </div>

      <RoleSwitcher />

      {/* System health — the actual state of the four backing services */}
      <div className="border-t border-[var(--color-line-subtle)] px-4 py-3.5">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-[11px] font-semibold tracking-wide text-[var(--color-ink-faint)] uppercase">
            System
          </p>
          {offlineCount > 0 && (
            <span className="text-[11px] font-medium text-[var(--color-danger)]">
              {offlineCount} offline
            </span>
          )}
        </div>
        <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
          {services.length === 0 ? (
            <p className="col-span-2 text-[12px] text-[var(--color-ink-faint)]">Connecting…</p>
          ) : (
            services.map((service) => (
              <div key={service.name} className="flex items-center gap-1.5">
                <StatusDot
                  online={service.status !== 'OFFLINE'}
                  degraded={service.status === 'NO_MODELS'}
                />
                <span
                  className="truncate text-[12px] text-[var(--color-ink-muted)]"
                  title={`${service.name}: ${service.status}`}
                >
                  {service.name}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </>
  );

  return (
    <div className="flex min-h-screen bg-[var(--color-surface-base)]">
      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-[var(--color-line-subtle)] bg-[var(--color-surface-raised)] lg:flex">
        {sidebarContent}
      </aside>

      {/* Mobile drawer */}
      {mobileNavOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            className="absolute inset-0 bg-black/60"
            onClick={() => setMobileNavOpen(false)}
            aria-label="Close navigation"
          />
          <aside className="animate-fade-in relative flex h-full w-64 flex-col border-r border-[var(--color-line-subtle)] bg-[var(--color-surface-raised)]">
            {sidebarContent}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile top bar */}
        <header className="sticky top-0 z-40 flex items-center gap-3 border-b border-[var(--color-line-subtle)] bg-[var(--color-surface-raised)]/95 px-4 py-3 backdrop-blur lg:hidden">
          <button
            onClick={() => setMobileNavOpen(true)}
            className="rounded-lg p-1.5 text-[var(--color-ink-secondary)] hover:bg-[var(--color-surface-overlay)]"
            aria-label="Open navigation"
          >
            <IconMenu size={20} />
          </button>
          <span className="text-[15px] font-semibold">IndusBrain</span>
          {openConflicts > 0 && (
            <span className="ml-auto rounded-full bg-[var(--color-danger-soft)] px-2 py-0.5 text-[11px] font-semibold text-[var(--color-danger)]">
              {openConflicts} conflict{openConflicts === 1 ? '' : 's'}
            </span>
          )}
        </header>

        {/* Backend unreachable — a persistent, non-animated banner */}
        {connectionError && (
          <div className="flex items-start gap-3 border-b border-[color-mix(in_srgb,var(--color-danger)_30%,transparent)] bg-[var(--color-danger-soft)] px-5 py-3">
            <IconAlert size={17} className="mt-0.5 shrink-0 text-[var(--color-danger)]" />
            <div className="min-w-0">
              <p className="text-[13px] font-medium text-[var(--color-danger)]">
                Cannot reach the IndusBrain API
              </p>
              <p className="mt-0.5 text-[12.5px] text-[var(--color-ink-secondary)]">
                {connectionError} Data shown may be stale.
              </p>
            </div>
          </div>
        )}

        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
};

export const PageHeader: React.FC<{
  title: string;
  description?: string;
  actions?: React.ReactNode;
}> = ({ title, description, actions }) => (
  <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
    <div className="min-w-0">
      <h1 className="text-[22px] leading-tight font-semibold tracking-[-0.01em] text-[var(--color-ink-primary)]">
        {title}
      </h1>
      {description && (
        <p className="mt-1 max-w-2xl text-[13.5px] text-[var(--color-ink-muted)]">{description}</p>
      )}
    </div>
    {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
  </div>
);

export const PageBody: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="mx-auto w-full max-w-[1400px] px-5 py-6 sm:px-7 sm:py-8">{children}</div>
);
