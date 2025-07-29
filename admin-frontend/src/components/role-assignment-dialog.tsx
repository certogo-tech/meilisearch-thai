'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { UserInfo, UserRole, Permission } from '@/types';
import { useAuth } from '@/hooks/use-auth';
import { Settings } from 'lucide-react';

interface RoleAssignmentDialogProps {
  user: UserInfo;
  onRoleUpdate: (userId: string, newRole: UserRole) => Promise<void>;
}

const rolePermissions: Record<UserRole, Permission[]> = {
  [UserRole.ADMIN]: [
    Permission.VIEW_COMPOUNDS,
    Permission.EDIT_COMPOUNDS,
    Permission.DELETE_COMPOUNDS,
    Permission.BULK_OPERATIONS,
    Permission.VIEW_ANALYTICS,
    Permission.SYSTEM_ADMIN,
  ],
  [UserRole.EDITOR]: [
    Permission.VIEW_COMPOUNDS,
    Permission.EDIT_COMPOUNDS,
    Permission.BULK_OPERATIONS,
    Permission.VIEW_ANALYTICS,
  ],
  [UserRole.VIEWER]: [
    Permission.VIEW_COMPOUNDS,
    Permission.VIEW_ANALYTICS,
  ],
};

const roleDescriptions: Record<UserRole, string> = {
  [UserRole.ADMIN]: 'Full system access including user management and system settings',
  [UserRole.EDITOR]: 'Can view, edit, and perform bulk operations on compound words',
  [UserRole.VIEWER]: 'Read-only access to compound words and analytics',
};

export function RoleAssignmentDialog({ user, onRoleUpdate }: RoleAssignmentDialogProps) {
  const [open, setOpen] = useState(false);
  const [selectedRole, setSelectedRole] = useState<UserRole>(user.role);
  const [isLoading, setIsLoading] = useState(false);
  const { hasPermission } = useAuth();

  // Only system admins can assign roles
  if (!hasPermission(Permission.SYSTEM_ADMIN)) {
    return null;
  }

  const handleRoleUpdate = async () => {
    if (selectedRole === user.role) {
      setOpen(false);
      return;
    }

    setIsLoading(true);
    try {
      await onRoleUpdate(user.id, selectedRole);
      setOpen(false);
    } catch (error) {
      console.error('Failed to update user role:', error);
      // Reset to original role on error
      setSelectedRole(user.role);
    } finally {
      setIsLoading(false);
    }
  };

  const selectedPermissions = rolePermissions[selectedRole];

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Settings className="h-4 w-4 mr-2" />
          Manage Role
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Manage User Role</DialogTitle>
          <DialogDescription>
            Update the role and permissions for {user.username} ({user.email})
          </DialogDescription>
        </DialogHeader>
        
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="role">Role</Label>
            <Select
              value={selectedRole}
              onValueChange={(value) => setSelectedRole(value as UserRole)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a role" />
              </SelectTrigger>
              <SelectContent>
                {Object.values(UserRole).map((role) => (
                  <SelectItem key={role} value={role}>
                    <div className="flex flex-col">
                      <span className="font-medium capitalize">{role}</span>
                      <span className="text-xs text-muted-foreground">
                        {roleDescriptions[role]}
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <Label>Permissions</Label>
            <div className="border rounded-md p-3 bg-muted/50">
              <div className="grid gap-1">
                {selectedPermissions.map((permission) => (
                  <div key={permission} className="flex items-center text-sm">
                    <div className="w-2 h-2 bg-green-500 rounded-full mr-2" />
                    <span className="capitalize">
                      {permission.replace(/_/g, ' ')}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {selectedRole !== user.role && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3">
              <p className="text-sm text-yellow-800">
                <strong>Warning:</strong> Changing this user's role will immediately 
                update their permissions and may affect their access to certain features.
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => {
              setSelectedRole(user.role);
              setOpen(false);
            }}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleRoleUpdate}
            disabled={isLoading || selectedRole === user.role}
          >
            {isLoading ? 'Updating...' : 'Update Role'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}