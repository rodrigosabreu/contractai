'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { api } from '@/lib/api';
import { UserResponse } from '@/lib/types';

interface AuthContextType {
  user: UserResponse | null;
  loading: boolean;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  logout: () => Promise<void>;
  register: (email: string, password: string, fullName: string, organizationName: string, organizationSlug: string) => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = async () => {
    try {
      const userData = await api.getCurrentUser();
      setUser(userData);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  const login = async (email: string, password: string, rememberMe = false) => {
    const result = await api.login(email, password, rememberMe);
    setUser(result.user);
  };

  const register = async (email: string, password: string, fullName: string, organizationName: string, organizationSlug: string) => {
    const result = await api.register({ email, password, full_name: fullName, organization_name: organizationName, organization_slug: organizationSlug });
    setUser(result.user);
  };

  const logout = async () => {
    try { await api.logout(); } finally { setUser(null); }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}