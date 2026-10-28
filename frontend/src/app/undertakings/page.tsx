'use client';

import React, { useState, useEffect } from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/lib/auth';
import {
  undertakingsApi,
  UndertakingItem,
  lookupApi,
  Region,
  filesApi,
} from '@/lib/api';
import {
  ClipboardList,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileText,
  Search,
  Filter,
  Eye,
  ShieldAlert,
  Download,
  History,
  Send,
  Building2,
  Calendar,
  AlertCircle,
} from 'lucide-react';

export default function UndertakingsPage() {
  const { scope } = useAuth();
  const [undertakings, setUndertakings] = useState<UndertakingItem[]>([]);
  const [regions, setRegions] = useState<Region[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Filters
  const [selectedRegion, setSelectedRegion] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  // Drawer state
  const [selectedItem, setSelectedItem] = useState<UndertakingItem | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Verification form state
  const [verifyAction, setVerifyAction] = useState<'VERIFIED' | 'REJECTED' | 'NEEDS_MORE_EVIDENCE'>('VERIFIED');
  const [verifyRemarks, setVerifyRemarks] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const fetchUndertakings = async () => {
    try {
      setLoading(true);
      setError('');
      const params: Record<string, any> = {};
      if (selectedRegion !== 'ALL') params.region_id = parseInt(selectedRegion, 10);
      if (selectedStatus !== 'ALL') params.status = selectedStatus;

      const data = await undertakingsApi.list(params);
      setUndertakings(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load undertakings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUndertakings();
  }, [selectedRegion, selectedStatus]);

  useEffect(() => {
    lookupApi.getRegions().then(setRegions).catch(() => {});
  }, []);

  const openDrawer = async (item: UndertakingItem) => {
    try {
      const full = await undertakingsApi.get(item.id);
      setSelectedItem(full);
    } catch {
      setSelectedItem(item);
    }
    setDrawerOpen(true);
    setVerifyAction('VERIFIED');
    setVerifyRemarks('');
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    setSelectedItem(null);
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem) return;
    if ((verifyAction === 'REJECTED' || verifyAction === 'NEEDS_MORE_EVIDENCE') && !verifyRemarks.trim()) {
      alert('Remarks are mandatory when rejecting or requesting more evidence.');
      return;
    }

    setActionLoading(true);
    try {
      const updated = await undertakingsApi.verify(selectedItem.id, {
        action: verifyAction,
        remarks: verifyRemarks,
      });
      setSelectedItem(updated);
      setSuccessMsg(`✓ Undertaking compliance updated: ${verifyAction}`);
      fetchUndertakings();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to record verification decision');
    } finally {
      setActionLoading(false);
    }
  };

  const filteredItems = undertakings.filter((u) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      u.institution_name.toLowerCase().includes(term) ||
      u.title.toLowerCase().includes(term) ||
      u.application_number.toLowerCase().includes(term)
    );
  });

  const getStatusBadge = (status: string, isEscalated: boolean) => {
    if (isEscalated) {
      return (
        <Badge variant="destructive" className="animate-pulse flex items-center gap-1">
          <ShieldAlert className="w-3 h-3" />
          Escalated to Council
        </Badge>
      );
    }

    switch (status) {
      case 'PENDING':
        return <Badge variant="secondary">Pending Evidence</Badge>;
      case 'SUBMITTED':
        return <Badge variant="info">Evidence Submitted</Badge>;
      case 'VERIFIED':
        return <Badge variant="success">Verified Compliant</Badge>;
      case 'REJECTED':
        return <Badge variant="destructive">Rejected</Badge>;
      case 'NEEDS_MORE_EVIDENCE':
        return <Badge variant="warning">Needs Evidence</Badge>;
      case 'OVERDUE':
        return <Badge variant="destructive">Overdue</Badge>;
      case 'ESCALATED':
        return <Badge variant="destructive">Escalated</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  return (
    <AppShell>
      <div className="space-y-4">
        {/* Header Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <ClipboardList className="w-5 h-5 text-indigo-700" />
              Statutory Undertakings Compliance Ledger
            </h1>
            <p className="text-xs text-slate-500">
              Module D: Time-bound commitments tracker, multi-file evidence auditing, 2-strike escalation, and officer sign-offs.
            </p>
          </div>
        </div>

        {/* Success Alert */}
        {successMsg && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-900 rounded text-xs flex items-center justify-between">
            <span>{successMsg}</span>
            <button onClick={() => setSuccessMsg('')} className="text-emerald-700 font-bold">&times;</button>
          </div>
        )}

        {/* Stats Strip */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          <Card className="p-3 bg-white border-slate-200">
            <div className="text-[11px] font-semibold text-slate-500 uppercase">Total Undertakings</div>
            <div className="text-xl font-bold text-slate-900 mt-0.5">{undertakings.length}</div>
            <div className="text-[10px] text-slate-400 mt-1">Across approved institutions</div>
          </Card>

          <Card className="p-3 bg-blue-50/50 border-blue-200">
            <div className="text-[11px] font-semibold text-blue-800 uppercase">Awaiting Verification</div>
            <div className="text-xl font-bold text-blue-900 mt-0.5">
              {undertakings.filter((u) => u.status === 'SUBMITTED').length}
            </div>
            <div className="text-[10px] text-blue-700 mt-1">Evidence uploaded by college</div>
          </Card>

          <Card className="p-3 bg-emerald-50/50 border-emerald-200">
            <div className="text-[11px] font-semibold text-emerald-800 uppercase">Verified & Compliant</div>
            <div className="text-xl font-bold text-emerald-900 mt-0.5">
              {undertakings.filter((u) => u.status === 'VERIFIED').length}
            </div>
            <div className="text-[10px] text-emerald-700 mt-1">Fully closed commitments</div>
          </Card>

          <Card className="p-3 bg-rose-50/50 border-rose-200">
            <div className="text-[11px] font-semibold text-rose-800 uppercase">Overdue</div>
            <div className="text-xl font-bold text-rose-900 mt-0.5">
              {undertakings.filter((u) => u.is_overdue && u.status !== 'VERIFIED').length}
            </div>
            <div className="text-[10px] text-rose-700 mt-1">Breached deadline</div>
          </Card>

          <Card className="p-3 bg-purple-50/50 border-purple-200">
            <div className="text-[11px] font-semibold text-purple-800 uppercase">Escalated to Council</div>
            <div className="text-xl font-bold text-purple-900 mt-0.5">
              {undertakings.filter((u) => u.is_escalated).length}
            </div>
            <div className="text-[10px] text-purple-700 mt-1">&ge; 2 rejections or severe delay</div>
          </Card>
        </div>

        {/* Filter Bar */}
        <div className="bg-white p-3 rounded-lg border border-slate-200 flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
          <div className="relative w-full md:w-80">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search condition, institution, application..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 border border-slate-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-700"
            />
          </div>

          <div className="flex items-center gap-3 w-full md:w-auto">
            <div className="flex items-center gap-1.5">
              <span className="text-slate-500 font-medium text-[11px]">Region:</span>
              <select
                value={selectedRegion}
                onChange={(e) => setSelectedRegion(e.target.value)}
                className="p-1.5 border border-slate-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-700"
              >
                <option value="ALL">All Regions</option>
                {regions.map((r) => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-slate-500 font-medium text-[11px]">Status:</span>
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="p-1.5 border border-slate-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-700"
              >
                <option value="ALL">All Statuses</option>
                <option value="PENDING">Pending Evidence</option>
                <option value="SUBMITTED">Submitted (Needs Review)</option>
                <option value="VERIFIED">Verified</option>
                <option value="NEEDS_MORE_EVIDENCE">Needs More Evidence</option>
                <option value="REJECTED">Rejected</option>
                <option value="OVERDUE">Overdue</option>
                <option value="ESCALATED">Escalated</option>
              </select>
            </div>
          </div>
        </div>

        {/* Table View */}
        <Card className="border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-4">Institution & Application</th>
                  <th className="py-2.5 px-3">Condition Title</th>
                  <th className="py-2.5 px-3">Region</th>
                  <th className="py-2.5 px-3">Due Date & SLA</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Evidence</th>
                  <th className="py-2.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-400">Loading undertakings registry...</td>
                  </tr>
                ) : filteredItems.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500">No undertakings matching filters.</td>
                  </tr>
                ) : (
                  filteredItems.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-900">{item.institution_name}</div>
                        <div className="text-[11px] text-slate-500 mt-0.5 font-mono">
                          {item.application_number}
                        </div>
                      </td>

                      <td className="py-3 px-3">
                        <div className="font-medium text-slate-800 line-clamp-1">{item.title}</div>
                        {item.condition_clause && (
                          <div className="text-[10px] text-slate-400 mt-0.5">
                            Clause: {item.condition_clause} (sample reference)
                          </div>
                        )}
                        {item.rejection_count > 0 && (
                          <span className="inline-block mt-1 px-1.5 py-0.2 rounded text-[10px] font-bold bg-rose-100 text-rose-900 border border-rose-300">
                            Rejections: {item.rejection_count} / 2
                          </span>
                        )}
                      </td>

                      <td className="py-3 px-3">
                        <span className="text-slate-700">{item.region_name}</span>
                      </td>

                      <td className="py-3 px-3">
                        <div className="font-mono text-[11px] font-medium text-slate-800">
                          {new Date(item.due_date).toLocaleDateString()}
                        </div>
                        {item.status !== 'VERIFIED' && (
                          <div className="mt-0.5">
                            {item.is_overdue ? (
                              <span className="text-[10px] font-bold text-rose-700 flex items-center gap-0.5">
                                <AlertCircle className="w-2.5 h-2.5" />
                                Overdue by {Math.abs(item.days_remaining)}d
                              </span>
                            ) : (
                              <span className="text-[10px] text-amber-700">
                                {item.days_remaining}d remaining
                              </span>
                            )}
                          </div>
                        )}
                      </td>

                      <td className="py-3 px-3">
                        {getStatusBadge(item.status, item.is_escalated)}
                      </td>

                      <td className="py-3 px-3">
                        {item.evidence_files && item.evidence_files.length > 0 ? (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-blue-50 border border-blue-200 rounded text-[10px] text-blue-900 font-medium">
                            <FileText className="w-3 h-3 text-blue-600" />
                            {item.evidence_files.length} File(s)
                          </span>
                        ) : (
                          <span className="text-[11px] text-slate-400 italic">No files</span>
                        )}
                      </td>

                      <td className="py-3 px-4 text-right">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => openDrawer(item)}
                          className="h-7 text-xs border-indigo-600 text-indigo-700 hover:bg-indigo-50"
                        >
                          <Eye className="w-3 h-3 mr-1" />
                          Review & Audit
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Sliding Audit & Verification Drawer */}
        {drawerOpen && selectedItem && (
          <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/50 backdrop-blur-sm">
            <div className="bg-white w-full max-w-xl h-full shadow-2xl flex flex-col border-l border-slate-200 overflow-hidden animate-in slide-in-from-right duration-200">
              {/* Drawer Header */}
              <div className="bg-slate-900 text-white px-5 py-4 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-sm flex items-center gap-2">
                    <ClipboardList className="w-4 h-4 text-indigo-400" />
                    Undertaking Audit & Officer Verification
                  </h3>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    {selectedItem.institution_name} • {selectedItem.application_number}
                  </div>
                </div>
                <button
                  onClick={closeDrawer}
                  className="text-slate-400 hover:text-white text-lg font-bold p-1"
                >
                  &times;
                </button>
              </div>

              {/* Drawer Body */}
              <div className="flex-1 overflow-y-auto p-5 space-y-5 text-xs text-slate-700">
                {/* Condition Dossier */}
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] uppercase font-bold text-slate-500">Condition Spec</span>
                    {getStatusBadge(selectedItem.status, selectedItem.is_escalated)}
                  </div>
                  <div className="font-bold text-sm text-slate-900">{selectedItem.title}</div>
                  <p className="text-slate-600 text-xs leading-relaxed">{selectedItem.description}</p>
                  {selectedItem.condition_clause && (
                    <div className="text-[10px] text-slate-500 bg-white p-1.5 rounded border border-slate-200 font-mono">
                      APH Clause: {selectedItem.condition_clause} (sample reference)
                    </div>
                  )}
                  <div className="flex items-center justify-between pt-2 border-t border-slate-200 text-[11px]">
                    <span className="text-slate-500">Due Date: <strong>{new Date(selectedItem.due_date).toLocaleDateString()}</strong></span>
                    <span className={selectedItem.is_overdue ? 'text-rose-700 font-bold' : 'text-slate-700'}>
                      {selectedItem.is_overdue ? `Overdue by ${Math.abs(selectedItem.days_remaining)} days` : `${selectedItem.days_remaining} days left`}
                    </span>
                  </div>
                </div>

                {/* Escalation Alert Banner if applicable */}
                {selectedItem.is_escalated && (
                  <div className="p-3 bg-rose-50 border border-rose-300 rounded-lg text-rose-900 space-y-1">
                    <div className="font-bold flex items-center gap-1.5 text-xs">
                      <ShieldAlert className="w-4 h-4 text-rose-700" />
                      Escalated to Competent Authority
                    </div>
                    <p className="text-[11px] leading-relaxed">
                      {selectedItem.escalation_reason || 'This undertaking breached statutory time limits or was rejected twice by the regional scrutiny desk.'}
                    </p>
                  </div>
                )}

                {/* Uploaded Evidence Dossier */}
                <div className="space-y-2">
                  <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-blue-700" />
                    Uploaded Evidence Documents ({selectedItem.evidence_files?.length || 0})
                  </h4>

                  {selectedItem.evidence_files && selectedItem.evidence_files.length > 0 ? (
                    <div className="space-y-1.5">
                      {selectedItem.evidence_files.map((file) => (
                        <div
                          key={file.id}
                          className="p-2.5 bg-white border border-slate-200 rounded-lg flex items-center justify-between hover:border-blue-300 transition-colors"
                        >
                          <div className="flex items-center gap-2">
                            <FileText className="w-4 h-4 text-slate-400" />
                            <div>
                              <div className="font-semibold text-slate-800 text-xs">{file.original_filename}</div>
                              <div className="text-[10px] text-slate-400">
                                {(file.file_size / 1024).toFixed(1)} KB • Uploaded on {new Date(file.created_at).toLocaleDateString()}
                              </div>
                            </div>
                          </div>

                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => filesApi.downloadFile(file.id, file.original_filename)}
                            className="h-6 text-[10px] border-slate-300 hover:bg-slate-50"
                          >
                            <Download className="w-3 h-3 mr-1" />
                            View Evidence
                          </Button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-3 bg-slate-50 border border-dashed border-slate-300 rounded text-center text-slate-400 text-xs">
                      No evidence documents uploaded yet by the institution.
                    </div>
                  )}
                </div>

                {/* Verification Decision Form for Officers */}
                {selectedItem.status !== 'VERIFIED' && (
                  <form onSubmit={handleVerify} className="space-y-3 pt-3 border-t border-slate-200">
                    <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" />
                      Record Officer Verification Determination
                    </h4>

                    <div className="p-2 bg-blue-50 border border-blue-200 rounded text-blue-900 text-[11px]">
                      <strong>Statutory Workflow Rule:</strong> Scrutiny Officers audit compliance. 2 consecutive rejections automatically escalate this condition to the Competent Authority.
                    </div>

                    <div className="grid grid-cols-3 gap-2">
                      <label className={`p-2 rounded-lg border text-center cursor-pointer transition-all ${
                        verifyAction === 'VERIFIED'
                          ? 'border-emerald-500 bg-emerald-50 text-emerald-900 font-bold ring-1 ring-emerald-400'
                          : 'border-slate-200 bg-white hover:bg-slate-50'
                      }`}>
                        <input
                          type="radio"
                          name="action"
                          className="sr-only"
                          checked={verifyAction === 'VERIFIED'}
                          onChange={() => setVerifyAction('VERIFIED')}
                        />
                        <CheckCircle2 className="w-4 h-4 mx-auto mb-1 text-emerald-700" />
                        <span className="text-[11px] block">Verified</span>
                      </label>

                      <label className={`p-2 rounded-lg border text-center cursor-pointer transition-all ${
                        verifyAction === 'NEEDS_MORE_EVIDENCE'
                          ? 'border-amber-500 bg-amber-50 text-amber-900 font-bold ring-1 ring-amber-400'
                          : 'border-slate-200 bg-white hover:bg-slate-50'
                      }`}>
                        <input
                          type="radio"
                          name="action"
                          className="sr-only"
                          checked={verifyAction === 'NEEDS_MORE_EVIDENCE'}
                          onChange={() => setVerifyAction('NEEDS_MORE_EVIDENCE')}
                        />
                        <AlertTriangle className="w-4 h-4 mx-auto mb-1 text-amber-700" />
                        <span className="text-[11px] block">Need Evidence</span>
                      </label>

                      <label className={`p-2 rounded-lg border text-center cursor-pointer transition-all ${
                        verifyAction === 'REJECTED'
                          ? 'border-rose-500 bg-rose-50 text-rose-900 font-bold ring-1 ring-rose-400'
                          : 'border-slate-200 bg-white hover:bg-slate-50'
                      }`}>
                        <input
                          type="radio"
                          name="action"
                          className="sr-only"
                          checked={verifyAction === 'REJECTED'}
                          onChange={() => setVerifyAction('REJECTED')}
                        />
                        <XCircle className="w-4 h-4 mx-auto mb-1 text-rose-700" />
                        <span className="text-[11px] block">Reject</span>
                      </label>
                    </div>

                    <div>
                      <label className="font-semibold text-slate-700 block mb-1">
                        Officer Remarks & Audit Justification:
                      </label>
                      <textarea
                        rows={3}
                        value={verifyRemarks}
                        onChange={(e) => setVerifyRemarks(e.target.value)}
                        placeholder="Detail audit findings, missing statutory disclosures, or compliance confirmation..."
                        className="w-full p-2 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-blue-700"
                        required={verifyAction !== 'VERIFIED'}
                      />
                    </div>

                    <Button
                      type="submit"
                      size="sm"
                      disabled={actionLoading}
                      className={`w-full text-white ${
                        verifyAction === 'VERIFIED'
                          ? 'bg-emerald-700 hover:bg-emerald-800'
                          : verifyAction === 'REJECTED'
                          ? 'bg-rose-700 hover:bg-rose-800'
                          : 'bg-amber-600 hover:bg-amber-700'
                      }`}
                    >
                      {actionLoading ? 'Recording Decision...' : `Submit Determination (${verifyAction})`}
                    </Button>
                  </form>
                )}

                {/* Audit Trail Timeline */}
                <div className="space-y-3 pt-3 border-t border-slate-200">
                  <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                    <History className="w-3.5 h-3.5 text-slate-600" />
                    Lifecycle Audit History
                  </h4>

                  {selectedItem.history && selectedItem.history.length > 0 ? (
                    <div className="relative pl-5 space-y-3 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
                      {selectedItem.history.map((hist) => (
                        <div key={hist.id} className="relative text-xs">
                          <div className="absolute -left-5 top-1 w-2.5 h-2.5 rounded-full bg-slate-400 ring-2 ring-white" />
                          <div className="font-semibold text-slate-800">
                            {hist.action}
                            <span className="text-[10px] text-slate-400 font-normal ml-2">
                              {new Date(hist.created_at).toLocaleString()}
                            </span>
                          </div>
                          <div className="text-[11px] text-slate-500">
                            By: {hist.actor_name} ({hist.actor_role})
                          </div>
                          {hist.remarks && (
                            <div className="mt-1 p-2 bg-slate-50 rounded border border-slate-200 text-[11px] text-slate-700">
                              {hist.remarks}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-slate-400 text-xs italic">No prior history events recorded.</div>
                  )}
                </div>
              </div>

              {/* Drawer Footer */}
              <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-end">
                <Button size="sm" variant="outline" onClick={closeDrawer}>
                  Close Drawer
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
