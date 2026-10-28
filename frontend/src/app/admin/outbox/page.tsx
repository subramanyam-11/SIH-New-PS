'use client';

import React, { useState, useEffect } from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { adminApi, EmailOutboxItem } from '@/lib/api';
import { Mail, Clock, Send, AlertCircle, Eye, CheckCircle2, ChevronDown, ChevronUp } from 'lucide-react';

export default function AdminOutboxPage() {
  const [outbox, setOutbox] = useState<EmailOutboxItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const fetchOutbox = async () => {
    setLoading(true);
    try {
      const data = await adminApi.getOutbox({
        status: statusFilter !== 'ALL' ? statusFilter : undefined,
        limit: 50,
      });
      setOutbox(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOutbox();
  }, [statusFilter]);

  const statusVariant: Record<string, 'neutral' | 'info' | 'success' | 'warning' | 'danger'> = {
    QUEUED: 'warning',
    SENT: 'success',
    FAILED: 'danger',
    SUPPRESSED: 'neutral',
  };

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Mail className="w-6 h-6 text-blue-700" />
              <h1 className="text-2xl font-bold text-slate-900">Email Outbox Dispatch Queue</h1>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              Statutory communication outbox. When EMAIL_SEND_ENABLED=false (default), emails are held safely in SUPPRESSED status for full in-app visibility without external SMTP traffic.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 text-xs rounded-md border border-slate-300 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="ALL">Status: All Records</option>
              <option value="QUEUED">Queued</option>
              <option value="SENT">Sent (SMTP)</option>
              <option value="SUPPRESSED">Suppressed (Simulation)</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>
        </div>

        {/* Outbox Table */}
        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-semibold uppercase tracking-wider text-slate-600">
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Recipient</th>
                  <th className="py-3 px-4">Subject</th>
                  <th className="py-3 px-4">Template / Entity</th>
                  <th className="py-3 px-4">Attempts</th>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4 text-right">Inspect Body</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500">
                      Loading outbox queue...
                    </td>
                  </tr>
                ) : outbox.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-slate-500">
                      <Mail className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                      <p>No outbox communications found matching the filter.</p>
                    </td>
                  </tr>
                ) : (
                  outbox.map((item) => (
                    <React.Fragment key={item.id}>
                      <tr
                        onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                        className={`hover:bg-slate-50/80 cursor-pointer transition-colors ${
                          expandedId === item.id ? 'bg-blue-50/30' : ''
                        }`}
                      >
                        <td className="py-3 px-4 shrink-0">
                          <Badge variant={statusVariant[item.status] || 'neutral'}>
                            {item.status}
                          </Badge>
                        </td>
                        <td className="py-3 px-4">
                          <div className="font-semibold text-slate-800">{item.recipient_email}</div>
                          {item.recipient_name && (
                            <div className="text-[11px] text-slate-400">{item.recipient_name}</div>
                          )}
                        </td>
                        <td className="py-3 px-4 max-w-sm truncate font-medium text-slate-800">
                          {item.subject}
                        </td>
                        <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                          {item.template_code || item.entity_type || '—'}
                        </td>
                        <td className="py-3 px-4 text-slate-600">
                          {item.attempts}
                        </td>
                        <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                          {new Date(item.created_at).toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setExpandedId(expandedId === item.id ? null : item.id);
                            }}
                            className="text-blue-600 hover:text-blue-800 font-medium inline-flex items-center gap-1"
                          >
                            <span>{expandedId === item.id ? 'Collapse' : 'Preview'}</span>
                            {expandedId === item.id ? (
                              <ChevronUp className="w-3.5 h-3.5" />
                            ) : (
                              <ChevronDown className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </td>
                      </tr>

                      {/* Expanded Email Body Preview */}
                      {expandedId === item.id && (
                        <tr className="bg-slate-50/70">
                          <td colSpan={7} className="p-4">
                            <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-inner space-y-2">
                              <div className="flex items-center justify-between text-xs border-b border-slate-100 pb-2">
                                <div>
                                  <span className="text-slate-400">To:</span>{' '}
                                  <span className="font-semibold text-slate-800">{item.recipient_email}</span>
                                </div>
                                <div>
                                  <span className="text-slate-400">Subject:</span>{' '}
                                  <span className="font-semibold text-slate-800">{item.subject}</span>
                                </div>
                              </div>
                              <pre className="text-xs text-slate-700 whitespace-pre-wrap font-sans leading-relaxed pt-2">
                                {item.body}
                              </pre>
                              {item.error_message && (
                                <div className="text-xs text-red-600 bg-red-50 p-2 rounded mt-2 border border-red-200">
                                  Error: {item.error_message}
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
