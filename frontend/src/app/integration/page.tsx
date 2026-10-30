'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { integrationApi } from '@/lib/api';
import {
  Radio,
  Search,
  Send,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowRightLeft,
  Key,
  ShieldCheck,
  RefreshCw,
  Code
} from 'lucide-react';

export default function IntegrationPage() {
  const [statusData, setStatusData] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Test Lookup state
  const [lookupId, setLookupId] = useState('1-10974231');
  const [lookupResult, setLookupResult] = useState<any>(null);
  const [lookupLoading, setLookupLoading] = useState(false);

  // Test Status Push state
  const [pushAppNum, setPushAppNum] = useState('AICTE/2026/APP-10001');
  const [pushStatus, setPushStatus] = useState('SCRUTINY_PASSED');
  const [pushRemarks, setPushRemarks] = useState('Verified compliance documents in portal.');
  const [pushResult, setPushResult] = useState<any>(null);
  const [pushLoading, setPushLoading] = useState(false);

  const fetchStatusAndLogs = async () => {
    setLoading(true);
    try {
      const [statusRes, logsRes] = await Promise.all([
        integrationApi.getStatus(),
        integrationApi.getLogs(30),
      ]);
      setStatusData(statusRes);
      setLogs(logsRes.items || []);
    } catch (err) {
      console.error('Failed to load integration status/logs', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatusAndLogs();
  }, []);

  const handleLookup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lookupId) return;
    setLookupLoading(true);
    setLookupResult(null);
    try {
      const res = await integrationApi.lookupInstitution(lookupId);
      setLookupResult(res);
      await fetchStatusAndLogs();
    } catch (err: any) {
      setLookupResult({
        status: 'ERROR',
        message: err?.response?.data?.detail || 'Lookup failed'
      });
    } finally {
      setLookupLoading(false);
    }
  };

  const handlePushStatus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pushAppNum) return;
    setPushLoading(true);
    setPushResult(null);
    try {
      const res = await integrationApi.pushStatus({
        application_number: pushAppNum,
        new_status: pushStatus,
        remarks: pushRemarks,
      });
      setPushResult(res);
      await fetchStatusAndLogs();
    } catch (err: any) {
      setPushResult({
        status: 'ERROR',
        message: err?.response?.data?.detail || 'Status push failed'
      });
    } finally {
      setPushLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              AICTE National Portal Integration
            </h1>
            <Badge variant="warning" size="sm">
              MOCK ADAPTER
            </Badge>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Standardized integration adapter for external portal data synchronization, HMAC signature verification, and replay guards.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={fetchStatusAndLogs}
          disabled={loading}
          className="flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 text-slate-600 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Logs</span>
        </Button>
      </div>

      {/* Prominent Mandatory Mock Notice */}
      <div className="p-4 rounded-lg border border-amber-300 bg-amber-50 text-amber-900 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="text-xs">
          <strong className="font-semibold uppercase tracking-wider block text-[11px] mb-0.5">
            MOCK ADAPTER. No real AICTE system is contacted.
          </strong>
          All records, lookups, extension of approval (EoA) histories, and status push acknowledgments in this section are synthetic demonstrations. In production, this adapter connects to the national portal using mutual TLS and certified API gateways.
        </div>
      </div>

      {/* Adapter Architecture & Security Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4 bg-white border border-slate-200">
          <div className="flex items-center gap-2 text-slate-500 mb-1">
            <Radio className="w-4 h-4 text-blue-600" />
            <span className="text-[11px] font-semibold uppercase tracking-wider">
              Adapter Mode
            </span>
          </div>
          <div className="text-sm font-bold text-slate-800">
            {statusData?.implementation || 'MockAicteAdapter'}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">Synthetic Local Sandbox</div>
        </Card>

        <Card className="p-4 bg-white border border-slate-200">
          <div className="flex items-center gap-2 text-slate-500 mb-1">
            <Key className="w-4 h-4 text-emerald-600" />
            <span className="text-[11px] font-semibold uppercase tracking-wider">
              Inbound HMAC Auth
            </span>
          </div>
          <div className="text-sm font-bold text-slate-800">HMAC-SHA256 Active</div>
          <div className="text-[11px] text-slate-400 mt-0.5">X-API-Key + X-Signature</div>
        </Card>

        <Card className="p-4 bg-white border border-slate-200">
          <div className="flex items-center gap-2 text-slate-500 mb-1">
            <ShieldCheck className="w-4 h-4 text-purple-600" />
            <span className="text-[11px] font-semibold uppercase tracking-wider">
              Replay Protection
            </span>
          </div>
          <div className="text-sm font-bold text-slate-800">
            {statusData?.replay_window_seconds || 300}s Drift Guard
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">Timestamp & Idempotency</div>
        </Card>

        <Card className="p-4 bg-white border border-slate-200">
          <div className="flex items-center gap-2 text-slate-500 mb-1">
            <ArrowRightLeft className="w-4 h-4 text-amber-600" />
            <span className="text-[11px] font-semibold uppercase tracking-wider">
              Secondary Adapter
            </span>
          </div>
          <div className="text-sm font-bold text-slate-800">SMTP Outbox</div>
          <div className="text-[11px] text-slate-400 mt-0.5">Documented Email Service</div>
        </Card>
      </div>

      {/* Two Columns: Test Lookup & Test Status Push */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Test 1: Institution Lookup */}
        <Card className="border border-slate-200 bg-white">
          <CardHeader className="p-4 border-b border-slate-100">
            <CardTitle className="text-sm font-semibold text-slate-800 flex items-center gap-2">
              <Search className="w-4 h-4 text-blue-600" />
              <span>Simulate External Institution Lookup</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-500">
              Query synthetic national portal records by AICTE Permanent ID.
            </CardDescription>
          </CardHeader>

          <CardContent className="p-4 space-y-4">
            <form onSubmit={handleLookup} className="flex gap-2">
              <input
                type="text"
                value={lookupId}
                onChange={(e) => setLookupId(e.target.value)}
                placeholder="e.g. 1-10974231"
                className="flex-1 text-xs p-2 rounded border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
              />
              <Button type="submit" variant="primary" size="sm" disabled={lookupLoading}>
                {lookupLoading ? 'Querying...' : 'Lookup'}
              </Button>
            </form>

            <div className="text-[11px] text-slate-500 flex gap-2">
              <span>Try sample IDs:</span>
              <button
                type="button"
                onClick={() => setLookupId('1-10974231')}
                className="text-blue-600 underline"
              >
                1-10974231
              </button>
              <button
                type="button"
                onClick={() => setLookupId('1-4328901')}
                className="text-blue-600 underline"
              >
                1-4328901
              </button>
              <button
                type="button"
                onClick={() => setLookupId('1-9876543')}
                className="text-blue-600 underline"
              >
                1-9876543
              </button>
            </div>

            {lookupResult && (
              <div>
                <div className="text-[11px] font-semibold text-slate-700 mb-1 flex items-center justify-between">
                  <span>Adapter Response Payload:</span>
                  <Badge variant="warning" size="sm">
                    {lookupResult.adapter_mode}
                  </Badge>
                </div>
                <pre className="p-3 bg-slate-900 text-slate-100 rounded text-[11px] overflow-x-auto max-h-56">
                  {JSON.stringify(lookupResult, null, 2)}
                </pre>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Test 2: Status Push */}
        <Card className="border border-slate-200 bg-white">
          <CardHeader className="p-4 border-b border-slate-100">
            <CardTitle className="text-sm font-semibold text-slate-800 flex items-center gap-2">
              <Send className="w-4 h-4 text-emerald-600" />
              <span>Simulate Status Push to External Portal</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-500">
              Transmit internal workflow status update to simulated national portal endpoint.
            </CardDescription>
          </CardHeader>

          <CardContent className="p-4 space-y-4">
            <form onSubmit={handlePushStatus} className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                    Application #
                  </label>
                  <input
                    type="text"
                    value={pushAppNum}
                    onChange={(e) => setPushAppNum(e.target.value)}
                    className="w-full text-xs p-2 rounded border border-slate-300 bg-white text-slate-800 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                    New Target Status
                  </label>
                  <select
                    value={pushStatus}
                    onChange={(e) => setPushStatus(e.target.value)}
                    className="w-full text-xs p-2 rounded border border-slate-300 bg-white text-slate-800"
                  >
                    <option value="SCRUTINY_PASSED">SCRUTINY_PASSED</option>
                    <option value="EVC_SCHEDULED">EVC_SCHEDULED</option>
                    <option value="APPROVAL_GRANTED">APPROVAL_GRANTED</option>
                    <option value="APPROVAL_REJECTED">APPROVAL_REJECTED</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                  Sync Remarks
                </label>
                <input
                  type="text"
                  value={pushRemarks}
                  onChange={(e) => setPushRemarks(e.target.value)}
                  className="w-full text-xs p-2 rounded border border-slate-300 bg-white text-slate-800"
                />
              </div>

              <Button type="submit" variant="primary" size="sm" disabled={pushLoading} className="w-full">
                {pushLoading ? 'Syncing...' : 'Push Status Update'}
              </Button>
            </form>

            {pushResult && (
              <div>
                <div className="text-[11px] font-semibold text-slate-700 mb-1 flex items-center justify-between">
                  <span>Push Acknowledgment:</span>
                  <Badge variant="warning" size="sm">
                    {pushResult.adapter_mode}
                  </Badge>
                </div>
                <pre className="p-3 bg-slate-900 text-slate-100 rounded text-[11px] overflow-x-auto max-h-48">
                  {JSON.stringify(pushResult, null, 2)}
                </pre>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Integration Logs Table */}
      <Card className="border border-slate-200 bg-white overflow-hidden">
        <CardHeader className="p-4 border-b border-slate-100 flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-sm font-semibold text-slate-800">
              Integration Sync Audit Log
            </CardTitle>
            <CardDescription className="text-xs text-slate-500">
              Complete history of inbound webhooks and outbound synchronization requests.
            </CardDescription>
          </div>
          <Badge variant="neutral" size="sm">
            {logs.length} Recent Calls
          </Badge>
        </CardHeader>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3">Direction</th>
                <th className="py-2.5 px-3">Operation</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Idempotency Key</th>
                <th className="py-2.5 px-3">Timestamp (UTC)</th>
                <th className="py-2.5 px-3">Request Summary</th>
                <th className="py-2.5 px-3">Response Summary</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700 font-mono text-[11px]">
              {loading ? (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-slate-400 font-sans">
                    Loading integration synchronization log...
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-slate-400 font-sans">
                    No integration requests recorded yet.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-2.5 px-3 font-sans">
                      <Badge
                        variant={log.direction === 'INBOUND' ? 'info' : 'neutral'}
                        size="sm"
                      >
                        {log.direction}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-slate-800">
                      {log.operation}
                    </td>
                    <td className="py-2.5 px-3 font-sans">
                      <Badge
                        variant={log.status === 'SUCCESS' ? 'success' : 'danger'}
                        size="sm"
                      >
                        {log.status}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 text-slate-500">
                      {log.idempotency_key ? log.idempotency_key.substring(0, 16) + '...' : '-'}
                    </td>
                    <td className="py-2.5 px-3 text-slate-500 whitespace-nowrap">
                      {log.created_at ? log.created_at.replace('T', ' ').substring(0, 19) : '-'}
                    </td>
                    <td className="py-2.5 px-3 text-slate-600 max-w-[160px] truncate" title={JSON.stringify(log.request_summary)}>
                      {JSON.stringify(log.request_summary)}
                    </td>
                    <td className="py-2.5 px-3 text-slate-600 max-w-[160px] truncate" title={JSON.stringify(log.response_summary)}>
                      {JSON.stringify(log.response_summary)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
