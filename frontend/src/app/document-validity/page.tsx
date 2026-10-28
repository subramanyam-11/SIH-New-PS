'use client';

import React, { useState, useEffect } from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/lib/auth';
import {
  documentsApi,
  DocumentItem,
  lookupApi,
  Region,
  filesApi,
} from '@/lib/api';
import {
  ShieldCheck,
  ShieldAlert,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileText,
  Search,
  Filter,
  Eye,
  Download,
  History,
  Building2,
  Calendar,
  AlertCircle,
  FileCheck,
  Layers,
} from 'lucide-react';

export default function DocumentValidityPage() {
  const { scope } = useAuth();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [regions, setRegions] = useState<Region[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Filters
  const [selectedRegion, setSelectedRegion] = useState<string>('ALL');
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [selectedUrgency, setSelectedUrgency] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  // Drawer state
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Renewal verification form
  const [verifyAction, setVerifyAction] = useState<'APPROVE' | 'REJECT'>('APPROVE');
  const [approvedExpiryDate, setApprovedExpiryDate] = useState('');
  const [verifyRemarks, setVerifyRemarks] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      setError('');
      const params: Record<string, any> = {};
      if (selectedRegion !== 'ALL') params.region_id = parseInt(selectedRegion, 10);
      if (selectedType !== 'ALL') params.document_type = selectedType;

      const data = await documentsApi.list(params);
      setDocuments(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [selectedRegion, selectedType]);

  useEffect(() => {
    lookupApi.getRegions().then(setRegions).catch(() => {});
  }, []);

  const openDrawer = async (doc: DocumentItem) => {
    try {
      const full = await documentsApi.get(doc.id);
      setSelectedDoc(full);
      setApprovedExpiryDate(full.expiry_date ? full.expiry_date.slice(0, 10) : '');
    } catch {
      setSelectedDoc(doc);
      setApprovedExpiryDate(doc.expiry_date ? doc.expiry_date.slice(0, 10) : '');
    }
    setDrawerOpen(true);
    setVerifyAction('APPROVE');
    setVerifyRemarks('');
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    setSelectedDoc(null);
  };

  const handleVerifyRenewal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDoc) return;
    if (verifyAction === 'REJECT' && !verifyRemarks.trim()) {
      alert('Remarks are required when rejecting a document renewal.');
      return;
    }

    setActionLoading(true);
    try {
      const updated = await documentsApi.verifyRenewal(selectedDoc.id, {
        action: verifyAction,
        remarks: verifyRemarks,
        approved_expiry_date: approvedExpiryDate || undefined,
      });
      setSelectedDoc(updated);
      setSuccessMsg(`✓ Document renewal verification recorded: ${verifyAction}. Linked alerts auto-resolved.`);
      fetchDocuments();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to verify renewal');
    } finally {
      setActionLoading(false);
    }
  };

  const filteredDocs = documents.filter((d) => {
    if (selectedUrgency !== 'ALL' && d.urgency !== selectedUrgency) return false;
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      d.institution_name.toLowerCase().includes(term) ||
      d.title.toLowerCase().includes(term) ||
      d.document_type.toLowerCase().includes(term) ||
      d.application_number.toLowerCase().includes(term)
    );
  });

  const getUrgencyBadge = (urgency: string, status: string) => {
    if (status === 'RENEWAL_SUBMITTED') {
      return (
        <Badge variant="warning" className="bg-amber-100 text-amber-900 border-amber-300">
          Renewal submitted, awaiting verification
        </Badge>
      );
    }
    if (status === 'SUPERSEDED') {
      return <Badge variant="secondary">Superseded</Badge>;
    }

    switch (urgency) {
      case 'EXPIRED':
        return <Badge variant="destructive">EXPIRED</Badge>;
      case 'CRITICAL':
        return <Badge variant="destructive" className="bg-rose-700 text-white">Critical &le;30d</Badge>;
      case 'EXPIRING_SOON':
        return <Badge variant="warning">Expiring &le;60d</Badge>;
      case 'VALID':
        return <Badge variant="success">Valid</Badge>;
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
              <ShieldCheck className="w-5 h-5 text-emerald-700" />
              Statutory Document Validity & Renewal Watchtower
            </h1>
            <p className="text-xs text-slate-500">
              Module E: Expiry queue, multi-version supersede history, and renewal verification with deferred alert resolution.
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
            <div className="text-[11px] font-semibold text-slate-500 uppercase">Total Documents</div>
            <div className="text-xl font-bold text-slate-900 mt-0.5">{documents.length}</div>
            <div className="text-[10px] text-slate-400 mt-1">Monitored statutory certificates</div>
          </Card>

          <Card className="p-3 bg-rose-50/50 border-rose-200">
            <div className="text-[11px] font-semibold text-rose-800 uppercase">Expired</div>
            <div className="text-xl font-bold text-rose-900 mt-0.5">
              {documents.filter((d) => d.urgency === 'EXPIRED').length}
            </div>
            <div className="text-[10px] text-rose-700 mt-1">Requires immediate enforcement</div>
          </Card>

          <Card className="p-3 bg-amber-50/50 border-amber-200">
            <div className="text-[11px] font-semibold text-amber-800 uppercase">Critical &le;30 Days</div>
            <div className="text-xl font-bold text-amber-900 mt-0.5">
              {documents.filter((d) => d.urgency === 'CRITICAL').length}
            </div>
            <div className="text-[10px] text-amber-700 mt-1">Imminent regulatory breach</div>
          </Card>

          <Card className="p-3 bg-blue-50/50 border-blue-200">
            <div className="text-[11px] font-semibold text-blue-800 uppercase">Renewal Submitted</div>
            <div className="text-xl font-bold text-blue-900 mt-0.5">
              {documents.filter((d) => d.status === 'RENEWAL_SUBMITTED').length}
            </div>
            <div className="text-[10px] text-blue-700 mt-1">Awaiting officer audit</div>
          </Card>

          <Card className="p-3 bg-emerald-50/50 border-emerald-200">
            <div className="text-[11px] font-semibold text-emerald-800 uppercase">Valid & Compliant</div>
            <div className="text-xl font-bold text-emerald-900 mt-0.5">
              {documents.filter((d) => d.urgency === 'VALID').length}
            </div>
            <div className="text-[10px] text-emerald-700 mt-1">Clear statutory validity</div>
          </Card>
        </div>

        {/* Filter Controls */}
        <div className="bg-white p-3 rounded-lg border border-slate-200 flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
          <div className="relative w-full md:w-80">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search document title, college, type..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 border border-slate-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-700"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            <div className="flex items-center gap-1.5">
              <span className="text-slate-500 font-medium text-[11px]">Region:</span>
              <select
                value={selectedRegion}
                onChange={(e) => setSelectedRegion(e.target.value)}
                className="p-1.5 border border-slate-200 rounded text-xs focus:ring-1 focus:ring-blue-700"
              >
                <option value="ALL">All Regions</option>
                {regions.map((r) => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-slate-500 font-medium text-[11px]">Type:</span>
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="p-1.5 border border-slate-200 rounded text-xs focus:ring-1 focus:ring-blue-700"
              >
                <option value="ALL">All Document Types</option>
                <option value="LEASE">Land Lease Deed</option>
                <option value="FIRE_NOC">Fire Safety NOC</option>
                <option value="FDR">FDR Bank Guarantee</option>
                <option value="BUILDING_PLAN">Approved Building Plan</option>
                <option value="LAND_TITLE">Land Title Certificate</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-slate-500 font-medium text-[11px]">Urgency:</span>
              <select
                value={selectedUrgency}
                onChange={(e) => setSelectedUrgency(e.target.value)}
                className="p-1.5 border border-slate-200 rounded text-xs focus:ring-1 focus:ring-blue-700"
              >
                <option value="ALL">All Urgency States</option>
                <option value="EXPIRED">Expired</option>
                <option value="CRITICAL">Critical &le;30d</option>
                <option value="EXPIRING_SOON">Expiring &le;60d</option>
                <option value="VALID">Valid</option>
              </select>
            </div>
          </div>
        </div>

        {/* Documents Table */}
        <Card className="border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-4">Institution & Application</th>
                  <th className="py-2.5 px-3">Document Title & Type</th>
                  <th className="py-2.5 px-3">Region</th>
                  <th className="py-2.5 px-3">Version</th>
                  <th className="py-2.5 px-3">Expiry Date & Countdown</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-400">Loading document watchtower...</td>
                  </tr>
                ) : filteredDocs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500">No documents matching filters.</td>
                  </tr>
                ) : (
                  filteredDocs.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-900">{doc.institution_name}</div>
                        <div className="text-[11px] text-slate-500 mt-0.5 font-mono">
                          {doc.application_number}
                        </div>
                      </td>

                      <td className="py-3 px-3">
                        <div className="font-medium text-slate-800 line-clamp-1">{doc.title}</div>
                        <span className="inline-block mt-0.5 px-1.5 py-0.2 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                          {doc.document_type}
                        </span>
                      </td>

                      <td className="py-3 px-3">
                        <span className="text-slate-700">{doc.region_name}</span>
                      </td>

                      <td className="py-3 px-3">
                        <span className="inline-flex items-center gap-1 font-mono font-bold text-xs text-blue-900 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-200">
                          <Layers className="w-3 h-3 text-blue-600" />
                          v{doc.version}
                        </span>
                      </td>

                      <td className="py-3 px-3">
                        <div className="font-mono text-[11px] font-medium text-slate-800">
                          {new Date(doc.expiry_date).toLocaleDateString()}
                        </div>
                        <div className="mt-0.5">
                          {doc.days_to_expiry < 0 ? (
                            <span className="text-[10px] font-bold text-rose-700 flex items-center gap-0.5">
                              <AlertCircle className="w-2.5 h-2.5" />
                              Expired {Math.abs(doc.days_to_expiry)}d ago
                            </span>
                          ) : (
                            <span className={`text-[10px] font-medium ${
                              doc.days_to_expiry <= 30 ? 'text-rose-700 font-bold' : doc.days_to_expiry <= 60 ? 'text-amber-700' : 'text-slate-500'
                            }`}>
                              {doc.days_to_expiry}d left
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="py-3 px-3">
                        {getUrgencyBadge(doc.urgency, doc.status)}
                      </td>

                      <td className="py-3 px-4 text-right">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => openDrawer(doc)}
                          className="h-7 text-xs border-emerald-600 text-emerald-700 hover:bg-emerald-50"
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

        {/* Sliding Audit & Renewal Drawer */}
        {drawerOpen && selectedDoc && (
          <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/50 backdrop-blur-sm">
            <div className="bg-white w-full max-w-xl h-full shadow-2xl flex flex-col border-l border-slate-200 overflow-hidden animate-in slide-in-from-right duration-200">
              {/* Drawer Header */}
              <div className="bg-slate-900 text-white px-5 py-4 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-sm flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    Document Lifecycle & Renewal Verification
                  </h3>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    {selectedDoc.institution_name} • {selectedDoc.title}
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
                {/* Active Document Card */}
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] uppercase font-bold text-slate-500">Active Record</span>
                    <span className="font-mono text-xs font-bold text-blue-900 bg-blue-100 px-2 py-0.5 rounded">
                      Version {selectedDoc.version}
                    </span>
                  </div>

                  <div className="font-bold text-sm text-slate-900">{selectedDoc.title}</div>
                  <div className="text-slate-600 text-xs">Type: <strong>{selectedDoc.document_type}</strong></div>

                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-200 text-[11px]">
                    <div>
                      <span className="text-slate-500 block">Expiry Date:</span>
                      <strong className="text-slate-800 font-mono">{new Date(selectedDoc.expiry_date).toLocaleDateString()}</strong>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Current Status:</span>
                      {getUrgencyBadge(selectedDoc.urgency, selectedDoc.status)}
                    </div>
                  </div>

                  {selectedDoc.file_id && (
                    <div className="pt-2 flex justify-end">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => filesApi.downloadFile(selectedDoc.file_id!, selectedDoc.file_name || undefined)}
                        className="h-6 text-[10px] border-slate-300 hover:bg-slate-100"
                      >
                        <Download className="w-3 h-3 mr-1" />
                        Download Certificate (v{selectedDoc.version})
                      </Button>
                    </div>
                  )}
                </div>

                {/* Renewal Pending Notice */}
                {selectedDoc.status === 'RENEWAL_SUBMITTED' && (
                  <div className="p-3 bg-amber-50 border border-amber-300 rounded-lg text-amber-900 space-y-1">
                    <div className="font-bold flex items-center gap-1.5 text-xs">
                      <AlertTriangle className="w-4 h-4 text-amber-700" />
                      Renewal Certificate Submitted by Institution
                    </div>
                    <p className="text-[11px] leading-relaxed">
                      The institution uploaded a renewal certificate for this document. Status shows <em>"Renewal submitted, awaiting verification"</em>. Linked expiry alerts remain active until an officer formally approves this renewal.
                    </p>
                  </div>
                )}

                {/* Officer Renewal Verification Controls */}
                {selectedDoc.status === 'RENEWAL_SUBMITTED' && (
                  <form onSubmit={handleVerifyRenewal} className="space-y-3 pt-3 border-t border-slate-200">
                    <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                      <FileCheck className="w-3.5 h-3.5 text-blue-700" />
                      Officer Verification Decision
                    </h4>

                    <div className="grid grid-cols-2 gap-2">
                      <label className={`p-2.5 rounded-lg border text-center cursor-pointer transition-all ${
                        verifyAction === 'APPROVE'
                          ? 'border-emerald-500 bg-emerald-50 text-emerald-900 font-bold ring-1 ring-emerald-400'
                          : 'border-slate-200 bg-white hover:bg-slate-50'
                      }`}>
                        <input
                          type="radio"
                          name="action"
                          className="sr-only"
                          checked={verifyAction === 'APPROVE'}
                          onChange={() => setVerifyAction('APPROVE')}
                        />
                        <CheckCircle2 className="w-4 h-4 mx-auto mb-1 text-emerald-700" />
                        <span className="text-[11px] block">Approve Renewal</span>
                      </label>

                      <label className={`p-2.5 rounded-lg border text-center cursor-pointer transition-all ${
                        verifyAction === 'REJECT'
                          ? 'border-rose-500 bg-rose-50 text-rose-900 font-bold ring-1 ring-rose-400'
                          : 'border-slate-200 bg-white hover:bg-slate-50'
                      }`}>
                        <input
                          type="radio"
                          name="action"
                          className="sr-only"
                          checked={verifyAction === 'REJECT'}
                          onChange={() => setVerifyAction('REJECT')}
                        />
                        <XCircle className="w-4 h-4 mx-auto mb-1 text-rose-700" />
                        <span className="text-[11px] block">Reject Renewal</span>
                      </label>
                    </div>

                    {verifyAction === 'APPROVE' && (
                      <div>
                        <label className="font-semibold text-slate-700 block mb-1">
                          Approved New Expiry Date:
                        </label>
                        <input
                          type="date"
                          value={approvedExpiryDate}
                          onChange={(e) => setApprovedExpiryDate(e.target.value)}
                          className="w-full p-2 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-blue-700"
                          required
                        />
                      </div>
                    )}

                    <div>
                      <label className="font-semibold text-slate-700 block mb-1">
                        Audit Findings & Verification Remarks:
                      </label>
                      <textarea
                        rows={2}
                        value={verifyRemarks}
                        onChange={(e) => setVerifyRemarks(e.target.value)}
                        placeholder="Certificate verified against state registry or issuing bank..."
                        className="w-full p-2 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-blue-700"
                        required={verifyAction === 'REJECT'}
                      />
                    </div>

                    <Button
                      type="submit"
                      size="sm"
                      disabled={actionLoading}
                      className={`w-full text-white ${
                        verifyAction === 'APPROVE' ? 'bg-emerald-700 hover:bg-emerald-800' : 'bg-rose-700 hover:bg-rose-800'
                      }`}
                    >
                      {actionLoading ? 'Recording...' : `Confirm ${verifyAction} & Resolve Alerts`}
                    </Button>
                  </form>
                )}

                {/* Complete Multi-Version History Chain */}
                <div className="space-y-3 pt-3 border-t border-slate-200">
                  <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                    <History className="w-3.5 h-3.5 text-slate-600" />
                    Superseded Version History & Audit Trail
                  </h4>

                  {selectedDoc.versions && selectedDoc.versions.length > 0 ? (
                    <div className="space-y-2">
                      {selectedDoc.versions.map((ver) => (
                        <div
                          key={ver.id}
                          className={`p-2.5 rounded-lg border text-xs space-y-1 ${
                            ver.version === selectedDoc.version
                              ? 'border-blue-300 bg-blue-50/40'
                              : 'border-slate-200 bg-slate-50/70'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-mono font-bold text-slate-900">
                              v{ver.version} • Status: {ver.status}
                            </span>
                            {ver.version !== selectedDoc.version && (
                              <Badge variant="secondary" className="text-[10px]">Superseded</Badge>
                            )}
                          </div>

                          <div className="text-[11px] text-slate-500">
                            Valid Until: <strong>{new Date(ver.expiry_date).toLocaleDateString()}</strong> • Uploaded: {new Date(ver.created_at).toLocaleDateString()}
                          </div>

                          {ver.remarks && (
                            <div className="text-[10px] text-slate-600 italic bg-white p-1 rounded border border-slate-200">
                              {ver.remarks}
                            </div>
                          )}

                          {ver.file_id && (
                            <div className="pt-1 flex justify-end">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => filesApi.downloadFile(ver.file_id!, ver.file_name || undefined)}
                                className="h-5 text-[10px] text-blue-700 hover:bg-blue-100"
                              >
                                Download v{ver.version} File
                              </Button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-slate-400 text-xs italic">Initial version v1 (no prior revisions).</div>
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
