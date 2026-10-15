import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, setActiveRole, setAuthToken } from './api';
import type { PermissionId, RoleDefinition, RoleId, UserProfile } from './types';

/**
 * Session state for the whole application.
 *
 * Two modes, selected by the backend's AUTH_MODE setting:
 *
 *   demo   - no credentials. The login screen asks only which role to enter as
 *            (Employee or Manager) and the role is sent as a header. Permissions
 *            are still enforced per role by the API, but identity is NOT verified.
 *
 *   secure - real sign-in. Bearer token, role read from the user's record.
 *
 * The UI reads which mode is active from the server rather than assuming, so the
 * two never disagree. Permissions always come from the server's own table.
 */

interface AuthContextValue {
  mode: 'demo' | 'secure';
  user: UserProfile | null;
  role: RoleId;
  setRole: (role: RoleId) => void;
  /** Demo mode only: enter the app as a role from the login screen. */
  enterDemo: (role: RoleId) => void;
  roles: RoleDefinition[];
  loading: boolean;
  requiresLogin: boolean;
  can: (permission: PermissionId) => boolean;
  /** Resolves with the signed-in profile so callers can check the account's role. */
  login: (email: string, password: string) => Promise<UserProfile>;
  register: (email: string, fullName: string, password: string) => Promise<UserProfile>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const TOKEN_KEY = 'indusbrain.token';
const ROLE_KEY = 'indusbrain.role';
// Per-tab: closing the tab returns to the login screen, like a real session.
const ENTERED_KEY = 'indusbrain.entered';

/** User-facing name for a role. The backend calls the non-manager role `engineer`. */
export function roleLabel(role: RoleId): string {
  return role === 'manager' ? 'Manager' : 'Employee';
}

function loadEntered(): boolean {
  try {
    return window.sessionStorage.getItem(ENTERED_KEY) === '1';
  } catch {
    return false;
  }
}

function loadStoredRole(): RoleId {
  return window.localStorage.getItem(ROLE_KEY) === 'manager' ? 'manager' : 'engineer';
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mode, setMode] = useState<'demo' | 'secure'>('demo');
  const [user, setUser] = useState<UserProfile | null>(null);
  const [role, setRoleState] = useState<RoleId>(loadStoredRole);
  const [roles, setRoles] = useState<RoleDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [demoEntered, setDemoEntered] = useState(loadEntered);

  // Keep the API client's outgoing role header in step with the selection.
  useEffect(() => {
    setActiveRole(role);
    window.localStorage.setItem(ROLE_KEY, role);
  }, [role]);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      let requiresLogin = false;
      try {
        const bootstrap = await api.bootstrap();
        requiresLogin = bootstrap.requires_login;
        if (!cancelled) setMode(bootstrap.auth_mode);
      } catch {
        // Backend unreachable — fall back to demo so the UI still renders and
        // shows its own connection error rather than a blank login screen.
      }

      try {
        const roleTable = await api.roles();
        if (!cancelled) setRoles(roleTable.roles);
      } catch {
        /* navigation falls back to the least-privileged view */
      }

      // Only attempt to restore a session when the server actually wants one.
      const stored = window.localStorage.getItem(TOKEN_KEY);
      if (requiresLogin && stored) {
        setAuthToken(stored);
        try {
          const profile = await api.me();
          if (!cancelled) {
            setUser(profile);
            setRoleState(profile.role);
          }
        } catch {
          window.localStorage.removeItem(TOKEN_KEY);
          setAuthToken(null);
        }
      }

      if (!cancelled) setLoading(false);
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const applySession = useCallback((token: string, profile: UserProfile) => {
    window.localStorage.setItem(TOKEN_KEY, token);
    setAuthToken(token);
    setUser(profile);
    setRoleState(profile.role);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const result = await api.login(email, password);
      applySession(result.access_token, result.user);
      return result.user;
    },
    [applySession],
  );

  const register = useCallback(
    async (email: string, fullName: string, password: string) => {
      const result = await api.register(email, fullName, password);
      applySession(result.access_token, result.user);
      return result.user;
    },
    [applySession],
  );

  const enterDemo = useCallback((next: RoleId) => {
    setRoleState(next);
    try {
      window.sessionStorage.setItem(ENTERED_KEY, '1');
    } catch {
      /* storage blocked — the user will simply see the login again on refresh */
    }
    setDemoEntered(true);
  }, []);

  const logout = useCallback(async () => {
    // Demo mode has no server session: leaving just returns to the login screen.
    try {
      window.sessionStorage.removeItem(ENTERED_KEY);
    } catch {
      /* ignore */
    }
    setDemoEntered(false);
    if (mode === 'demo') return;
    try {
      await api.logout();
    } catch {
      /* clear locally regardless, so the user is signed out here */
    }
    window.localStorage.removeItem(TOKEN_KEY);
    setAuthToken(null);
    setUser(null);
  }, [mode]);

  // Permissions come from the server's table for whichever role is active.
  const can = useCallback(
    (permission: PermissionId) => {
      if (user) return user.permissions.includes(permission);
      const definition = roles.find((r) => r.id === role);
      return Boolean(definition?.permissions.includes(permission));
    },
    [user, roles, role],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      mode,
      user,
      role: user?.role ?? role,
      setRole: setRoleState,
      enterDemo,
      roles,
      loading,
      requiresLogin: mode === 'secure' ? !user : !demoEntered,
      can,
      login,
      register,
      logout,
    }),
    [mode, user, role, roles, loading, can, login, register, logout, enterDemo, demoEntered],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside an AuthProvider');
  return context;
}
