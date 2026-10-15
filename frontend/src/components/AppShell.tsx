import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { motion, useReducedMotion } from 'motion/react';
import type { DashboardPayload, PermissionId } from '../lib/types';
import { roleLabel, useAuth } from '../lib/AuthContext';
import { useTheme } from '../lib/theme';
import { cx, StatusDot } from './ui/primitives';
import { FaultNotice } from './ui/FaultNotice';
import { Logo, LogoMark } from './brand/Logo';
import { SHOW_INFRASTRUCTURE_DETAILS } from '../lib/uiConfig';
import {
  IconAlert,
  IconChart,
  IconChat,
  IconDocs,
  IconFlask,
  IconGauge,
  IconGraph,
  IconMenu,
  IconMoon,
  IconSidebar,
  IconSignOut,
  IconSun,
} from './ui/icons';

/**
 * Application shell.
 *
 * Wallpaper + noise + cursor-focus grid sit fixed behind everything (Backdrop).
 * The sidebar is a floating glass pane that can be closed (button, or
 * Ctrl/Cmd + B); the choice is remembered per browser. Pages render on the
 * wallpaper as glass containers.
 */

interface NavEntry {
  to: string;
  label: string;
  icon: React.FC<{ size?: number; className?: string }>;
  badge?: number;
  permission?: PermissionId;
}

/** Lets PageHeader read issue time / document count without prop drilling. */
const ShellContext = createContext<DashboardPayload | null>(null);

const SIDEBAR_KEY = 'indusbrain.sidebar';
/** Expanded: icons + labels. Collapsed: an icon rail (logo, nav icons, controls). */
const SIDEBAR_WIDTH = '17rem';
const RAIL_WIDTH = '4.5rem';

function loadSidebarExpanded(): boolean {
  try {
    return localStorage.getItem(SIDEBAR_KEY) !== 'closed';
  } catch {
    return true;
  }
}

// ---------------------------------------------------------------------------
// Small icon buttons (theme, sidebar)
// ---------------------------------------------------------------------------
const ThemeSwitch: React.FC<{ className?: string }> = ({ className }) => {
  const { theme, toggleTheme } = useTheme();
  const dark = theme === 'dark';
  return (
    <button
      onClick={toggleTheme}
      aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}
      title={dark ? 'Light theme' : 'Dark theme'}
      className={cx(
        'pressable inline-flex h-8 w-8 items-center justify-center rounded-[var(--radius-control)] text-[var(--color-frame-muted)] hover:bg-[var(--color-frame-raised)] hover:text-[var(--color-frame-ink)]',
        className,
      )}
    >
      {dark ? <IconSun size={16} /> : <IconMoon size={16} />}
    </button>
  );
};

const SidebarToggle: React.FC<{ expanded: boolean; onToggle: () => void; className?: string }> = ({
  expanded,
  onToggle,
  className,
}) => (
  <button
    onClick={onToggle}
    aria-label={expanded ? 'Collapse sidebar' : 'Expand sidebar'}
    aria-expanded={expanded}
    title={`${expanded ? 'Collapse' : 'Expand'} sidebar (Ctrl+B)`}
    className={cx(
      'pressable inline-flex h-8 w-8 items-center justify-center rounded-[var(--radius-control)] text-[var(--color-frame-muted)] hover:bg-[var(--color-frame-raised)] hover:text-[var(--color-frame-ink)]',
      className,
    )}
  >
    <IconSidebar size={17} />
  </button>
);

/**
 * Signed-in user panel.
 *
 * Demo mode has no accounts: the role chosen on the login screen is shown, and
 * "Sign out" returns to that screen. In secure mode the role is the one stored
 * against the account in the database and cannot be changed from the client.
 */
const UserPanel: React.FC<{ collapsed?: boolean }> = ({ collapsed = false }) => {
  const { mode, user, role, roles, logout } = useAuth();
  const [busy, setBusy] = useState(false);

  const displayName = user?.full_name ?? roleLabel(role);
  const subtitle = user?.email ?? roles.find((r) => r.id === role)?.description;
  const roleText = user ? roleLabel(user.role) : mode === 'demo' ? 'Demo session' : '';
  const initials = (user?.full_name ?? roleLabel(role))
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');

  const signOut = async () => {
    setBusy(true);
    await logout();
    setBusy(false);
  };

  const avatar = (
    <div
      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--color-frame-raised)] text-[12.5px] font-semibold text-[var(--color-frame-ink)]"
      title={collapsed ? `${displayName} · ${roleText}` : undefined}
    >
      {initials || '?'}
    </div>
  );

  // Icon rail: just the avatar and a sign-out icon, stacked.
  if (collapsed) {
    return (
      <div className="flex flex-col items-center gap-1.5 border-t border-[var(--color-frame-line)] px-2 py-3">
        {avatar}
        <button
          onClick={signOut}
          disabled={busy}
          aria-label="Sign out"
          title="Sign out"
          className="pressable inline-flex h-8 w-8 items-center justify-center rounded-[var(--radius-control)] text-[var(--color-frame-muted)] hover:bg-[var(--color-frame-raised)] hover:text-[var(--color-frame-ink)] disabled:opacity-50"
        >
          <IconSignOut size={16} />
        </button>
      </div>
    );
  }

  return (
    <div className="border-t border-[var(--color-frame-line)] px-4 py-4">
      <div className="flex items-center gap-3">
        {avatar}
        <div className="min-w-0 flex-1">
          <p className="truncate text-[13.5px] font-medium text-[var(--color-frame-ink)]" title={displayName}>
            {displayName}
          </p>
          <p className="truncate text-[12px] text-[var(--color-frame-muted)]" title={subtitle}>
            {roleText}
          </p>
        </div>
        <button
          onClick={signOut}
          disabled={busy}
          className="pressable rounded-[var(--radius-control)] px-2 py-1 text-[12.5px] text-[var(--color-frame-muted)] hover:bg-[var(--color-frame-raised)] hover:text-[var(--color-frame-ink)] disabled:opacity-50"
        >
          {busy ? '…' : 'Sign out'}
        </button>
      </div>
    </div>
  );
};

export const AppShell: React.FC<{
  dashboard: DashboardPayload | null;
  connectionError: string | null;
  children: React.ReactNode;
}> = ({ dashboard, connectionError, children }) => {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [expanded, setExpanded] = useState(loadSidebarExpanded);
  const { can } = useAuth();
  const reduce = useReducedMotion();

  const toggleSidebar = useCallback(() => {
    setExpanded((open) => {
      try {
        // 'closed' is the stored name for the collapsed icon rail.
        localStorage.setItem(SIDEBAR_KEY, open ? 'closed' : 'open');
      } catch {
        /* storage blocked — the choice just won't persist */
      }
      return !open;
    });
  }, []);

  // Ctrl/Cmd + B collapses / expands the sidebar, as in most editors and macOS apps.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'b') {
        event.preventDefault();
        toggleSidebar();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [toggleSidebar]);

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

  // Documents is visible to BOTH roles - engineers need to read source material.
  // The page itself gates the mutating ACTIONS (upload, delete) on permission,
  // rather than hiding the whole area from engineers.
  const secondaryNav: NavEntry[] = [
    { to: '/analytics', label: 'Analytics', icon: IconChart },
    { to: '/simulator', label: 'Impact Simulator', icon: IconFlask },
    { to: '/documents', label: 'Documents', icon: IconDocs, permission: 'view_documents' },
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

  // `layoutGroup` differs between desktop and the mobile drawer so the sliding
  // active marker never tries to animate between the two copies of the nav.
  const renderNavGroup = (label: string, entries: NavEntry[], layoutGroup: string, collapsed: boolean) => {
    // Filter against the SERVER's permission list, so navigation can never offer
    // a destination the API would reject.
    const visible = entries.filter((entry) => !entry.permission || can(entry.permission));
    if (visible.length === 0) return null;

    return (
      <div className={collapsed ? 'mb-4' : 'mb-6'}>
        {collapsed ? (
          <span aria-hidden="true" className="mx-3 mb-2 block h-px bg-[var(--color-frame-line)]" />
        ) : (
          <p className="eyebrow mb-1.5 px-3 !text-[var(--color-frame-muted)]">{label}</p>
        )}
        <nav className="flex flex-col gap-0.5" aria-label={label}>
          {visible.map(({ to, label: navLabel, icon: Icon, badge }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={closeMobileNav}
              title={collapsed ? navLabel : undefined}
              aria-label={navLabel}
              className={({ isActive }) =>
                cx(
                  'group relative flex items-center rounded-[var(--radius-control)] py-2.5 text-[14px] transition-colors duration-200',
                  collapsed ? 'justify-center px-0' : 'gap-3 px-3',
                  isActive
                    ? 'font-medium text-[var(--color-frame-ink)]'
                    : 'text-[var(--color-frame-muted)] hover:text-[var(--color-frame-ink)]',
                )
              }
            >
              {({ isActive }) => (
                <>
                  {/* Active marker slides between items (shared layout). */}
                  {isActive &&
                    (reduce ? (
                      <span className="absolute inset-0 rounded-[var(--radius-control)] bg-[var(--color-frame-raised)]" />
                    ) : (
                      <motion.span
                        layoutId={`nav-active-${layoutGroup}`}
                        className="absolute inset-0 rounded-[var(--radius-control)] bg-[var(--color-frame-raised)]"
                        transition={{ type: 'spring', stiffness: 520, damping: 40 }}
                      />
                    ))}
                  <Icon
                    size={18}
                    className={cx(
                      'relative transition-transform duration-300 group-hover:-translate-y-px',
                      isActive ? 'text-[var(--color-accent)]' : 'text-[var(--color-frame-muted)]',
                    )}
                  />
                  <span className={cx('relative flex-1 truncate', collapsed && 'sr-only')}>{navLabel}</span>
                  {badge !== undefined &&
                    badge > 0 &&
                    (collapsed ? (
                      // Rail: a dot on the icon.
                      <span
                        aria-hidden="true"
                        className="absolute top-2 right-3 h-2 w-2 rounded-full bg-[var(--color-danger)]"
                      />
                    ) : (
                      <span className="relative text-[13px] font-semibold text-[var(--color-danger)] tabular-nums">
                        {badge}
                      </span>
                    ))}
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </div>
    );
  };

  const sidebarContent = (layoutGroup: string, showToggle: boolean, collapsed: boolean) => (
    <>
      {collapsed ? (
        <div className="flex flex-col items-center gap-3 px-2 pt-5 pb-5">
          <NavLink
            to="/"
            onClick={closeMobileNav}
            className="rounded-[var(--radius-control)] text-[var(--color-frame-ink)]"
            aria-label="IndusBrain overview"
            title="IndusBrain"
          >
            <LogoMark size={30} />
          </NavLink>
          {showToggle && <SidebarToggle expanded={false} onToggle={toggleSidebar} />}
        </div>
      ) : (
        <div className="flex items-center justify-between gap-2 px-4 pt-5 pb-6">
          <NavLink
            to="/"
            onClick={closeMobileNav}
            className="rounded-[var(--radius-control)] text-[var(--color-frame-ink)]"
            aria-label="IndusBrain overview"
          >
            <Logo size={30} />
          </NavLink>
          {showToggle && <SidebarToggle expanded onToggle={toggleSidebar} />}
        </div>
      )}

      <div className="flex-1 overflow-x-hidden overflow-y-auto px-2">
        {renderNavGroup('Workspace', primaryNav, layoutGroup, collapsed)}
        {renderNavGroup('Insight', secondaryNav, layoutGroup, collapsed)}
      </div>

      {/* Service health.
          Named infrastructure is hidden for the demo (see uiConfig). What is NOT
          hidden is the consequence: if a backing service is down, features are
          silently degraded, and the operator still needs to know that — just in
          product terms rather than database names. */}
      {collapsed ? (
        offlineCount > 0 && (
          <div
            className="flex justify-center border-t border-[var(--color-frame-line)] py-3"
            title="Some features are temporarily limited. Search results may be incomplete."
          >
            <StatusDot online={false} />
          </div>
        )
      ) : SHOW_INFRASTRUCTURE_DETAILS ? (
        <div className="border-t border-[var(--color-frame-line)] px-4 py-3.5">
          <div className="mb-2 flex items-center justify-between">
            <p className="eyebrow !text-[var(--color-frame-muted)]">System</p>
            {offlineCount > 0 && (
              <span className="text-[12px] font-medium text-[var(--color-danger)]">
                {offlineCount} offline
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
            {services.length === 0 ? (
              <p className="col-span-2 text-[12px] text-[var(--color-frame-muted)]">Connecting…</p>
            ) : (
              services.map((service) => (
                <div key={service.name} className="flex items-center gap-1.5">
                  <StatusDot
                    online={service.status !== 'OFFLINE'}
                    degraded={service.status === 'NO_MODELS'}
                  />
                  <span
                    className="truncate text-[12px] text-[var(--color-frame-muted)]"
                    title={`${service.name}: ${service.status}`}
                  >
                    {service.name}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      ) : (
        offlineCount > 0 && (
          <div className="flex items-start gap-2 border-t border-[var(--color-frame-line)] px-4 py-3">
            <span className="mt-1.5">
              <StatusDot online={false} />
            </span>
            <p className="text-[12.5px] leading-snug text-[var(--color-frame-muted)]">
              Some features are temporarily limited. Search results may be incomplete.
            </p>
          </div>
        )
      )}

      <div
        className={cx(
          'flex items-center border-t border-[var(--color-frame-line)] py-2.5',
          collapsed ? 'justify-center px-2' : 'justify-between px-4',
        )}
      >
        {!collapsed && <span className="text-[12.5px] text-[var(--color-frame-muted)]">Appearance</span>}
        <ThemeSwitch />
      </div>

      <UserPanel collapsed={collapsed} />
    </>
  );

  return (
    <ShellContext.Provider value={dashboard}>
      <div className="relative z-10 flex min-h-screen">
        {/* Desktop sidebar: a glass panel flush with the window edge (no outer
            margin). It never disappears — it collapses to an icon rail. */}
        <div
          className="hidden shrink-0 transition-[width] duration-[420ms] ease-[var(--ease-valve)] lg:block"
          style={{ width: expanded ? SIDEBAR_WIDTH : RAIL_WIDTH }}
        >
          <aside
            aria-label="Main navigation"
            data-sidebar
            className="glass sticky top-0 flex h-screen w-full flex-col overflow-hidden rounded-none border-y-0 border-l-0 bg-[var(--color-frame)] text-[var(--color-frame-ink)]"
          >
            {sidebarContent('desktop', true, !expanded)}
          </aside>
        </div>

        {/* Mobile drawer */}
        {mobileNavOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <button
              className="animate-fade-in absolute inset-0 bg-black/40"
              onClick={() => setMobileNavOpen(false)}
              aria-label="Close navigation"
            />
            <aside
              data-sidebar
              className="glass-strong animate-fade-rise relative flex h-full w-72 max-w-[85vw] flex-col overflow-hidden rounded-none border-y-0 border-l-0 bg-[var(--color-frame-drawer)] text-[var(--color-frame-ink)]"
            >
              {sidebarContent('mobile', false, false)}
            </aside>
          </div>
        )}

        <div className="flex min-w-0 flex-1 flex-col">
          {/* Mobile top bar */}
          <header className="glass sticky top-0 z-40 flex items-center gap-3 border-x-0 border-t-0 px-4 py-3 lg:hidden">
            <button
              onClick={() => setMobileNavOpen(true)}
              className="pressable rounded-[var(--radius-control)] p-1.5 text-[var(--color-ink-primary)] hover:bg-[var(--color-surface-overlay)]"
              aria-label="Open navigation"
            >
              <IconMenu size={20} />
            </button>
            <Logo size={24} animate={false} />
            <div className="ml-auto flex items-center gap-3">
              {openConflicts > 0 && (
                <span className="text-[12.5px] font-semibold text-[var(--color-danger)]">
                  {openConflicts} conflict{openConflicts === 1 ? '' : 's'}
                </span>
              )}
              <ThemeSwitch />
            </div>
          </header>

          {/* Backend unreachable — a persistent notice, shown until it recovers */}
          {connectionError && (
            <div className="mx-[var(--gutter)] mt-4">
              <FaultNotice
                kicker="Connection lost"
                title="Cannot reach the IndusBrain API"
                detail={`${connectionError} Data shown may be stale.`}
                compact
              />
            </div>
          )}

          <main className="min-w-0 flex-1">{children}</main>
        </div>
      </div>
    </ShellContext.Provider>
  );
};

// ---------------------------------------------------------------------------
// Page header
// ---------------------------------------------------------------------------
function formatIssued(epochSeconds: number): string {
  const d = new Date(epochSeconds * 1000);
  const date = d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
  const time = d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  return `${date}, ${time}`;
}

/**
 * Page header: a large title, a one-line description, and — as plain text, not
 * a box — how many documents the view covers and when the data was issued. The
 * issue time is the dashboard's `generated_at`, never the browser clock.
 */
export const PageHeader: React.FC<{
  title: string;
  description?: string;
  actions?: React.ReactNode;
}> = ({ title, description, actions }) => {
  const dashboard = useContext(ShellContext);

  return (
    <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <h1 className="text-[length:var(--text-sheet-title)] leading-[1.05] font-semibold tracking-[-0.035em] text-[var(--color-ink-primary)]">
          {title}
        </h1>
        {description && (
          <p className="mt-2 max-w-2xl text-[14.5px] leading-relaxed text-[var(--color-ink-muted)]">{description}</p>
        )}
        {dashboard && (
          <p className="mt-2 text-[12.5px] text-[var(--color-ink-muted)] tabular-nums">
            {dashboard.metrics.total_documents} documents · updated {formatIssued(dashboard.generated_at)}
          </p>
        )}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
};

export const PageBody: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="mx-auto w-full max-w-[1440px] px-[var(--gutter)] py-8 sm:py-10">{children}</div>
);
