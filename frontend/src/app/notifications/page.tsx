'use client';

import React, { useState, useEffect } from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { notificationsApi, NotificationItem } from '@/lib/api';
import { Bell, CheckCircle2, Clock, Check, Filter } from 'lucide-react';

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [filterUnread, setFilterUnread] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  const loadNotifications = async (unreadOnly = filterUnread) => {
    setLoading(true);
    try {
      const data = await notificationsApi.list(unreadOnly);
      setNotifications(data.notifications);
      setUnreadCount(data.unread_count);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNotifications(filterUnread);
  }, [filterUnread]);

  const handleMarkOneRead = async (id: number) => {
    try {
      await notificationsApi.markRead(id);
      loadNotifications(filterUnread);
    } catch (err) {
      console.error(err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead();
      loadNotifications(filterUnread);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-slate-900">Notification Center</h1>
              {unreadCount > 0 && (
                <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-2 py-0.5 rounded-full">
                  {unreadCount} unread
                </span>
              )}
            </div>
            <p className="text-sm text-slate-500 mt-1">
              Role-scoped statutory notices, escalation intimations, and SLA alerts.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setFilterUnread(!filterUnread)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${
                filterUnread
                  ? 'bg-blue-50 text-blue-700 border-blue-200'
                  : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
              }`}
            >
              <Filter className="w-3.5 h-3.5" />
              <span>{filterUnread ? 'Showing Unread Only' : 'Show All'}</span>
            </button>

            {unreadCount > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleMarkAllRead}
                className="flex items-center gap-1.5 text-xs text-slate-700"
              >
                <Check className="w-3.5 h-3.5 text-blue-600" />
                <span>Mark All Read</span>
              </Button>
            )}
          </div>
        </div>

        {/* Notifications List */}
        <Card className="divide-y divide-slate-100 p-0 overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-sm text-slate-500">Loading notifications...</div>
          ) : notifications.length === 0 ? (
            <div className="p-12 text-center text-sm text-slate-500">
              <Bell className="w-8 h-8 mx-auto text-slate-300 mb-2" />
              <p>No notifications found.</p>
            </div>
          ) : (
            notifications.map((item) => (
              <div
                key={item.id}
                className={`p-4 transition-colors flex items-start gap-4 hover:bg-slate-50/80 ${
                  !item.is_read ? 'bg-blue-50/20' : ''
                }`}
              >
                <div className="mt-1 shrink-0">
                  {!item.is_read ? (
                    <div className="w-2.5 h-2.5 rounded-full bg-blue-600 ring-4 ring-blue-100" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4 text-slate-300" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className={`text-sm ${!item.is_read ? 'font-semibold text-slate-900' : 'text-slate-800'}`}>
                      {item.title}
                    </h3>
                    <div className="flex items-center gap-1 text-xs text-slate-400 shrink-0">
                      <Clock className="w-3.5 h-3.5" />
                      <span>{new Date(item.sent_at).toLocaleString()}</span>
                    </div>
                  </div>

                  <p className="text-xs text-slate-600 mt-1 leading-relaxed whitespace-pre-line">
                    {item.body}
                  </p>

                  <div className="mt-3 flex items-center gap-3">
                    {item.alert_id && (
                      <a
                        href={`/alerts?id=${item.alert_id}`}
                        className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline"
                      >
                        Inspect Linked Alert →
                      </a>
                    )}
                    {!item.is_read && (
                      <button
                        onClick={() => handleMarkOneRead(item.id)}
                        className="text-xs text-slate-500 hover:text-slate-800"
                      >
                        Mark as read
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </Card>
      </div>
    </AppShell>
  );
}
