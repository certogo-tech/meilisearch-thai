'use client';

import { ReactNode, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/use-auth';
import { Permission } from '@/types';
import { Loader2 } from 'lucide-react';

interface ProtectedRouteProps {
  children: ReactNode;
  requiredPermissions?: Permission[];
  requireAll?: boolean; // If true, user must have ALL permissions. If false, user needs ANY permission.
  fallbackPath?: string;
}

export function ProtectedRoute({ 
  children, 
  requiredPermissions = [], 
  requireAll = false,
  fallbackPath = '/dashboard'
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user, hasPermission, hasAnyPermission } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    if (requiredPermissions.length > 0) {
      const hasRequiredPermissions = requireAll
        ? requiredPermissions.every(permission => hasPermission(permission))
        : hasAnyPermission(requiredPermissions);

      if (!hasRequiredPermissions) {
        router.push(fallbackPath);
        return;
      }
    }
  }, [isAuthenticated, isLoading, user, requiredPermissions, requireAll, fallbackPath, router, hasPermission, hasAnyPermission]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center space-x-2">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span>Loading...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // Will redirect to login
  }

  if (requiredPermissions.length > 0) {
    const hasRequiredPermissions = requireAll
      ? requiredPermissions.every(permission => hasPermission(permission))
      : hasAnyPermission(requiredPermissions);

    if (!hasRequiredPermissions) {
      return null; // Will redirect to fallback
    }
  }

  return <>{children}</>;
}

interface PermissionGateProps {
  children: ReactNode;
  requiredPermissions: Permission[];
  requireAll?: boolean;
  fallback?: ReactNode;
}

export function PermissionGate({ 
  children, 
  requiredPermissions, 
  requireAll = false,
  fallback = null 
}: PermissionGateProps) {
  const { hasPermission, hasAnyPermission } = useAuth();

  const hasRequiredPermissions = requireAll
    ? requiredPermissions.every(permission => hasPermission(permission))
    : hasAnyPermission(requiredPermissions);

  if (!hasRequiredPermissions) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}