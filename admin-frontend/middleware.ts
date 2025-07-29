import { NextRequest, NextResponse } from 'next/server';
import { verifyToken } from '@/lib/jwt';
import { Permission } from '@/types';

// Define protected routes and their required permissions
const protectedRoutes: Record<string, Permission[]> = {
  '/dashboard': [Permission.VIEW_COMPOUNDS],
  '/dictionary': [Permission.VIEW_COMPOUNDS],
  '/test': [Permission.VIEW_COMPOUNDS],
  '/analytics': [Permission.VIEW_ANALYTICS],
  '/import-export': [Permission.BULK_OPERATIONS],
  '/settings': [Permission.SYSTEM_ADMIN],
  '/admin': [Permission.SYSTEM_ADMIN],
};

// Routes that don't require authentication
const publicRoutes = ['/login', '/api/auth/login'];

// API routes that don't require authentication
const publicApiRoutes = ['/api/auth/login', '/api/auth/refresh'];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public routes
  if (publicRoutes.includes(pathname) || publicApiRoutes.includes(pathname)) {
    return NextResponse.next();
  }

  // Allow static files and Next.js internals
  if (
    pathname.startsWith('/_next/') ||
    pathname.startsWith('/favicon.ico') ||
    pathname.startsWith('/api/health')
  ) {
    return NextResponse.next();
  }

  // Get token from Authorization header or cookie
  let token: string | undefined;
  
  const authHeader = request.headers.get('authorization');
  if (authHeader && authHeader.startsWith('Bearer ')) {
    token = authHeader.substring(7);
  } else {
    // For page requests, try to get token from cookie (if set by client-side)
    token = request.cookies.get('accessToken')?.value;
  }

  if (!token) {
    // Redirect to login for page requests
    if (!pathname.startsWith('/api/')) {
      const loginUrl = new URL('/login', request.url);
      loginUrl.searchParams.set('redirect', pathname);
      return NextResponse.redirect(loginUrl);
    }
    
    // Return 401 for API requests
    return NextResponse.json(
      { error: 'Authentication required' },
      { status: 401 }
    );
  }

  try {
    // Verify token
    const payload = await verifyToken(token);
    
    // Check if route requires specific permissions
    const requiredPermissions = protectedRoutes[pathname];
    if (requiredPermissions) {
      const hasPermission = requiredPermissions.some(permission =>
        payload.permissions.includes(permission)
      );
      
      if (!hasPermission) {
        // Redirect to dashboard for page requests
        if (!pathname.startsWith('/api/')) {
          return NextResponse.redirect(new URL('/dashboard', request.url));
        }
        
        // Return 403 for API requests
        return NextResponse.json(
          { error: 'Insufficient permissions' },
          { status: 403 }
        );
      }
    }

    // Add user info to request headers for API routes
    if (pathname.startsWith('/api/')) {
      const requestHeaders = new Headers(request.headers);
      requestHeaders.set('x-user-id', payload.sub);
      requestHeaders.set('x-user-role', payload.role);
      requestHeaders.set('x-user-permissions', JSON.stringify(payload.permissions));
      
      return NextResponse.next({
        request: {
          headers: requestHeaders,
        },
      });
    }

    return NextResponse.next();
  } catch (error) {
    console.error('Token verification failed:', error);
    
    // Redirect to login for page requests
    if (!pathname.startsWith('/api/')) {
      const loginUrl = new URL('/login', request.url);
      loginUrl.searchParams.set('redirect', pathname);
      return NextResponse.redirect(loginUrl);
    }
    
    // Return 401 for API requests
    return NextResponse.json(
      { error: 'Invalid or expired token' },
      { status: 401 }
    );
  }
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};