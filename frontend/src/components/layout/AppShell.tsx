'use client';

import React from 'react';
import { useAuth } from '@/lib/auth';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

export function AppShell({ children }: { children: React.ReactNode }) {
  const { scope, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center">
        <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="mt-3 text-xs text-slate-500 font-medium">Loading session...</p>
      </div>
    );
  }

  if (!scope) {
    return null; // Will redirect in AuthProvider
  }

  return (
    <div className="flex h-screen bg-slate-100 overflow-hidden text-slate-900 antialiased font-sans">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-y-auto p-6 md:p-8 bg-slate-50">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
