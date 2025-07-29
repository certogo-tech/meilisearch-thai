import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { findUserById, updateUserProfile, changeUserPassword, getUserInfo } from '@/lib/auth-db';
import { verifyToken } from '@/lib/jwt';
import { createAuditLog, getClientInfo } from '@/lib/audit-logger';
import { AuditAction } from '@/types';

const profileUpdateSchema = z.object({
  email: z.string().email().optional(),
  username: z.string().min(1).optional(),
});

const passwordChangeSchema = z.object({
  currentPassword: z.string().min(1, 'Current password is required'),
  newPassword: z.string().min(6, 'New password must be at least 6 characters'),
  confirmPassword: z.string().min(1, 'Password confirmation is required'),
}).refine((data) => data.newPassword === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

async function getUserFromToken(request: NextRequest) {
  const authHeader = request.headers.get('authorization');
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    throw new Error('No authorization token provided');
  }

  const token = authHeader.substring(7);
  const payload = await verifyToken(token);
  const user = await findUserById(payload.sub);
  
  if (!user) {
    throw new Error('User not found');
  }

  return user;
}

export async function GET(request: NextRequest) {
  try {
    const user = await getUserFromToken(request);
    return NextResponse.json(getUserInfo(user));
  } catch (error) {
    console.error('Get profile error:', error);
    return NextResponse.json(
      { error: 'Unauthorized' },
      { status: 401 }
    );
  }
}

export async function PUT(request: NextRequest) {
  try {
    const user = await getUserFromToken(request);
    const body = await request.json();
    const updates = profileUpdateSchema.parse(body);

    const updatedUser = await updateUserProfile(user.id, updates);
    if (!updatedUser) {
      return NextResponse.json(
        { error: 'Failed to update profile' },
        { status: 500 }
      );
    }

    // Create audit log for profile update
    const { ipAddress, userAgent } = getClientInfo(request);
    await createAuditLog({
      userId: user.id,
      username: user.username,
      action: AuditAction.PROFILE_UPDATE,
      resource: 'user',
      resourceId: user.id,
      details: {
        updatedFields: Object.keys(updates),
        changes: updates,
      },
      ipAddress,
      userAgent,
    });

    return NextResponse.json(updatedUser);
  } catch (error) {
    console.error('Update profile error:', error);
    
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid input', details: error.errors },
        { status: 400 }
      );
    }

    return NextResponse.json(
      { error: 'Unauthorized' },
      { status: 401 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const user = await getUserFromToken(request);
    const body = await request.json();
    const { currentPassword, newPassword } = passwordChangeSchema.parse(body);

    const success = await changeUserPassword(user.id, currentPassword, newPassword);
    if (!success) {
      return NextResponse.json(
        { error: 'Current password is incorrect' },
        { status: 400 }
      );
    }

    // Create audit log for password change
    const { ipAddress, userAgent } = getClientInfo(request);
    await createAuditLog({
      userId: user.id,
      username: user.username,
      action: AuditAction.PASSWORD_CHANGE,
      resource: 'user',
      resourceId: user.id,
      details: {
        changeMethod: 'self-service',
      },
      ipAddress,
      userAgent,
    });

    return NextResponse.json({ message: 'Password changed successfully' });
  } catch (error) {
    console.error('Change password error:', error);
    
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid input', details: error.errors },
        { status: 400 }
      );
    }

    // Handle password validation errors
    if (error instanceof Error && error.message.startsWith('Password validation failed:')) {
      return NextResponse.json(
        { error: error.message },
        { status: 400 }
      );
    }

    return NextResponse.json(
      { error: 'Unauthorized' },
      { status: 401 }
    );
  }
}