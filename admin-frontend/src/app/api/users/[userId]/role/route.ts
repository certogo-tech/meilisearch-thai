import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { verifyToken } from '@/lib/jwt';
import { findUserById, getUserInfo } from '@/lib/auth-db';
import { createAuditLog, getClientInfo } from '@/lib/audit-logger';
import { UserRole, AuditAction, Permission } from '@/types';

const roleUpdateSchema = z.object({
  role: z.nativeEnum(UserRole),
});

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ userId: string }> }
) {
  try {
    // Verify authentication
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      );
    }

    const token = authHeader.substring(7);
    const adminPayload = await verifyToken(token);

    // Check if user has system admin permission
    if (!adminPayload.permissions.includes(Permission.SYSTEM_ADMIN)) {
      return NextResponse.json(
        { error: 'Insufficient permissions' },
        { status: 403 }
      );
    }

    const { userId } = await context.params;
    const body = await request.json();
    const { role } = roleUpdateSchema.parse(body);

    // Find the target user
    const targetUser = await findUserById(userId);
    if (!targetUser) {
      return NextResponse.json(
        { error: 'User not found' },
        { status: 404 }
      );
    }

    // Prevent self-role modification for safety
    if (adminPayload.sub === userId) {
      return NextResponse.json(
        { error: 'Cannot modify your own role' },
        { status: 400 }
      );
    }

    const oldRole = targetUser.role;
    
    // Update user role (in a real app, this would update the database)
    targetUser.role = role;
    
    // Update permissions based on role
    const rolePermissions = {
      [UserRole.ADMIN]: [
        'view_compounds',
        'edit_compounds',
        'delete_compounds',
        'bulk_operations',
        'view_analytics',
        'system_admin',
      ],
      [UserRole.EDITOR]: [
        'view_compounds',
        'edit_compounds',
        'bulk_operations',
        'view_analytics',
      ],
      [UserRole.VIEWER]: [
        'view_compounds',
        'view_analytics',
      ],
    };
    
    targetUser.permissions = rolePermissions[role] as any[];

    // Create audit log
    const { ipAddress, userAgent } = getClientInfo(request);
    await createAuditLog({
      userId: adminPayload.sub,
      username: adminPayload.username,
      action: AuditAction.ROLE_ASSIGNMENT,
      resource: 'user',
      resourceId: userId,
      details: {
        targetUserId: userId,
        targetUsername: targetUser.username,
        oldRole,
        newRole: role,
        oldPermissions: rolePermissions[oldRole as UserRole],
        newPermissions: rolePermissions[role],
      },
      ipAddress,
      userAgent,
    });

    const updatedUserInfo = getUserInfo(targetUser);

    return NextResponse.json({
      message: 'User role updated successfully',
      user: updatedUserInfo,
    });
  } catch (error) {
    console.error('Role update error:', error);
    
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid input', details: error.errors },
        { status: 400 }
      );
    }

    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}