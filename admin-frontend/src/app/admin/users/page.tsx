'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ProtectedRoute } from '@/components/protected-route';
import { DashboardLayout } from '@/components/dashboard-layout';
import { RoleAssignmentDialog } from '@/components/role-assignment-dialog';
import { useAuth } from '@/hooks/use-auth';
import { UserInfo, UserRole, Permission } from '@/types';
import { Search, Users, Shield, Eye, Edit } from 'lucide-react';

// Mock users data - in production, this would come from an API
const mockUsers: UserInfo[] = [
  {
    id: '1',
    username: 'admin',
    email: 'admin@example.com',
    role: UserRole.ADMIN,
    permissions: [
      Permission.VIEW_COMPOUNDS,
      Permission.EDIT_COMPOUNDS,
      Permission.DELETE_COMPOUNDS,
      Permission.BULK_OPERATIONS,
      Permission.VIEW_ANALYTICS,
      Permission.SYSTEM_ADMIN,
    ],
    lastLogin: new Date('2025-01-28T10:30:00Z'),
  },
  {
    id: '2',
    username: 'editor',
    email: 'editor@example.com',
    role: UserRole.EDITOR,
    permissions: [
      Permission.VIEW_COMPOUNDS,
      Permission.EDIT_COMPOUNDS,
      Permission.BULK_OPERATIONS,
      Permission.VIEW_ANALYTICS,
    ],
    lastLogin: new Date('2025-01-27T15:45:00Z'),
  },
  {
    id: '3',
    username: 'viewer',
    email: 'viewer@example.com',
    role: UserRole.VIEWER,
    permissions: [
      Permission.VIEW_COMPOUNDS,
      Permission.VIEW_ANALYTICS,
    ],
    lastLogin: new Date('2025-01-26T09:15:00Z'),
  },
];

const roleIcons = {
  [UserRole.ADMIN]: Shield,
  [UserRole.EDITOR]: Edit,
  [UserRole.VIEWER]: Eye,
};

const roleColors = {
  [UserRole.ADMIN]: 'bg-red-100 text-red-800 border-red-200',
  [UserRole.EDITOR]: 'bg-blue-100 text-blue-800 border-blue-200',
  [UserRole.VIEWER]: 'bg-green-100 text-green-800 border-green-200',
};

export default function UsersPage() {
  const [users, setUsers] = useState<UserInfo[]>(mockUsers);
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredUsers, setFilteredUsers] = useState<UserInfo[]>(mockUsers);
  const { user: currentUser } = useAuth();

  useEffect(() => {
    const filtered = users.filter(
      (user) =>
        user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.role.toLowerCase().includes(searchTerm.toLowerCase())
    );
    setFilteredUsers(filtered);
  }, [users, searchTerm]);

  const handleRoleUpdate = async (userId: string, newRole: UserRole) => {
    try {
      // In production, this would make an API call
      const response = await fetch(`/api/users/${userId}/role`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
        },
        body: JSON.stringify({ role: newRole }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to update role');
      }

      const { user: updatedUser } = await response.json();

      // Update local state
      setUsers(prevUsers =>
        prevUsers.map(user =>
          user.id === userId ? updatedUser : user
        )
      );

      console.log(`Role updated successfully for user ${userId}`);
    } catch (error) {
      console.error('Failed to update user role:', error);
      throw error;
    }
  };

  const formatLastLogin = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  return (
    <ProtectedRoute requiredPermissions={[Permission.SYSTEM_ADMIN]}>
      <DashboardLayout>
        <div>
        <div className="mb-8">
          <h1 className="text-4xl font-bold tracking-tight">User Management</h1>
          <p className="text-muted-foreground">
            Manage user roles and permissions
          </p>
        </div>

        <div className="mb-6">
          <div className="flex items-center space-x-2">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
              <Input
                placeholder="Search users..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="flex items-center space-x-2 text-sm text-muted-foreground">
              <Users className="h-4 w-4" />
              <span>{filteredUsers.length} users</span>
            </div>
          </div>
        </div>

        <div className="grid gap-4">
          {filteredUsers.map((user) => {
            const RoleIcon = roleIcons[user.role];
            const isCurrentUser = currentUser?.id === user.id;

            return (
              <Card key={user.id} className={isCurrentUser ? 'ring-2 ring-blue-200' : ''}>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="w-12 h-12 bg-muted rounded-full flex items-center justify-center">
                        <span className="text-lg font-semibold">
                          {user.username.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <h3 className="font-semibold">{user.username}</h3>
                          {isCurrentUser && (
                            <Badge variant="outline" className="text-xs">
                              You
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">{user.email}</p>
                        <p className="text-xs text-muted-foreground">
                          Last login: {formatLastLogin(user.lastLogin)}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-4">
                      <div className="text-right space-y-2">
                        <div className="flex items-center space-x-2">
                          <RoleIcon className="h-4 w-4" />
                          <Badge className={roleColors[user.role]}>
                            {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {user.permissions.length} permissions
                        </p>
                      </div>

                      {!isCurrentUser && (
                        <RoleAssignmentDialog
                          user={user}
                          onRoleUpdate={handleRoleUpdate}
                        />
                      )}
                    </div>
                  </div>

                  <div className="mt-4 pt-4 border-t">
                    <div className="flex flex-wrap gap-1">
                      {user.permissions.slice(0, 4).map((permission) => (
                        <Badge key={permission} variant="secondary" className="text-xs">
                          {permission.replace(/_/g, ' ')}
                        </Badge>
                      ))}
                      {user.permissions.length > 4 && (
                        <Badge variant="secondary" className="text-xs">
                          +{user.permissions.length - 4} more
                        </Badge>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {filteredUsers.length === 0 && (
          <Card>
            <CardContent className="p-12 text-center">
              <Users className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No users found</h3>
              <p className="text-muted-foreground">
                Try adjusting your search criteria
              </p>
            </CardContent>
          </Card>
        )}
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  );
}