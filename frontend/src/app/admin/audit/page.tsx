'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { auditApi } from '@/lib/api';
import {
  ShieldCheck,
  AlertTriangle,
  Download,
  Search,
  Filter,
  CheckCircle2,
  RefreshCw,
  Lock,
  Eye,
  X
} from 'lucide-react';

export default function AuditLogPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [loading, setLoading] = useState(true);

  // Filters
  const [actorRole, setActorRole] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [tableName, setTableName] = useState('');
  const [appId, setAppId] = useState('');

  // Integrity Check State
  const [verifying, setVerifying] = useState(false);
  const [integrityResult, setIntegrityResult] = useState<any>(null);

  // Detail Modal
  const [selectedRecord, setSelectedRecord] = useState<any>(null);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params: any = { page, page_size: pageSize };
      if (actorRole) params.actor_role = actorRole;
      if (actionFilter) params.action = actionFilter;
      if (tableName) params.table_name = tableName;
      if (appId) params.application_id = appId;

      const res = await auditApi.search(params);
      setLogs(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error('Failed to load audit logs', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [page, pageSize, actorRole, actionFilter, tableName, appId]);

  const handleVerifyIntegrity = async () => {
    setVerifying(true);
    setIntegrityResult(null);
    try {
      const res = await auditApi.verifyIntegrity();
      setIntegrityResult(res);
    } catch (err: any) {
      setIntegrityResult({
        status: 'TAMPER_DETECTED',
        verified: false,
        reason: err?.response?.data?.detail || 'Verification error'
      });
    } finally {
      setVerifying(false);
    }
  };

  const handleExportCsv = () => {
    const params: any = {};
    if (actorRole) params.actor_role = actorRole;
    if (actionFilter) params.action = actionFilter;
    if (tableName) params.table_name = tableName;
    if (appId) params.application_id = appId;
    window.location.href = auditApi.exportCsvUrl(params);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Title & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Cryptographic Audit Trail
            </h1>
            <Badge variant="success" size="sm">
              APPEND-ONLY
            </Badge>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Tamper-evident SHA-256 hash-chained log. Modifications and deletions are strictly blocked by database triggers.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleVerifyIntegrity}
            disabled={verifying}
            className="flex items-center gap-2 border-slate-300"
          >
            {verifying ? (
              <RefreshCw className="w-4 h-4 animate-spin text-slate-600" />
            ) : (
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
            )}
            <span>{verifying ? 'Verifying Chain...' : 'Verify Integrity'}</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleExportCsv}
            className="flex items-center gap-2"
          >
            <Download className="w-4 h-4 text-slate-600" />
            <span>Export CSV</span>
          </Button>
        </div>
      </div>

      {/* Integrity Verification Banner */}
      {integrityResult && (
        <div
          className={`p-4 rounded-lg border text-sm flex items-start gap-3 transition-all ${
            integrityResult.verified
              ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
              : 'bg-red-50 border-red-200 text-red-900'
          }`}
        >
          {integrityResult.verified ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          )}
          <div className="flex-1">
            <div className="font-semibold text-xs tracking-wide uppercase">
              {integrityResult.verified
                ? 'Hash Chain Integrity Verified 100% Intact'
                : 'Tamper Alert Detected'}
            </div>
            <div className="text-xs mt-1">
              {integrityResult.message || integrityResult.reason}
            </div>
            {integrityResult.latest_hash && (
              <div className="mt-2 text-[11px] font-mono text-emerald-800 break-all bg-emerald-100/60 p-1.5 rounded">
                <strong>Latest Chain Hash:</strong> {integrityResult.latest_hash}
              </div>
            )}
          </div>
          <button
            onClick={() => setIntegrityResult(null)}
            className="text-slate-400 hover:text-slate-600 text-xs"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Filters Bar */}
      <Card className="p-4 bg-white border border-slate-200">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">
              Actor Role
            </label>
            <select
              value={actorRole}
              onChange={(e) => {
                setActorRole(e.target.value);
                setPage(1);
              }}
              className="w-full text-xs p-2 rounded border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">All Roles</option>
              <option value="ADMIN">System Admin</option>
              <option value="COMPETENT_AUTHORITY">Competent Authority</option>
              <option value="REGIONAL_HEAD">Regional Head</option>
              <option value="SCRUTINY_OFFICER">Scrutiny Officer</option>
              <option value="EVC_COORDINATOR">EVC Coordinator</option>
              <option value="BUREAU_OFFICER">Bureau Officer</option>
              <option value="COMMITTEE_MEMBER">Committee Member</option>
              <option value="INSTITUTION_USER">Institution User</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">
              Action
            </label>
            <input
              type="text"
              placeholder="e.g. SUBMIT_APPLICATION, VIEW_CASE"
              value={actionFilter}
              onChange={(e) => {
                setActionFilter(e.target.value);
                setPage(1);
              }}
              className="w-full text-xs p-2 rounded border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">
              Entity / Table
            </label>
            <input
              type="text"
              placeholder="e.g. applications, uploaded_files"
              value={tableName}
              onChange={(e) => {
                setTableName(e.target.value);
                setPage(1);
              }}
              className="w-full text-xs p-2 rounded border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">
              Application ID
            </label>
            <input
              type="number"
              placeholder="e.g. 1, 15, 33"
              value={appId}
              onChange={(e) => {
                setAppId(e.target.value);
                setPage(1);
              }}
              className="w-full text-xs p-2 rounded border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>
      </Card>

      {/* Audit Log Table */}
      <Card className="border border-slate-200 overflow-hidden bg-white">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3 w-16">ID</th>
                <th className="py-2.5 px-3">Timestamp (UTC)</th>
                <th className="py-2.5 px-3">Actor</th>
                <th className="py-2.5 px-3">Action</th>
                <th className="py-2.5 px-3">Entity</th>
                <th className="py-2.5 px-3">Hash Linkage</th>
                <th className="py-2.5 px-3 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {loading ? (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-slate-400">
                    Loading cryptographic audit events...
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-slate-400">
                    No audit records matching query criteria.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-2 px-3 font-mono text-[11px] text-slate-500">
                      #{log.id}
                    </td>
                    <td className="py-2 px-3 whitespace-nowrap text-slate-600 font-mono text-[11px]">
                      {log.created_at ? log.created_at.replace('T', ' ').substring(0, 19) : '-'}
                    </td>
                    <td className="py-2 px-3">
                      <div className="font-medium text-slate-900">{log.actor_name}</div>
                      <div className="text-[10px] text-slate-400">{log.actor_role}</div>
                    </td>
                    <td className="py-2 px-3">
                      <Badge
                        variant={
                          log.action.includes('REJECT')
                            ? 'danger'
                            : log.action.includes('VIEW')
                            ? 'neutral'
                            : log.action.includes('VERIF') || log.action.includes('APPROV')
                            ? 'success'
                            : 'info'
                        }
                        size="sm"
                      >
                        {log.action}
                      </Badge>
                    </td>
                    <td className="py-2 px-3 text-slate-600">
                      <span className="font-mono text-[11px] bg-slate-100 px-1 py-0.5 rounded">
                        {log.table_name}
                      </span>
                      <span className="text-[10px] text-slate-400 ml-1">#{log.record_id}</span>
                    </td>
                    <td className="py-2 px-3 font-mono text-[10px] text-slate-400 max-w-[120px] truncate" title={`Hash: ${log.hash}\nPrev: ${log.prev_hash}`}>
                      {log.hash ? log.hash.substring(0, 12) + '...' : 'GENESIS'}
                    </td>
                    <td className="py-2 px-3 text-right">
                      <button
                        onClick={() => setSelectedRecord(log)}
                        className="inline-flex items-center gap-1 text-[11px] text-blue-600 hover:text-blue-800 font-medium px-2 py-1 rounded hover:bg-blue-50"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Inspect</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="p-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
          <div>
            Showing <strong>{logs.length > 0 ? (page - 1) * pageSize + 1 : 0}</strong> to{' '}
            <strong>{Math.min(page * pageSize, total)}</strong> of <strong>{total}</strong> verified entries
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1 || loading}
              onClick={() => setPage(page - 1)}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page * pageSize >= total || loading}
              onClick={() => setPage(page + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      </Card>

      {/* Record Inspection Modal */}
      {selectedRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[85vh] flex flex-col border border-slate-200">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-sm text-slate-900">
                  Audit Record #{selectedRecord.id} Details
                </h3>
                <p className="text-xs text-slate-500">
                  {selectedRecord.action} on {selectedRecord.table_name} (#{selectedRecord.record_id})
                </p>
              </div>
              <button
                onClick={() => setSelectedRecord(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 overflow-y-auto space-y-3 text-xs flex-1">
              <div className="grid grid-cols-2 gap-2 p-2 bg-slate-50 rounded border border-slate-100 font-mono text-[11px]">
                <div>
                  <span className="text-slate-500">Timestamp:</span> {selectedRecord.created_at}
                </div>
                <div>
                  <span className="text-slate-500">Actor IP:</span> {selectedRecord.ip_address || 'Internal/Loopback'}
                </div>
                <div className="col-span-2 break-all">
                  <span className="text-slate-500">Previous Hash:</span> {selectedRecord.prev_hash}
                </div>
                <div className="col-span-2 break-all">
                  <span className="text-slate-500">Row Hash:</span> {selectedRecord.hash}
                </div>
              </div>

              {selectedRecord.old_values && (
                <div>
                  <div className="font-semibold text-slate-700 mb-1">Previous Values:</div>
                  <pre className="p-2.5 bg-slate-900 text-slate-100 rounded text-[11px] overflow-x-auto">
                    {JSON.stringify(selectedRecord.old_values, null, 2)}
                  </pre>
                </div>
              )}

              {selectedRecord.new_values && (
                <div>
                  <div className="font-semibold text-slate-700 mb-1">New Values / Metadata:</div>
                  <pre className="p-2.5 bg-slate-900 text-slate-100 rounded text-[11px] overflow-x-auto">
                    {JSON.stringify(selectedRecord.new_values, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="p-3 border-t border-slate-100 flex justify-end">
              <Button variant="outline" size="sm" onClick={() => setSelectedRecord(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
