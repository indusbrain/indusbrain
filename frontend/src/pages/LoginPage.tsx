import React, { useState } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import { ApiError } from '../lib/api';
import { roleLabel, useAuth } from '../lib/AuthContext';
import type { RoleId } from '../lib/types';
import { FaultNotice } from '../components/ui/FaultNotice';
import { Logo, LogoMark } from '../components/brand/Logo';
import { IconShield, IconUsers, IconWrench } from '../components/ui/icons';
import { EASE_VALVE } from '../components/motion/Motion';

/**
 * Sign-in for Employees and Managers.
 *
 * A black, noisy screen with a slowly turning hex watermark and the same
 * cursor-focus grid as the app. Two tabs choose the role to enter as.
 *
 *   demo mode    No credentials exist. Picking a tab and continuing enters the
 *                app as that role; the API still enforces what the role may do.
 *                The screen says so plainly — it is not a security boundary.
 *   secure mode  Email + password. The role comes from the account in the
 *                database; if someone picks the Manager tab with an Employee
 *                account they are signed out again and told why.
 *
 * "Employee" is the user-facing name for the backend's `engineer` role.
 */

const ROLE_TABS: Array<{
  id: RoleId;
  icon: React.FC<{ size?: number; className?: string }>;
  fallback: string;
}> = [
  {
    id: 'engineer',
    icon: IconWrench,
    fallback: 'Ask questions, search the knowledge base and read source documents.',
  },
  {
    id: 'manager',
    icon: IconUsers,
    fallback: 'Everything an employee can do, plus upload, replace and remove documents.',
  },
];

export const LoginPage: React.FC = () => {
  const { mode, login, register, enterDemo, logout, roles } = useAuth();
  const reduce = useReducedMotion();

  // With no roles loaded the backend has not been reached; in secure mode treat
  // that as first run so account creation is offered rather than a dead login.
  const isFirstRun = mode === 'secure' && roles.length === 0;
  const [selected, setSelected] = useState<RoleId>('engineer');
  const [formMode, setFormMode] = useState<'login' | 'register'>(isFirstRun ? 'register' : 'login');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeForm = isFirstRun ? 'register' : formMode;
  const selectedTab = ROLE_TABS.find((tab) => tab.id === selected) ?? ROLE_TABS[0];
  const description = roles.find((r) => r.id === selected)?.description ?? selectedTab.fallback;

  const chooseRole = (role: RoleId) => {
    setSelected(role);
    setError(null);
    // Accounts can only be created as Employees; managers are promoted.
    if (role === 'manager' && !isFirstRun) setFormMode('login');
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    if (mode === 'demo') {
      enterDemo(selected);
      return;
    }

    setBusy(true);
    try {
      const profile =
        activeForm === 'register'
          ? await register(email.trim(), fullName.trim(), password)
          : await login(email.trim(), password);

      if (selected === 'manager' && profile.role !== 'manager') {
        await logout();
        setError('This account does not have manager access. Choose Employee, or ask a manager to upgrade you.');
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  const fieldClass =
    'w-full rounded-[14px] border border-white/12 bg-white/[0.06] px-4 py-3 text-[14.5px] text-white ' +
    'placeholder:text-white/35 transition-colors duration-200 hover:border-white/25 focus:border-white/60 focus:bg-white/[0.09]';
  const labelClass = 'mb-1.5 block text-[12.5px] font-medium text-white/60';

  return (
    // data-theme="dark" remaps every token inside, so shared components and
    // the logo render light-on-black here regardless of the app's theme.
    <div data-theme="dark" className="noir relative isolate min-h-screen overflow-hidden">
      {/* Slowly turning hex watermark */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute top-1/2 left-[-8vw] -z-0 -translate-y-1/2 text-white opacity-[0.07]"
      >
        <motion.div
          animate={reduce ? undefined : { rotate: 360 }}
          transition={{ duration: 120, ease: 'linear', repeat: Infinity }}
        >
          <LogoMark size={720} animate={false} className="[&_*]:stroke-[0.5]" />
        </motion.div>
      </div>

      <div className="relative z-10 grid min-h-screen lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        {/* ── Brand side ─────────────────────────────────────────────────── */}
        <section className="flex flex-col justify-between gap-12 px-[var(--gutter)] py-8 sm:py-10 lg:px-[clamp(32px,5vw,88px)]">
          <Logo size={34} />

          <div className="max-w-xl">
            <motion.h1
              initial={reduce ? false : { opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, ease: EASE_VALVE, delay: 0.15 }}
              className="text-[clamp(2.6rem,1.4rem+4.6vw,5.4rem)] leading-[0.95] font-semibold tracking-[-0.045em]"
            >
              Every manual.
              <br />
              Every log.
              <br />
              <span className="text-white/45">One answer.</span>
            </motion.h1>
            <motion.p
              initial={reduce ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: EASE_VALVE, delay: 0.35 }}
              className="mt-6 max-w-md text-[16px] leading-relaxed text-white/60"
            >
              IndusBrain reads your plant&rsquo;s documentation, answers with the exact passage it came
              from, and flags where two documents disagree.
            </motion.p>
          </div>

          <p className="hidden text-[12.5px] text-white/40 lg:block">
            Answers cite their sources. Nothing is estimated.
          </p>
        </section>

        {/* ── Sign-in panel ──────────────────────────────────────────────── */}
        <section className="flex items-center justify-center px-[var(--gutter)] py-10">
          <motion.div
            initial={reduce ? false : { opacity: 0, y: 24, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.7, ease: EASE_VALVE, delay: 0.2 }}
            className="glass w-full max-w-[440px] rounded-[28px] p-7 sm:p-9"
          >
            <h2 className="text-[26px] leading-tight font-semibold tracking-[-0.03em] text-white">
              {activeForm === 'register' ? 'Create your account' : 'Sign in'}
            </h2>
            <p className="mt-1.5 text-[14px] text-white/55">
              {mode === 'demo'
                ? 'Choose how you are entering today.'
                : activeForm === 'register'
                  ? 'Set a password you will remember — there is no reset flow yet.'
                  : 'Use the credentials for your plant account.'}
            </p>

            {/* Role tabs — an underline slides between them; no boxes. */}
            <div role="tablist" aria-label="Sign in as" className="mt-7 flex gap-7 border-b border-white/12">
              {ROLE_TABS.map(({ id, icon: Icon }) => {
                const active = id === selected;
                return (
                  <button
                    key={id}
                    role="tab"
                    id={`tab-${id}`}
                    aria-selected={active}
                    aria-controls="login-panel"
                    onClick={() => chooseRole(id)}
                    className={`relative -mb-px flex items-center gap-2 pb-3 text-[15px] font-medium transition-colors duration-200 ${
                      active ? 'text-white' : 'text-white/45 hover:text-white/75'
                    }`}
                  >
                    <Icon size={17} />
                    {roleLabel(id)}
                    {active &&
                      (reduce ? (
                        <span className="absolute inset-x-0 -bottom-px h-[2px] bg-white" />
                      ) : (
                        <motion.span
                          layoutId="login-tab"
                          className="absolute inset-x-0 -bottom-px h-[2px] bg-white"
                          transition={{ type: 'spring', stiffness: 520, damping: 42 }}
                        />
                      ))}
                  </button>
                );
              })}
            </div>

            <form
              id="login-panel"
              role="tabpanel"
              aria-labelledby={`tab-${selected}`}
              onSubmit={submit}
              className="mt-5"
            >
              <p className="min-h-[3.2em] text-[13.5px] leading-relaxed text-white/60">{description}</p>

              {mode === 'secure' && (
                <div className="mt-4 space-y-4">
                  {isFirstRun && (
                    <p className="flex items-start gap-2 text-[13px] leading-relaxed text-[var(--color-info)]">
                      <IconShield size={15} className="mt-0.5 shrink-0" />
                      No accounts exist yet. The first account you create becomes the manager.
                    </p>
                  )}

                  {activeForm === 'register' && (
                    <div>
                      <label htmlFor="full-name" className={labelClass}>
                        Full name
                      </label>
                      <input
                        id="full-name"
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        required
                        minLength={2}
                        autoComplete="name"
                        placeholder="Jordan Rivera"
                        className={fieldClass}
                      />
                    </div>
                  )}

                  <div>
                    <label htmlFor="email" className={labelClass}>
                      Work email
                    </label>
                    <input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      autoComplete="email"
                      placeholder="you@plant.com"
                      className={fieldClass}
                    />
                  </div>

                  <div>
                    <label htmlFor="password" className={labelClass}>
                      Password
                    </label>
                    <input
                      id="password"
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      minLength={8}
                      autoComplete={activeForm === 'register' ? 'new-password' : 'current-password'}
                      placeholder="At least 8 characters"
                      className={fieldClass}
                    />
                  </div>
                </div>
              )}

              {error && (
                <div className="mt-5">
                  <FaultNotice kicker="Sign-in failed" title={error} compact />
                </div>
              )}

              <button
                type="submit"
                disabled={busy}
                className="pressable mt-6 w-full rounded-[14px] bg-white py-3 text-[15px] font-semibold text-black transition-opacity duration-200 hover:opacity-90 disabled:opacity-50"
              >
                {busy
                  ? 'Checking credentials…'
                  : mode === 'demo'
                    ? `Continue as ${roleLabel(selected)}`
                    : activeForm === 'register'
                      ? 'Create account'
                      : `Sign in as ${roleLabel(selected)}`}
              </button>

              {mode === 'demo' && (
                <p className="mt-4 text-center text-[12.5px] leading-relaxed text-white/45">
                  Demo mode: no password is required. What each role may do is still enforced by the
                  server.
                </p>
              )}

              {mode === 'secure' && !isFirstRun && selected === 'engineer' && (
                <p className="mt-5 text-center text-[13.5px] text-white/55">
                  {activeForm === 'login' ? "Don't have an account?" : 'Already have an account?'}{' '}
                  <button
                    type="button"
                    onClick={() => {
                      setFormMode(activeForm === 'login' ? 'register' : 'login');
                      setError(null);
                    }}
                    className="font-semibold text-white underline-offset-4 hover:underline"
                  >
                    {activeForm === 'login' ? 'Create one' : 'Sign in'}
                  </button>
                </p>
              )}
            </form>
          </motion.div>
        </section>
      </div>
    </div>
  );
};
