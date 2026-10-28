'use client';

import React, { useState, useEffect, useMemo, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/lib/auth';
import {
  alertsApi,
  AlertItem,
  AlertDetail,
  AlertSummary
} from '@/lib/api';
import {
  AlertTriangle,
  ShieldAlert,
  Clock,
  CheckCircle2,
  X,
  Filter,
  Search,
  ChevronRight,
  Info,
  Calendar,
  Building,
  User,
  ArrowRight,
  RotateCcw,
  VolumeX,
  CheckSquare
} from 'lucide-react';

function AlertsContent() {
  const { scope } = useAuth();
  const searchParams = useSearchParams();
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [summary, setSummary] = useState<AlertSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedAlertId, setSelectedAlertId] = useState<number | null>(null);
  const [alertDetail, setAlertDetail] = useState<AlertDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);

  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('OPEN');
  const [tierFilter, setTierFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Action modals/states
  const [ackRemarks, setAckRemarks] = useState<string>('');
  const [isAckModalOpen, setIsAckModalOpen] = useState<boolean>(false);
  const [snoozeHours, setSnoozeHours] = useState<number>(24);
  const [snoozeReason, setSnoozeReason] = useState<string>('');
  const [isSnoozeModalOpen, setIsSnoozeModalOpen] = useState<boolean>(false);
  const [resolveRemarks, setResolveRemarks] = useState<string>('');
  const [isResolveModalOpen, setIsResolveModalOpen] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [submittingAction, setSubmittingAction] = useState<boolean>(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [alertsData, summaryData] = await Promise.all([
        alertsApi.list(),
        alertsApi.getSummary(),
      ]);
      setAlerts(alertsData);
      setSummary(summaryData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Check URL param ?id=
  useEffect(() => {
    const idParam = searchParams.get('id');
    if (idParam) {
      const parsedId = parseInt(idParam, 10);
      if (!isNaN(parsedId)) {
        setSelectedAlertId(parsedId);
      }
    }
  }, [searchParams]);

  // Load detail when selected
  useEffect(() => {
    if (!selectedAlertId) {
      setAlertDetail(null);
      return;
    }
    const fetchDetail = async () => {
      setLoadingDetail(true);
      try {
        const detail = await alertsApi.get(selectedAlertId);
        setAlertDetail(detail);
      } catch (err) {
        console.error(err);
      } finally {
        setLoadingDetail(false);
      }
    };
    fetchDetail();
  }, [selectedAlertId]);

  // Filtered alerts
  const filteredAlerts = useMemo(() => {
    return alerts.filter((a) => {
      if (severityFilter !== 'ALL' && a.severity !== severityFilter) return false;
      if (statusFilter === 'OPEN' && a.status === 'RESOLVED') return false;
      if (statusFilter === 'RESOLVED' && a.status !== 'RESOLVED') return false;
      if (statusFilter !== 'ALL' && statusFilter !== 'OPEN' && a.status !== statusFilter) return false;
      if (tierFilter !== 'ALL' && a.escalation_tier.toString() !== tierFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchTitle = a.title.toLowerCase().includes(q);
        const matchApp = a.application_number?.toLowerCase().includes(q);
        const matchInst = a.institution_name?.toLowerCase().includes(q);
        const matchRule = a.rule_code.toLowerCase().includes(q);
        if (!matchTitle && !matchApp && !matchInst && !matchRule) return false;
      }
      return true;
    });
  }, [alerts, severityFilter, statusFilter, tierFilter, searchQuery]);

  // Severity styling
  const severityBadgeVariant: Record<string, 'neutral' | 'info' | 'success' | 'warning' | 'danger'> = {
    INFO: 'neutral',
    MEDIUM: 'warning',
    HIGH: 'warning',
    CRITICAL: 'danger',
  };

  const statusBadgeVariant: Record<string, 'neutral' | 'info' | 'success' | 'warning' | 'danger'> = {
    ACTIVE: 'warning',
    ACKNOWLEDGED: 'info',
    SNOOZED: 'neutral',
    ESCALATED: 'danger',
    RESOLVED: 'success',
  };

  const tierBadge: Record<number, { label: string; color: string }> = {
    1: { label: 'L1 Officer', color: 'bg-slate-100 text-slate-700 border-slate-300' },
    2: { label: 'L2 Regional Head', color: 'bg-amber-100 text-amber-800 border-amber-300' },
    3: { label: 'L3 Competent Authority', color: 'bg-purple-100 text-purple-800 border-purple-300' },
  };

  // Action handlers
  const handleAcknowledge = async () => {
    if (!selectedAlertId) return;
    setSubmittingAction(true);
    setActionError(null);
    try {
      await alertsApi.acknowledge(selectedAlertId, ackRemarks);
      setIsAckModalOpen(false);
      setAckRemarks('');
      // Reload
      const detail = await alertsApi.get(selectedAlertId);
      setAlertDetail(detail);
      loadData();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Acknowledgement failed');
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleSnooze = async () => {
    if (!selectedAlertId) return;
    if (!snoozeReason.trim() || snoozeReason.trim().length < 5) {
      setActionError('A substantive written reason (at least 5 characters) is required to snooze.');
      return;
    }
    setSubmittingAction(true);
    setActionError(null);
    try {
      await alertsApi.snooze(selectedAlertId, snoozeHours, snoozeReason);
      setIsSnoozeModalOpen(false);
      setSnoozeReason('');
      // Reload
      const detail = await alertsApi.get(selectedAlertId);
      setAlertDetail(detail);
      loadData();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Snooze failed');
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleResolve = async () => {
    if (!selectedAlertId) return;
    if (!resolveRemarks.trim() || resolveRemarks.trim().length < 5) {
      setActionError('A substantive written remark (at least 5 characters) is required to resolve.');
      return;
    }
    setSubmittingAction(true);
    setActionError(null);
    try {
      await alertsApi.resolve(selectedAlertId, resolveRemarks);
      setIsResolveModalOpen(false);
      setResolveRemarks('');
      // Reload
      const detail = await alertsApi.get(selectedAlertId);
      setAlertDetail(detail);
      loadData();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Resolution failed');
    } finally {
      setSubmittingAction(false);
    }
  };

  const canResolve = scope && ['ADMIN', 'COMPETENT_AUTHORITY', 'REGIONAL_HEAD'].includes(scope.role);

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Statutory Watcher & Compliance Alerts</h1>
            <p className="text-sm text-slate-500 mt-1">
              Deterministic rule evaluation, SLA breaches, multi-tier escalation, and verifiable audit trails.
            </p>
          </div>
        </div>

        {/* Real-time Summary Cards */}
        {summary && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <Card className="p-4 border-l-4 border-l-red-500 bg-red-50/20">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Critical Alerts</div>
              <div className="text-2xl font-bold text-red-700 mt-1">{summary.by_severity['CRITICAL'] || 0}</div>
              <div className="text-[11px] text-slate-500 mt-0.5">Immediate statutory intervention</div>
            </Card>
            <Card className="p-4 border-l-4 border-l-amber-500 bg-amber-50/20">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">High Severity</div>
              <div className="text-2xl font-bold text-amber-700 mt-1">{summary.by_severity['HIGH'] || 0}</div>
              <div className="text-[11px] text-slate-500 mt-0.5">SLA overdue or expired conditions</div>
            </Card>
            <Card className="p-4 border-l-4 border-l-blue-500 bg-blue-50/20">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Medium / Near Breach</div>
              <div className="text-2xl font-bold text-blue-700 mt-1">{summary.by_severity['MEDIUM'] || 0}</div>
              <div className="text-[11px] text-slate-500 mt-0.5">Threshold warnings within 80% SLA</div>
            </Card>
            <Card className="p-4 border-l-4 border-l-purple-500 bg-purple-50/20">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Escalated (L2 / L3)</div>
              <div className="text-2xl font-bold text-purple-700 mt-1">
                {(summary.by_level['2'] || 0) + (summary.by_level['3'] || 0)}
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">Regional Head & Council level</div>
            </Card>
          </div>
        )}

        {/* Filter Toolbar */}
        <Card className="p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2 flex-1 min-w-[280px]">
              {/* Search */}
              <div className="relative w-64">
                <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Filter by application, institution, rule..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-xs rounded-md border border-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              {/* Status Filter */}
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-2.5 py-1.5 text-xs rounded-md border border-slate-300 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="OPEN">Status: Open Only (Active/Ack/Snoozed/Esc)</option>
                <option value="ALL">Status: All Statuses</option>
                <option value="ACTIVE">Active</option>
                <option value="ACKNOWLEDGED">Acknowledged</option>
                <option value="SNOOZED">Snoozed</option>
                <option value="ESCALATED">Escalated</option>
                <option value="RESOLVED">Resolved</option>
              </select>

              {/* Severity Filter */}
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="px-2.5 py-1.5 text-xs rounded-md border border-slate-300 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="ALL">Severity: All</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="INFO">Info</option>
              </select>

              {/* Level Filter */}
              <select
                value={tierFilter}
                onChange={(e) => setTierFilter(e.target.value)}
                className="px-2.5 py-1.5 text-xs rounded-md border border-slate-300 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="ALL">Tier: All Levels</option>
                <option value="1">L1 - Desk Officer</option>
                <option value="2">L2 - Regional Head</option>
                <option value="3">L3 - Competent Authority</option>
              </select>
            </div>

            <div className="text-xs text-slate-500">
              Showing <span className="font-semibold text-slate-800">{filteredAlerts.length}</span> of {alerts.length} alerts
            </div>
          </div>
        </Card>

        {/* Alerts Table */}
        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-semibold uppercase tracking-wider text-slate-600">
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Rule & Alert Title</th>
                  <th className="py-3 px-4">Application / Entity</th>
                  <th className="py-3 px-4">Escalation Tier</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Age</th>
                  <th className="py-3 px-4 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500">
                      Loading compliance alerts...
                    </td>
                  </tr>
                ) : filteredAlerts.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-slate-500">
                      <CheckCircle2 className="w-8 h-8 mx-auto text-emerald-500 mb-2" />
                      <p className="font-medium text-slate-700">No alerts match the chosen filters.</p>
                      <p className="text-slate-400 text-[11px] mt-0.5">All regulatory timelines and SLA standards intact.</p>
                    </td>
                  </tr>
                ) : (
                  filteredAlerts.map((alert) => (
                    <tr
                      key={alert.id}
                      onClick={() => setSelectedAlertId(alert.id)}
                      className={`hover:bg-slate-50/80 cursor-pointer transition-colors ${
                        selectedAlertId === alert.id ? 'bg-blue-50/50' : ''
                      }`}
                    >
                      <td className="py-3 px-4 shrink-0">
                        <Badge variant={severityBadgeVariant[alert.severity] || 'neutral'}>
                          {alert.severity}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-medium text-slate-900">{alert.title}</div>
                        <div className="text-[11px] text-slate-400 font-mono mt-0.5">{alert.rule_code}</div>
                      </td>
                      <td className="py-3 px-4">
                        {alert.application_number ? (
                          <div className="font-medium text-blue-700 font-mono">{alert.application_number}</div>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                        <div className="text-[11px] text-slate-500 max-w-xs truncate">{alert.institution_name}</div>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border ${
                          tierBadge[alert.escalation_tier]?.color || 'bg-slate-100 text-slate-700 border-slate-300'
                        }`}>
                          {tierBadge[alert.escalation_tier]?.label || `Tier ${alert.escalation_tier}`}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant={statusBadgeVariant[alert.status] || 'neutral'}>
                          {alert.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                        {alert.age_hours !== null && alert.age_hours !== undefined
                          ? `${alert.age_hours}h`
                          : 'Recent'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedAlertId(alert.id);
                          }}
                          className="text-blue-600 hover:text-blue-800 font-medium inline-flex items-center gap-0.5"
                        >
                          <span>Explain</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Explainable Alert Detail Drawer / Modal */}
        {selectedAlertId && (
          <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-sm flex justify-end">
            <div className="w-full max-w-2xl bg-white h-full shadow-2xl flex flex-col animate-slide-left border-l border-slate-200">
              {/* Drawer Header */}
              <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between shrink-0">
                <div className="flex items-center gap-2.5">
                  <AlertTriangle className="w-5 h-5 text-amber-600" />
                  <div>
                    <h2 className="text-base font-bold text-slate-900">Explainable Compliance Alert</h2>
                    <p className="text-xs text-slate-500 font-mono">ID: ALT-{selectedAlertId}</p>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedAlertId(null)}
                  className="p-1.5 text-slate-400 hover:text-slate-700 rounded-md hover:bg-slate-200 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Drawer Body */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {loadingDetail || !alertDetail ? (
                  <div className="py-12 text-center text-sm text-slate-500">Loading alert explanation...</div>
                ) : (
                  <>
                    {/* Status & Severity Badges */}
                    <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 bg-slate-50 rounded-lg border border-slate-200">
                      <div className="flex items-center gap-2">
                        <Badge variant={severityBadgeVariant[alertDetail.severity]}>
                          {alertDetail.severity}
                        </Badge>
                        <Badge variant={statusBadgeVariant[alertDetail.status]}>
                          {alertDetail.status}
                        </Badge>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${
                          tierBadge[alertDetail.escalation_tier]?.color
                        }`}>
                          {tierBadge[alertDetail.escalation_tier]?.label}
                        </span>
                      </div>
                      <div className="text-xs text-slate-500 flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        <span>Created: {new Date(alertDetail.created_at).toLocaleString()}</span>
                      </div>
                    </div>

                    {/* Alert Title & Message */}
                    <div>
                      <h3 className="text-lg font-bold text-slate-900">{alertDetail.title}</h3>
                      <p className="text-sm text-slate-600 mt-1 leading-relaxed">{alertDetail.message}</p>
                    </div>

                    {/* WHY THIS ALERT FIRED: Explainability Box */}
                    <div className="p-4 rounded-lg bg-blue-50/60 border border-blue-200 space-y-3">
                      <div className="flex items-center gap-2 text-xs font-bold text-blue-900 uppercase tracking-wide">
                        <Info className="w-4 h-4 text-blue-700 shrink-0" />
                        <span>Why This Alert Fired (Statutory Engine Explanation)</span>
                      </div>

                      <p className="text-sm font-medium text-slate-800 leading-relaxed bg-white p-3 rounded border border-blue-100">
                        {alertDetail.explanation_meta?.why_fired || alertDetail.message}
                      </p>

                      <div className="grid grid-cols-2 gap-3 text-xs pt-1">
                        <div className="bg-white p-2.5 rounded border border-blue-100">
                          <span className="text-slate-500 block">Actual Observed Value:</span>
                          <span className="font-bold text-slate-900 text-sm mt-0.5 block">
                            {String(alertDetail.explanation_meta?.actual_value ?? 'N/A')}
                          </span>
                        </div>
                        <div className="bg-white p-2.5 rounded border border-blue-100">
                          <span className="text-slate-500 block">Statutory Threshold:</span>
                          <span className="font-bold text-slate-900 text-sm mt-0.5 block">
                            {String(alertDetail.explanation_meta?.threshold_value ?? 'N/A')}
                          </span>
                        </div>
                      </div>

                      {/* APH Clause Reference with (sample reference) marker */}
                      <div className="pt-2 border-t border-blue-100 flex items-center justify-between text-xs">
                        <span className="text-slate-500">Regulatory Clause:</span>
                        <span className="font-mono text-blue-900 font-semibold flex items-center gap-1.5">
                          <span>{alertDetail.explanation_meta?.reference_label || 'APH 2026 Manual'}</span>
                          {/* Treat APH clause references as sample labels unless config marks verified */}
                          {!alertDetail.explanation_meta?.is_verified_clause && (
                            <span className="text-[10px] bg-amber-100 text-amber-800 font-sans font-medium px-1.5 py-0.5 rounded border border-amber-200">
                              (sample reference)
                            </span>
                          )}
                        </span>
                      </div>
                    </div>

                    {/* Entity Details */}
                    <div className="space-y-2">
                      <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider">Associated Entity</h4>
                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 grid grid-cols-2 gap-3 text-xs">
                        <div>
                          <span className="text-slate-400 block">Application:</span>
                          <span className="font-semibold text-slate-800 font-mono">
                            {alertDetail.application_number || 'N/A'}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400 block">Institution:</span>
                          <span className="font-semibold text-slate-800 truncate block">
                            {alertDetail.institution_name || 'N/A'}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400 block">Rule Code:</span>
                          <span className="font-mono text-slate-700 font-semibold">{alertDetail.rule_code}</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block">Assigned Recipient:</span>
                          <span className="font-semibold text-slate-800">
                            {alertDetail.recipient_user_name || alertDetail.recipient_role}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Acknowledgement and Resolution State */}
                    {(alertDetail.acknowledged_at || alertDetail.resolved_at || alertDetail.snooze_count > 0) && (
                      <div className="space-y-2">
                        <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider">Procedural Records</h4>
                        <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200 space-y-2 text-xs">
                          {alertDetail.acknowledged_at && (
                            <div>
                              <span className="font-semibold text-emerald-800">✓ Acknowledged:</span>{' '}
                              <span className="text-slate-700">{alertDetail.acknowledgement_remarks}</span>
                              <span className="text-slate-400 block text-[10px]">
                                By Officer ID {alertDetail.acknowledged_by} on {new Date(alertDetail.acknowledged_at).toLocaleString()}
                              </span>
                            </div>
                          )}

                          {alertDetail.snooze_count > 0 && (
                            <div>
                              <span className="font-semibold text-slate-800">Snoozed ({alertDetail.snooze_count}x):</span>{' '}
                              <span className="text-slate-700">{alertDetail.snooze_reason}</span>
                              {alertDetail.snoozed_until && (
                                <span className="text-slate-400 block text-[10px]">
                                  Paused until {new Date(alertDetail.snoozed_until).toLocaleString()}
                                </span>
                              )}
                            </div>
                          )}

                          {alertDetail.resolved_at && (
                            <div className="pt-2 border-t border-slate-200">
                              <span className="font-semibold text-emerald-800">✓ Statutorily Resolved:</span>{' '}
                              <span className="text-slate-700">{alertDetail.resolution_remarks}</span>
                              <span className="text-slate-400 block text-[10px]">
                                By Officer ID {alertDetail.resolved_by} on {new Date(alertDetail.resolved_at).toLocaleString()}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* ESCALATION TRAIL TIMELINE */}
                    <div className="space-y-2">
                      <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider">Escalation Trail</h4>
                      {alertDetail.escalation_history.length === 0 ? (
                        <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-500 text-center">
                          Alert is currently at L1 Desk Officer tier. No upward escalation triggered.
                        </div>
                      ) : (
                        <div className="border-l-2 border-slate-200 ml-3 pl-4 space-y-4 py-1">
                          {alertDetail.escalation_history.map((h, idx) => (
                            <div key={h.id || idx} className="relative">
                              <div className="absolute -left-[23px] top-1 w-3 h-3 rounded-full bg-amber-500 ring-4 ring-white" />
                              <div className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
                                <span>Tier {h.from_tier}</span>
                                <ArrowRight className="w-3 h-3 text-slate-400" />
                                <span className="text-amber-700">Tier {h.to_tier} ({h.target_role})</span>
                              </div>
                              <p className="text-xs text-slate-600 mt-0.5">{h.reason}</p>
                              <span className="text-[10px] text-slate-400 block mt-0.5">
                                {new Date(h.created_at).toLocaleString()}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>

              {/* Drawer Action Bar */}
              {alertDetail && alertDetail.status !== 'RESOLVED' && (
                <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between shrink-0 gap-2">
                  <div className="flex items-center gap-2">
                    {/* Acknowledge */}
                    {alertDetail.status === 'ACTIVE' && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setActionError(null);
                          setIsAckModalOpen(true);
                        }}
                        className="flex items-center gap-1.5 text-xs text-blue-700 border-blue-300 hover:bg-blue-50"
                      >
                        <CheckSquare className="w-3.5 h-3.5" />
                        <span>Acknowledge</span>
                      </Button>
                    )}

                    {/* Snooze */}
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setActionError(null);
                        setIsSnoozeModalOpen(true);
                      }}
                      className="flex items-center gap-1.5 text-xs text-slate-700 hover:bg-slate-100"
                    >
                      <VolumeX className="w-3.5 h-3.5" />
                      <span>Snooze</span>
                    </Button>
                  </div>

                  {/* Resolve (Competent Authority, Regional Head, Admin) */}
                  {canResolve && (
                    <Button
                      size="sm"
                      onClick={() => {
                        setActionError(null);
                        setIsResolveModalOpen(true);
                      }}
                      className="flex items-center gap-1.5 text-xs bg-emerald-700 hover:bg-emerald-800 text-white"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Mark Resolved</span>
                    </Button>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* MODAL: Acknowledge */}
        {isAckModalOpen && (
          <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
            <Card className="w-full max-w-md p-6 space-y-4">
              <h3 className="text-base font-bold text-slate-900">Acknowledge Alert</h3>
              <p className="text-xs text-slate-600">
                Confirm receipt and accountability for this regulatory alert. An audit log row will be written.
              </p>
              {actionError && <div className="text-xs text-red-600 bg-red-50 p-2 rounded">{actionError}</div>}
              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">Acknowledgement Remarks (Optional)</label>
                <textarea
                  value={ackRemarks}
                  onChange={(e) => setAckRemarks(e.target.value)}
                  placeholder="e.g., Land deed verification in progress with tehsildar."
                  rows={3}
                  className="w-full p-2 text-xs rounded border border-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="ghost" size="sm" onClick={() => setIsAckModalOpen(false)}>
                  Cancel
                </Button>
                <Button size="sm" onClick={handleAcknowledge} disabled={submittingAction}>
                  {submittingAction ? 'Saving...' : 'Confirm Acknowledged'}
                </Button>
              </div>
            </Card>
          </div>
        )}

        {/* MODAL: Snooze */}
        {isSnoozeModalOpen && (
          <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
            <Card className="w-full max-w-md p-6 space-y-4">
              <h3 className="text-base font-bold text-slate-900">Snooze Alert</h3>
              <p className="text-xs text-slate-600">
                Pause reminder notifications for this alert. Note: snoozing never hides an alert from higher tiers once escalation thresholds are breached.
              </p>
              {actionError && <div className="text-xs text-red-600 bg-red-50 p-2 rounded">{actionError}</div>}
              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">Snooze Duration</label>
                <select
                  value={snoozeHours}
                  onChange={(e) => setSnoozeHours(Number(e.target.value))}
                  className="w-full p-2 text-xs rounded border border-slate-300 bg-white"
                >
                  <option value={12}>12 Hours</option>
                  <option value={24}>24 Hours (1 Day)</option>
                  <option value={48}>48 Hours (2 Days)</option>
                  <option value={72}>72 Hours (3 Days)</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">
                  Mandatory Written Reason <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={snoozeReason}
                  onChange={(e) => setSnoozeReason(e.target.value)}
                  placeholder="Substantive justification for pause (e.g. Awaiting certified revenue map from District Collector)."
                  rows={3}
                  className="w-full p-2 text-xs rounded border border-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="ghost" size="sm" onClick={() => setIsSnoozeModalOpen(false)}>
                  Cancel
                </Button>
                <Button size="sm" onClick={handleSnooze} disabled={submittingAction}>
                  {submittingAction ? 'Snoozing...' : 'Confirm Snooze'}
                </Button>
              </div>
            </Card>
          </div>
        )}

        {/* MODAL: Resolve */}
        {isResolveModalOpen && (
          <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
            <Card className="w-full max-w-md p-6 space-y-4">
              <h3 className="text-base font-bold text-slate-900">Mark Alert Resolved</h3>
              <p className="text-xs text-slate-600">
                Statutorily conclude this alert. Only the Member Secretary / Competent Authority, Regional Head, or System Admin may perform this action.
              </p>
              {actionError && <div className="text-xs text-red-600 bg-red-50 p-2 rounded">{actionError}</div>}
              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">
                  Resolution Remarks <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={resolveRemarks}
                  onChange={(e) => setResolveRemarks(e.target.value)}
                  placeholder="Substantive explanation of resolution (e.g., Validated updated Fire NOC submitted on portal)."
                  rows={3}
                  className="w-full p-2 text-xs rounded border border-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="ghost" size="sm" onClick={() => setIsResolveModalOpen(false)}>
                  Cancel
                </Button>
                <Button size="sm" onClick={handleResolve} disabled={submittingAction} className="bg-emerald-700 hover:bg-emerald-800 text-white">
                  {submittingAction ? 'Resolving...' : 'Confirm Resolution'}
                </Button>
              </div>
            </Card>
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default function AlertsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-sm text-slate-500">Loading alerts workspace...</div>}>
      <AlertsContent />
    </Suspense>
  );
}
