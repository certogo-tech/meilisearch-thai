import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { findUserById, getUserInfo } from '@/lib/auth-db';
import { signToken, verifyRefreshToken } from '@/lib/jwt';
import { AuthResponse } from '@/types';

const refreshSchema = z.object({
  refreshToken: z.string().optional(),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { refreshToken: bodyRefreshToken } = refreshSchema.parse(body);
    
    // Get refresh token from body or cookie
    const refreshToken = bodyRefreshToken || request.cookies.get('refreshToken')?.value;
    
    if (!refreshToken) {
      return NextResponse.json(
        { error: 'Refresh token not provided' },
        { status: 401 }
      );
    }

    // Verify refresh token
    const { sub: userId } = await verifyRefreshToken(refreshToken);

    // Find user
    const user = await findUserById(userId);
    if (!user) {
      return NextResponse.json(
        { error: 'User not found' },
        { status: 401 }
      );
    }

    // Generate new access token
    const userInfo = getUserInfo(user);
    const accessToken = await signToken({
      sub: user.id,
      username: user.username,
      email: user.email,
      role: user.role,
      permissions: user.permissions,
    });

    const response: AuthResponse = {
      accessToken,
      refreshToken, // Keep the same refresh token
      user: userInfo,
      expiresIn: 24 * 60 * 60, // 24 hours
    };

    return NextResponse.json(response);
  } catch (error) {
    console.error('Token refresh error:', error);
    
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid input', details: error.errors },
        { status: 400 }
      );
    }

    return NextResponse.json(
      { error: 'Invalid or expired refresh token' },
      { status: 401 }
    );
  }
}