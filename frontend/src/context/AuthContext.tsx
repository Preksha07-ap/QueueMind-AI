import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import type { LoginCredentials, RegisterCredentials, User, UserRole } from '../types';
import { authService } from '../services/authService';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<User>;
  platformLogin: (credentials: { email: string; password: string }) => Promise<User>;
  register: (credentials: RegisterCredentials) => Promise<User>;
  logout: () => Promise<void>;
  getRoleDashboardPath: (role?: UserRole) => string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const getRoleDashboardPath = (role?: UserRole): string => {
  switch (role) {
    case 'USER':
      return '/dashboard/user';
    case 'HELP_DESK':
      return '/dashboard/helpdesk';
    case 'SUPPORT_TEAM_MEMBER':
      return '/dashboard/support';
    case 'SUPPORT_TEAM_LEAD':
      return '/dashboard/team-lead';
    case 'ORGANIZATION_ADMIN':
      return '/dashboard/org-admin';
    case 'PLATFORM_OWNER':
      return '/dashboard/platform-owner';
    default:
      return '/dashboard/user';
  }
};

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const savedUser = localStorage.getItem('qm_user');
    if (savedUser) {
      try {
        return JSON.parse(savedUser);
      } catch {
        return null;
      }
    }
    return null;
  });

  const [token, setToken] = useState<string | null>(() => localStorage.getItem('qm_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initialize and verify session on load
  useEffect(() => {
    const initAuth = async () => {
      const savedToken = localStorage.getItem('qm_token');
      if (savedToken) {
        try {
          const freshUser = await authService.getMe();
          setUser(freshUser);
          localStorage.setItem('qm_user', JSON.stringify(freshUser));
        } catch {
          // Token is invalid or expired
          localStorage.removeItem('qm_token');
          localStorage.removeItem('qm_user');
          setToken(null);
          setUser(null);
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (credentials: LoginCredentials): Promise<User> => {
    setIsLoading(true);
    try {
      const result = await authService.login(credentials);
      localStorage.setItem('qm_token', result.access_token);
      localStorage.setItem('qm_user', JSON.stringify(result.user));
      setToken(result.access_token);
      setUser(result.user);
      return result.user;
    } finally {
      setIsLoading(false);
    }
  };

  const platformLogin = async (credentials: { email: string; password: string }): Promise<User> => {
    setIsLoading(true);
    try {
      const result = await authService.platformLogin(credentials);
      localStorage.setItem('qm_token', result.access_token);
      localStorage.setItem('qm_user', JSON.stringify(result.user));
      setToken(result.access_token);
      setUser(result.user);
      return result.user;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (credentials: RegisterCredentials): Promise<User> => {
    setIsLoading(true);
    try {
      const newUser = await authService.register(credentials);
      return newUser;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    setIsLoading(true);
    try {
      await authService.logout();
    } finally {
      setUser(null);
      setToken(null);
      setIsLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        login,
        platformLogin,
        register,
        logout,
        getRoleDashboardPath,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
