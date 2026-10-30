'use client';

import React from 'react';
import Link from 'next/navigation';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import {
  LayoutDashboard,
  FileText,
  CalendarCheck2,
  ClipboardList,
  ShieldCheck,
  Sliders,
  BarChart3,
  Building2,
  AlertTriangle,
  Network,
  Mail,
  Bell,
  History,
  Archive,
  Radio,
  Compass
} from 'lucide-react';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const ALL_NAV_ITEMS: NavItem[] = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Applications', href: '/applications', icon: FileText },
  { name: 'Alerts', href: '/alerts', icon: AlertTriangle },
  { name: 'Escalation Matrix', href: '/escalation-matrix', icon: Network },
  { name: 'Notifications', href: '/notifications', icon: Bell },
  { name: 'Email Outbox', href: '/admin/outbox', icon: Mail },
  { name: 'EVC Queue', href: '/evc-queue', icon: CalendarCheck2 },
  { name: 'Undertakings', href: '/undertakings', icon: ClipboardList },
  { name: 'Document Validity', href: '/document-validity', icon: ShieldCheck },
  { name: 'Bottlenecks', href: '/bottlenecks', icon: Network },
  { name: 'What-If Planner', href: '/planner', icon: Sliders },
  { name: 'APH & Escalation Rules', href: '/settings/rules', icon: Sliders },
  { name: 'Reports', href: '/reports', icon: BarChart3 },
  { name: 'Audit Trail', href: '/admin/audit', icon: History },
  { name: 'Data Retention', href: '/admin/retention', icon: Archive },
  { name: 'AICTE Integration', href: '/integration', icon: Radio },
];

const INSTITUTION_NAV_ITEMS: NavItem[] = [
  { name: 'My Applications', href: '/portal', icon: FileText },
  { name: 'Undertakings', href: '/portal/undertakings', icon: ClipboardList },
  { name: 'Document Validity', href: '/portal/documents', icon: ShieldCheck },
];

const COMMITTEE_NAV_ITEMS: NavItem[] = [
  { name: 'My Committee Cases', href: '/committee/my-cases', icon: ClipboardList },
];

export function Sidebar({ onNavigate }: { onNavigate?: () => void } = {}) {
  const { scope } = useAuth();
  const pathname = usePathname();

  if (!scope) return null;

  // Institution users see dedicated portal menu
  let navItems: NavItem[] = [];
  if (scope.is_institution) {
    navItems = INSTITUTION_NAV_ITEMS;
  } else if (scope.role === 'COMMITTEE_MEMBER') {
    navItems = COMMITTEE_NAV_ITEMS;
  } else {
    // Filter based on allowed_screens
    navItems = ALL_NAV_ITEMS.filter((item) => {
      if (item.href === '/') return scope.allowed_screens?.includes('/dashboard');
      return scope.allowed_screens?.includes(item.href);
    });
  }

  return (
    <aside className="w-64 h-full bg-slate-900 text-slate-300 flex flex-col shrink-0 border-r border-slate-800">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 gap-3 border-b border-slate-800 bg-slate-950">
        <div className="w-8 h-8 rounded bg-[#0f2b5c] border border-blue-400/30 flex items-center justify-center font-bold text-white text-sm">
          A
        </div>
        <div>
          <div className="text-sm font-semibold text-white tracking-wide">AICTE Approvals</div>
          <div className="text-[10px] text-slate-400">Workflow Automation</div>
        </div>
      </div>

      {/* Nav Menu */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          Navigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <a
              key={item.href}
              href={item.href}
              onClick={() => onNavigate?.()}
              className={`flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                isActive
                  ? 'bg-blue-900/40 text-blue-300 border-l-2 border-blue-400 pl-[10px]'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/70'
              }`}
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{item.name}</span>
            </a>
          );
        })}
      </nav>

      {/* Demo Guide Presenter Link */}
      <div className="px-3 pb-2">
        <a
          href="/demo"
          onClick={() => onNavigate?.()}
          className="flex items-center gap-2.5 px-3 py-2 text-xs font-semibold rounded-md bg-blue-950/60 text-blue-300 border border-blue-500/30 hover:bg-blue-900/50 hover:text-white transition-colors"
        >
          <Compass className="w-3.5 h-3.5 text-blue-400 shrink-0" />
          <span>Demo Guide (/demo)</span>
        </a>
      </div>

      {/* Sidebar Footer */}
      <div className="p-4 border-t border-slate-800 text-[11px] text-slate-400 flex flex-col gap-1 bg-slate-950">
        <div className="font-medium text-slate-300">Approval Cycle 2026-27</div>
        <div>Statutory Rule Engine: Active</div>
      </div>
    </aside>
  );
}
