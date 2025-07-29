'use client';

import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { useRouter } from 'next/navigation';
import { 
  UserInfo, 
  LoginCredentials, 
  AuthResponse, 
  Permission,
  UserProfileUpdateRequest,
  PasswordChangeRequest 
} from '@/types';

interface AuthContextType {
  user: UserInfo | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  updateProfile: (updates: UserProfileUpdateRequest) => Promise<UserInfo>;
  changePassword: (request: PasswordChangeRequest) => Promise<void>;
  hasPermission: (permission: Permission) => boolean;
  hasAnyPermission: (permissions: Permission[]) => boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export function useAuthProvider() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const router = useRouter();

  const isAuthenticated = !!user && !!accessToken;

  // Initialize auth state from localStorage
  useEffect(() => {
    const initAuth = async () => {
      try {
        const storedToken = localStorage.getItem('accessToken');
        const storedUser = localStorage.getItem('user');

        if (storedToken && storedUser) {
          setAccessToken(storedToken);
          setUser(JSON.parse(storedUser));
          
          // Try to refresh the token to ensure it's still valid
          await refreshTokenInternal(storedToken);
        }
      } catch (error) {
        console.error('Auth initialization failed:', error);
        // Clear invalid auth data
        localStorage.removeItem('accessToken');
        localStorage.removeItem('user');
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  // Set up automatic token refresh
  useEffect(() => {
    if (!accessToken) return;

    const refreshInterval = setInterval(async () => {
      try {
        await refreshTokenInternal();
      } catch (error) {
        console.error('Automatic token refresh failed:', error);
        await logout();
      }
    }, 23 * 60 * 60 * 1000); // Refresh every 23 hours

    return () => clearInterval(refreshInterval);
  }, [accessToken]);

  const refreshTokenInternal = async (token?: string) => {
    const currentToken = token || accessToken;
    if (!currentToken) throw new Error('No token available');

    const response = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}), // Refresh token will be read from cookie
    });

    if (!response.ok) {
      throw new Error('Token refresh failed');
    }

    const data: AuthResponse = await response.json();
    
    setAccessToken(data.accessToken);
    setUser(data.user);
    
    // Update localStorage
    localStorage.setItem('accessToken', data.accessToken);
    localStorage.setItem('user', JSON.stringify(data.user));
  };

  const login = async (credentials: LoginCredentials) => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Login failed');
      }

      const data: AuthResponse = await response.json();
      
      setAccessToken(data.accessToken);
      setUser(data.user);
      
      // Store in localStorage
      localStorage.setItem('accessToken', data.accessToken);
      localStorage.setItem('user', JSON.stringify(data.user));
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      // Call logout endpoint to clear server-side session
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      });
    } catch (error) {
      console.error('Logout API call failed:', error);
    } finally {
      // Clear client-side state regardless of API call result
      setAccessToken(null);
      setUser(null);
      localStorage.removeItem('accessToken');
      localStorage.removeItem('user');
      router.push('/login');
    }
  };

  const refreshToken = async () => {
    await refreshTokenInternal();
  };

  const updateProfile = async (updates: UserProfileUpdateRequest): Promise<UserInfo> => {
    if (!accessToken) throw new Error('Not authenticated');

    const response = await fetch('/api/auth/profile', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
      body: JSON.stringify(updates),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Profile update failed');
    }

    const updatedUser: UserInfo = await response.json();
    setUser(updatedUser);
    localStorage.setItem('user', JSON.stringify(updatedUser));
    
    return updatedUser;
  };

  const changePassword = async (request: PasswordChangeRequest) => {
    if (!accessToken) throw new Error('Not authenticated');

    const response = await fetch('/api/auth/profile', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Password change failed');
    }
  };

  const hasPermission = useCallback((permission: Permission): boolean => {
    return user?.permissions.includes(permission) ?? false;
  }, [user]);

  const hasAnyPermission = useCallback((permissions: Permission[]): boolean => {
    return permissions.some(permission => hasPermission(permission));
  }, [hasPermission]);

  return {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
    refreshToken,
    updateProfile,
    changePassword,
    hasPermission,
    hasAnyPermission,
  };
}

export { AuthContext };