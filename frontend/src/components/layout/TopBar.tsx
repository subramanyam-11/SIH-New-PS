'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/lib/auth';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  LogOut,
  User as UserIcon,
  Building,
  MapPin,
  Bell,
  Play,
  CheckCircle2,
  ExternalLink,
  Clock,
  Menu
} from 'lucide-react';
import { notificationsApi, alertsApi, NotificationItem } from '@/lib/api';

export function TopBar({ onToggleMobileMenu }: { onToggleMobileMenu?: () => void } = {}) {
  const { scope, logout } = useAuth();
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [recentNotifs, setRecentNotifs] = useState<NotificationItem[]>([]);
  const [isDropdownOpen, setIsDropdownOpen] = useState<boolean>(false);
  const [isRunningChecks, setIsRunningChecks] = useState<boolean>(false);
  const [checkStatusMsg, setCheckStatusMsg] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const fetchNotifications = async () => {
    try {
      const data = await notificationsApi.list(false);
      setUnreadCount(data.unread_count);
      setRecentNotifs(data.notifications.slice(0, 5));
    } catch {
      // Soft fail if not logged in
    }
  };

  useEffect(() => {
    if (!scope) return;
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 15000);
    return () => clearInterval(interval);
  }, [scope]);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleRunChecks = async () => {
    setIsRunningChecks(true);
    setCheckStatusMsg(null);
    try {
      const res = await alertsApi.runChecksNow();
      setCheckStatusMsg(`Checked: ${res.rules_evaluated} rules, ${res.alerts_created} new`);
      fetchNotifications();
      setTimeout(() => setCheckStatusMsg(null), 4000);
    } catch (err: any) {
      setCheckStatusMsg(err.response?.data?.detail || 'Error running checks');
      setTimeout(() => setCheckStatusMsg(null), 4000);
    } finally {
      setIsRunningChecks(false);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead();
      fetchNotifications();
    } catch (err) {
      console.error(err);
    }
  };

  const handleMarkOneRead = async (id: number) => {
    try {
      await notificationsApi.markRead(id);
      fetchNotifications();
    } catch (err) {
      console.error(err);
    }
  };

  if (!scope) return null;

  const roleLabelMap: Record<string, string> = {
    ADMIN: 'System Admin',
    REGIONAL_HEAD: 'Regional Head',
    SCRUTINY_OFFICER: 'Scrutiny Officer',
    EVC_COORDINATOR: 'EVC Coordinator',
    COMPETENT_AUTHORITY: 'Member Secretary / Competent Authority',
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
    <header className="h-16 bg-white border-b border-slate-200 px-4 sm:px-6 flex items-center justify-between shrink-0 relative z-30">
      <div className="flex items-center gap-2 sm:gap-3">
        <button
          onClick={onToggleMobileMenu}
          className="md:hidden p-1.5 -ml-1 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-md"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>
        <h1 className="text-sm md:text-base font-semibold text-slate-800 truncate max-w-[190px] sm:max-w-none">
          All India Council for Technical Education
        </h1>
        <span className="hidden sm:inline text-slate-300">|</span>
        <span className="hidden sm:inline text-xs text-slate-500 font-medium">Compliance & Workflow Portal</span>
      </div>

      <div className="flex items-center gap-4">
        {/* Run Checks Now (Engine evaluation button) */}
        {!scope.is_institution && (
          <div className="flex items-center gap-2">
            {checkStatusMsg && (
              <span className="text-xs text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200 animate-fade-in">
                {checkStatusMsg}
              </span>
            )}
            <button
              onClick={handleRunChecks}
              disabled={isRunningChecks}
              className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 active:bg-slate-300 border border-slate-300 rounded-md transition-colors"
              title="Trigger background alert rule evaluation immediately"
            >
              <Play className={`w-3 h-3 text-blue-600 ${isRunningChecks ? 'animate-spin' : ''}`} />
              <span>{isRunningChecks ? 'Evaluating...' : 'Run Checks Now'}</span>
            </button>
          </div>
        )}

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

        {/* Notification Bell Dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-full relative transition-colors"
            title="Notifications"
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 flex h-4 min-w-[16px] px-1 items-center justify-center rounded-full bg-red-600 text-[10px] font-bold text-white shadow-sm">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </button>

          {isDropdownOpen && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-lg shadow-xl border border-slate-200 overflow-hidden z-50">
              <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-800">Notifications</span>
                  {unreadCount > 0 && (
                    <span className="text-[10px] bg-blue-100 text-blue-800 font-bold px-1.5 py-0.5 rounded">
                      {unreadCount} unread
                    </span>
                  )}
                </div>
                {unreadCount > 0 && (
                  <button
                    onClick={handleMarkAllRead}
                    className="text-[11px] text-blue-600 hover:text-blue-800 font-medium"
                  >
                    Mark all read
                  </button>
                )}
              </div>

              <div className="max-h-72 overflow-y-auto divide-y divide-slate-100">
                {recentNotifs.length === 0 ? (
                  <div className="py-6 text-center text-xs text-slate-500">
                    No recent notifications
                  </div>
                ) : (
                  recentNotifs.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => !item.is_read && handleMarkOneRead(item.id)}
                      className={`p-3 text-left transition-colors cursor-pointer hover:bg-slate-50 flex items-start gap-2.5 ${
                        !item.is_read ? 'bg-blue-50/40' : ''
                      }`}
                    >
                      <div className="mt-0.5 shrink-0">
                        {!item.is_read ? (
                          <div className="w-2 h-2 rounded-full bg-blue-600 mt-1" />
                        ) : (
                          <CheckCircle2 className="w-3.5 h-3.5 text-slate-400 mt-0.5" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-xs ${!item.is_read ? 'font-semibold text-slate-900' : 'text-slate-700'}`}>
                          {item.title}
                        </p>
                        <p className="text-[11px] text-slate-500 line-clamp-2 mt-0.5">
                          {item.body}
                        </p>
                        <div className="flex items-center gap-1 text-[10px] text-slate-400 mt-1">
                          <Clock className="w-3 h-3" />
                          <span>{new Date(item.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="p-2.5 bg-slate-50 border-t border-slate-200 text-center">
                <a
                  href="/notifications"
                  onClick={() => setIsDropdownOpen(false)}
                  className="text-xs font-medium text-blue-600 hover:text-blue-800 flex items-center justify-center gap-1"
                >
                  <span>View all notifications</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          )}
        </div>

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
