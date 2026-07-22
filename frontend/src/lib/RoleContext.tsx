import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, setActiveRole } from './api';
import type { PermissionId, RoleDefinition, RoleId } from './types';

/**
 * Role state for the whole application.
 *
 * The permission table is fetched from the backend rather than duplicated here,
 * so the UI can never drift out of sync with what the server actually enforces.
 * Hiding a control the API would reject — or showing one it would allow — is the
 * usual way RBAC goes wrong.
 */

interface RoleContextValue {
  role: RoleId;
  setRole: (role: RoleId) => void;
  roles: RoleDefinition[];
  can: (permission: PermissionId) => boolean;
  authNotice: string | null;
  loading: boolean;
}

const RoleContext = createContext<RoleContextValue | null>(null);

const STORAGE_KEY = 'indusbrain.role';

function loadStoredRole(): RoleId {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return stored === 'manager' ? 'manager' : 'engineer';
}

export const RoleProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [role, setRoleState] = useState<RoleId>(loadStoredRole);
  const [roles, setRoles] = useState<RoleDefinition[]>([]);
  const [authNotice, setAuthNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Keep the API client's outgoing header in step with the selected role.
  useEffect(() => {
    setActiveRole(role);
    window.localStorage.setItem(STORAGE_KEY, role);
  }, [role]);

  useEffect(() => {
    let cancelled = false;
    api
      .roles()
      .then((response) => {
        if (cancelled) return;
        setRoles(response.roles);
        setAuthNotice(response.authentication_implemented ? null : response.notice);
      })
      .catch(() => undefined)
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const can = useCallback(
    (permission: PermissionId) => {
      const definition = roles.find((r) => r.id === role);
      // Before the role table loads, deny write permissions rather than briefly
      // showing controls that would fail.
      if (!definition) return false;
      return definition.permissions.includes(permission);
    },
    [roles, role],
  );

  const value = useMemo<RoleContextValue>(
    () => ({ role, setRole: setRoleState, roles, can, authNotice, loading }),
    [role, roles, can, authNotice, loading],
  );

  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>;
};

export function useRole(): RoleContextValue {
  const context = useContext(RoleContext);
  if (!context) throw new Error('useRole must be used inside a RoleProvider');
  return context;
}
