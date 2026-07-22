import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../lib/AuthContext';
import type { PermissionId } from '../lib/types';
import { Button, Card, EmptyState } from './ui/primitives';
import { IconShield } from './ui/icons';

/**
 * Route guard.
 *
 * Hiding a link is a usability choice, not a security control — a user can still
 * type the URL. This renders an explicit, explained refusal for those cases.
 * The API independently rejects the underlying calls, so this layer exists to
 * give a clear reason rather than a confusing empty screen.
 */
export const RequirePermission: React.FC<{
  permission: PermissionId;
  children: React.ReactNode;
  area: string;
}> = ({ permission, children, area }) => {
  const { can, user, loading } = useAuth();

  if (loading) return null;
  if (can(permission)) return <>{children}</>;

  return (
    <div className="mx-auto w-full max-w-[1400px] px-5 py-6 sm:px-7 sm:py-8">
      <Card>
        <EmptyState
          icon={<IconShield size={30} />}
          title={`${area} requires the manager role`}
          description={`You are signed in as ${user?.full_name ?? 'an engineer'} (${user?.role ?? 'engineer'}). This area changes the shared document corpus, so it is restricted to managers. Ask a manager to upgrade your account if you need access.`}
          action={
            <Link to="/">
              <Button variant="primary">Back to overview</Button>
            </Link>
          }
        />
      </Card>
    </div>
  );
};
