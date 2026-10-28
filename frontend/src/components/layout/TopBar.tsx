'use client';

import React from 'react';
import { useAuth } from '@/lib/auth';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { LogOut, User as UserIcon, Building, MapPin } from 'lucide-react';

export function TopBar() {
  const { scope, logout } = useAuth();

  if (!scope) return null;

  const roleLabelMap: Record<string, string> = {
    ADMIN: 'System Admin',
    REGIONAL_HEAD: 'Regional Head',
    SCRUTINY_OFFICER: 'Scrutiny Officer',
    EVC_COORDINATOR: 'EVC Coordinator',
    COMPETENT_AUTHORITY: 'Competent Authority',
    INSTITUTION_USER: 'Institution User',
  };

  const roleBadgeVariant: Record<string, 'neutral' | 'info' | 'success' | 'warning' | 'danger'> = {
    ADMIN: 'neutral',
    REGIONAL_HEAD: 'info',
    SCRUTINY_OFFICER: 'info',
    EVC_COORDINATOR: 'warning',
    COMPETENT_AUTHORITY: 'success',
    INSTITUTION_USER: 'neutral',
  };

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-3">
        <h1 className="text-base font-semibold text-slate-800">
          All India Council for Technical Education
        </h1>
        <span className="text-slate-300">|</span>
        <span className="text-xs text-slate-500 font-medium">Compliance & Workflow Portal</span>
      </div>

      <div className="flex items-center gap-4">
        {/* Region or Institution indicator */}
        {scope.region_name && (
          <div className="hidden md:flex items-center gap-1.5 text-xs text-slate-600 bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200">
            <MapPin className="w-3.5 h-3.5 text-slate-500" />
            <span className="font-medium">{scope.region_name}</span>
          </div>
        )}

        {scope.institution_name && (
          <div className="hidden md:flex items-center gap-1.5 text-xs text-slate-600 bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200">
            <Building className="w-3.5 h-3.5 text-slate-500" />
            <span className="font-medium max-w-xs truncate">{scope.institution_name}</span>
          </div>
        )}

        {/* User Info & Role Badge */}
        <div className="flex items-center gap-2">
          <Badge variant={roleBadgeVariant[scope.role] || 'neutral'}>
            {roleLabelMap[scope.role] || scope.role}
          </Badge>
          <span className="text-xs font-semibold text-slate-800 hidden sm:inline">
            {scope.full_name}
          </span>
        </div>

        {/* Logout */}
        <Button
          variant="ghost"
          size="sm"
          onClick={logout}
          className="text-slate-600 hover:text-red-700 hover:bg-red-50 flex items-center gap-1.5"
          title="Sign out"
        >
          <LogOut className="w-4 h-4" />
          <span className="hidden sm:inline text-xs">Logout</span>
        </Button>
      </div>
    </header>
  );
}
