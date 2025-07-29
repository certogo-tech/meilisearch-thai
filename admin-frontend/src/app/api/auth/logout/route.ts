import { NextRequest, NextResponse } from 'next/server';
import { verifyToken } from '@/lib/jwt';
import { createAuditLog, getClientInfo } from '@/lib/audit-logger';
import { AuditAction } from '@/types';

export async function POST(request: NextRequest) {
  try {
    // Try to get user info for audit logging
    let userId = 'unknown';
    let username = 'unknown';
    
    try {
      const authHeader = request.headers.get('authorization');
      if (authHeader && authHeader.startsWith('Bearer ')) {
        const token = authHeader.substring(7);
        const payload = await verifyToken(token);
        userId = payload.sub;
        username = payload.username;
      }
    } catch {
      // Ignore token verification errors for logout
    }

    // Create audit log for logout
    const { ipAddress, userAgent } = getClientInfo(request);
    await createAuditLog({
      userId,
      username,
      action: AuditAction.LOGOUT,
      resource: 'auth',
      details: {
        logoutMethod: 'manual',
      },
      ipAddress,
      userAgent,
    });

    const response = NextResponse.json({ message: 'Logged out successfully' });
    
    // Clear the refresh token cookie
    response.cookies.set('refreshToken', '', {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 0,
      path: '/',
    });

    return response;
  } catch (error) {
    console.error('Logout error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}