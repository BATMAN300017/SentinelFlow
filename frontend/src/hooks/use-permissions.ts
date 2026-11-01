'use client';

import { useState, useEffect } from 'react';
import { getCurrentUser, setCurrentRole, UserSession, UserRole } from '@/lib/auth';
import { getPermissionsForRole, RolePermissions } from '@/lib/permissions';

export function usePermissions() {
  const [user, setUser] = useState<UserSession>(() => getCurrentUser());
  const [permissions, setPermissions] = useState<RolePermissions>(() =>
    getPermissionsForRole(user.role)
  );

  useEffect(() => {
    function handleAuthChange() {
      const updatedUser = getCurrentUser();
      setUser(updatedUser);
      setPermissions(getPermissionsForRole(updatedUser.role));
    }

    window.addEventListener('sentinel-auth-changed', handleAuthChange);
    return () => window.removeEventListener('sentinel-auth-changed', handleAuthChange);
  }, []);

  const switchRole = (newRole: UserRole) => {
    const updated = setCurrentRole(newRole);
    setUser(updated);
    setPermissions(getPermissionsForRole(updated.role));
  };

  return {
    user,
    role: user.role,
    permissions,
    switchRole,
    canManageRules: permissions.canManageRules,
    canSubmitDisposition: permissions.canSubmitDisposition,
    canApproveDisposition: permissions.canApproveDisposition,
    isReadOnly: permissions.isReadOnly,
  };
}
