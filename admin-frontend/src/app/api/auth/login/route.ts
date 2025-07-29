import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { findUserByUsername, validatePassword, updateUserLastLogin, getUserInfo } from '@/lib/auth-db';
import { signToken, signRefreshToken } from '@/lib/jwt';
import { createAuditLog, getClientInfo } from '@/lib/audit-logger';
import { AuthResponse, AuditAction } from '@/types';

const loginSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
  rememberMe: z.boolean().optional(),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { username, password, rememberMe } = loginSchema.parse(body);

    // Find user by username
    const user = await findUserByUsername(username);
    if (!user) {
      return NextResponse.json(
        { error: 'Invalid username or password' },
        { status: 401 }
      );
    }

    // Validate password
    const isPasswordValid = await validatePassword(password, user.passwordHash);
    if (!isPasswordValid) {
      return NextResponse.json(
        { error: 'Invalid username or password' },
        { status: 401 }
      );
    }

    // Update last login
    await updateUserLastLogin(user.id);

    // Generate tokens
    const userInfo = getUserInfo(user);
    const accessToken = await signToken({
      sub: user.id,
      username: user.username,
      email: user.email,
      role: user.role,
      permissions: user.permissions,
    });

    const refreshToken = await signRefreshToken(user.id);

    // Create audit log for successful login
    const { ipAddress, userAgent } = getClientInfo(request);
    await createAuditLog({
      userId: user.id,
      username: user.username,
      action: AuditAction.LOGIN,
      resource: 'auth',
      details: {
        rememberMe,
        loginMethod: 'password',
      },
      ipAddress,
      userAgent,
    });

    const response: AuthResponse = {
      accessToken,
      refreshToken,
      user: userInfo,
      expiresIn: 24 * 60 * 60, // 24 hours
    };

    // Set HTTP-only cookie for refresh token if rememberMe is true
    const nextResponse = NextResponse.json(response);
    
    if (rememberMe) {
      nextResponse.cookies.set('refreshToken', refreshToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
        maxAge: 7 * 24 * 60 * 60, // 7 days
        path: '/',
      });
    }

    return nextResponse;
  } catch (error) {
    console.error('Login error:', error);
    
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