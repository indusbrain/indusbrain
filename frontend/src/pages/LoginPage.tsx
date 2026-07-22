import React, { useState } from 'react';
import { ApiError } from '../lib/api';
import { useAuth } from '../lib/AuthContext';
import { Button, cx, ErrorNotice } from '../components/ui/primitives';
import { IconShield } from '../components/ui/icons';

/**
 * Sign-in and account creation.
 *
 * When no account exists yet, the form switches to "create the first account"
 * and explains that it becomes the manager — so a fresh deployment has an
 * administrator without any seeded default credentials.
 */
export const LoginPage: React.FC = () => {
  const { login, register, roles } = useAuth();

  // With no roles loaded the backend has not been reached; treat as first run so
  // the user is offered account creation rather than a login they cannot pass.
  const isFirstRun = roles.length === 0;
  const [mode, setMode] = useState<'login' | 'register'>(isFirstRun ? 'register' : 'login');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeMode = isFirstRun ? 'register' : mode;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (activeMode === 'register') {
        await register(email.trim(), fullName.trim(), password);
      } else {
        await login(email.trim(), password);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  const inputClass =
    'w-full rounded-lg border border-[var(--color-line-default)] bg-[var(--color-surface-base)] px-3.5 py-2.5 ' +
    'text-[14px] text-[var(--color-ink-primary)] placeholder:text-[var(--color-ink-faint)] ' +
    'focus:border-[var(--color-accent)]';

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--color-surface-base)] px-5 py-10">
      <div className="w-full max-w-[400px]">
        {/* Brand */}
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-[var(--color-accent)]">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M12 3a4 4 0 0 0-4 4v1a3 3 0 0 0 0 6v1a4 4 0 0 0 8 0v-1a3 3 0 0 0 0-6V7a4 4 0 0 0-4-4Z"
                stroke="white"
                strokeWidth="1.7"
                strokeLinejoin="round"
              />
              <path d="M12 3v18" stroke="white" strokeWidth="1.7" />
            </svg>
          </div>
          <h1 className="text-[20px] font-semibold text-[var(--color-ink-primary)]">IndusBrain</h1>
          <p className="mt-0.5 text-[13.5px] text-[var(--color-ink-muted)]">
            Industrial Knowledge Intelligence Platform
          </p>
        </div>

        <div className="rounded-xl border border-[var(--color-line-subtle)] bg-[var(--color-surface-raised)] p-6">
          {isFirstRun && (
            <div className="mb-5 flex items-start gap-2.5 rounded-lg border border-[color-mix(in_srgb,var(--color-info)_26%,transparent)] bg-[var(--color-info-soft)] px-3.5 py-3">
              <IconShield size={15} className="mt-0.5 shrink-0 text-[var(--color-info)]" />
              <p className="text-[12.5px] leading-relaxed text-[var(--color-ink-secondary)]">
                No accounts exist yet. The first account you create becomes the
                <span className="font-medium text-[var(--color-info)]"> manager</span>, with
                permission to upload and manage documents.
              </p>
            </div>
          )}

          <h2 className="mb-1 text-[16px] font-semibold text-[var(--color-ink-primary)]">
            {activeMode === 'register' ? 'Create your account' : 'Sign in'}
          </h2>
          <p className="mb-5 text-[13px] text-[var(--color-ink-muted)]">
            {activeMode === 'register'
              ? 'Set a password you will remember — there is no reset flow yet.'
              : 'Use the credentials for your plant account.'}
          </p>

          {error && (
            <div className="mb-4">
              <ErrorNotice title="Could not continue" detail={error} />
            </div>
          )}

          <form onSubmit={submit} className="space-y-3.5">
            {activeMode === 'register' && (
              <div>
                <label htmlFor="full-name" className="mb-1.5 block text-[13px] text-[var(--color-ink-secondary)]">
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
                  className={inputClass}
                />
              </div>
            )}

            <div>
              <label htmlFor="email" className="mb-1.5 block text-[13px] text-[var(--color-ink-secondary)]">
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
                className={inputClass}
              />
            </div>

            <div>
              <label htmlFor="password" className="mb-1.5 block text-[13px] text-[var(--color-ink-secondary)]">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                autoComplete={activeMode === 'register' ? 'new-password' : 'current-password'}
                placeholder="At least 8 characters"
                className={inputClass}
              />
              {activeMode === 'register' && (
                <p className="mt-1.5 text-[12px] text-[var(--color-ink-faint)]">
                  Minimum 8 characters, mixing letters and numbers.
                </p>
              )}
            </div>

            <Button type="submit" variant="primary" className="w-full" disabled={busy}>
              {busy
                ? 'Please wait…'
                : activeMode === 'register'
                  ? 'Create account'
                  : 'Sign in'}
            </Button>
          </form>

          {!isFirstRun && (
            <p className="mt-5 border-t border-[var(--color-line-subtle)] pt-4 text-center text-[13px] text-[var(--color-ink-muted)]">
              {mode === 'login' ? "Don't have an account?" : 'Already have an account?'}{' '}
              <button
                onClick={() => {
                  setMode(mode === 'login' ? 'register' : 'login');
                  setError(null);
                }}
                className={cx('font-medium text-[var(--color-accent-hover)] hover:underline')}
              >
                {mode === 'login' ? 'Create one' : 'Sign in'}
              </button>
            </p>
          )}
        </div>

        <p className="mt-5 text-center text-[12px] leading-relaxed text-[var(--color-ink-faint)]">
          New accounts are created with the engineer role. Ask a manager to upgrade you if you need
          to manage documents.
        </p>
      </div>
    </div>
  );
};
