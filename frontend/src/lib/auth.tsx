'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { authApi, lookupApi, TokenResponse, UserScope } from './api';

interface AuthContextType {
  token: string | null;
  scope: UserScope | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  demoLogin: (role: string, email?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [scope, setScope] = useState<UserScope | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const savedToken = localStorage.getItem('aicte_token');
    if (savedToken) {
      setToken(savedToken);
      fetchScope();
    } else {
      setLoading(false);
      if (pathname !== '/login') {
        router.push('/login');
      }
    }
  }, []);

  const fetchScope = async () => {
    try {
      setLoading(true);
      const userScope = await lookupApi.getScope();
      setScope(userScope);
    } catch (err) {
      console.error('Failed to load user scope, session expired', err);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    const data: TokenResponse = await authApi.login(email, password);
    handleAuthSuccess(data);
  };

  const demoLogin = async (role: string, email?: string) => {
    const data: TokenResponse = await authApi.demoLogin(role, email);
    handleAuthSuccess(data);
  };

  const handleAuthSuccess = async (data: TokenResponse) => {
    localStorage.setItem('aicte_token', data.access_token);
    setToken(data.access_token);
    try {
      const userScope = await lookupApi.getScope();
      setScope(userScope);
      if (userScope.is_institution) {
        router.push('/portal');
      } else if (userScope.role === 'COMMITTEE_MEMBER') {
        router.push('/committee/my-cases');
      } else {
        router.push('/');
      }
    } catch (e) {
      router.push('/');
    }
  };

  const logout = () => {
    localStorage.removeItem('aicte_token');
    setToken(null);
    setScope(null);
    authApi.logout().catch(() => {});
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ token, scope, loading, login, demoLogin, logout }}>
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
