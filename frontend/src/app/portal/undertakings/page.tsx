'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  undertakingsApi,
  UndertakingItem,
  filesApi,
} from '@/lib/api';
import {
  ClipboardList,
  Upload,
  Clock,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Download,
  AlertCircle,
  History,
} from 'lucide-react';

export default function InstitutionUndertakingsPage() {
  const { scope } = useAuth();
  const [undertakings, setUndertakings] = useState<UndertakingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Upload modal state
  const [selectedItem, setSelectedItem] = useState<UndertakingItem | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [uploadRemarks, setUploadRemarks] = useState('');
  const [uploading, setUploading] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await undertakingsApi.list();
      setUndertakings(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load undertakings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const openUploadModal = (item: UndertakingItem) => {
    setSelectedItem(item);
    setEvidenceFile(null);
    setUploadRemarks('');
    setShowUploadModal(true);
  };

  const handleUploadEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem || !evidenceFile) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', evidenceFile);
      if (uploadRemarks) formData.append('remarks', uploadRemarks);

      await undertakingsApi.uploadEvidence(selectedItem.id, formData);
      setSuccessMsg(`✓ Evidence uploaded for condition: ${selectedItem.title}`);
      setShowUploadModal(false);
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to upload evidence file');
    } finally {
      setUploading(false);
    }
  };

  const getStatusBadge = (status: string, isEscalated: boolean) => {
    if (isEscalated) {
      return (
        <Badge variant="destructive" className="animate-pulse">
          Escalated to Council
        </Badge>
      );
    }

    switch (status) {
      case 'PENDING':
        return <Badge variant="secondary">Pending Evidence</Badge>;
      case 'SUBMITTED':
        return <Badge variant="info">Evidence Submitted (Awaiting Officer Audit)</Badge>;
      case 'VERIFIED':
        return <Badge variant="success">Verified Compliant</Badge>;
      case 'REJECTED':
        return <Badge variant="destructive">Rejected (Resubmission Required)</Badge>;
      case 'NEEDS_MORE_EVIDENCE':
        return <Badge variant="warning">Needs More Evidence</Badge>;
      case 'OVERDUE':
        return <Badge variant="destructive">Overdue</Badge>;
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
              My Statutory Undertakings & Conditions
            </h1>
            <p className="text-xs text-slate-500">
              Submit compliance documentation and evidence files before regulatory deadlines.
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

        {/* Main List */}
        <div className="space-y-3">
          {loading ? (
            <div className="py-12 text-center text-slate-400 text-xs">Loading institutional undertakings...</div>
          ) : undertakings.length === 0 ? (
            <Card className="p-8 text-center text-slate-400 text-xs">
              No statutory undertakings registered for your institution.
            </Card>
          ) : (
            undertakings.map((item) => (
              <Card key={item.id} className="border-slate-200 bg-white p-4 shadow-sm space-y-3">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-sm text-slate-900">{item.title}</h3>
                      {getStatusBadge(item.status, item.is_escalated)}
                    </div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      Application: <span className="font-mono">{item.application_number}</span>
                      {item.condition_clause && <span> • Clause: {item.condition_clause} (sample reference)</span>}
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="text-xs font-mono font-medium text-slate-700">
                      Due: {new Date(item.due_date).toLocaleDateString()}
                    </div>
                    {item.status !== 'VERIFIED' && (
                      <div className="mt-0.5">
                        {item.is_overdue ? (
                          <span className="text-[10px] font-bold text-rose-700 flex items-center justify-end gap-1">
                            <AlertCircle className="w-2.5 h-2.5" />
                            Overdue by {Math.abs(item.days_remaining)} days
                          </span>
                        ) : (
                          <span className="text-[10px] text-amber-700 font-medium">
                            {item.days_remaining} days left to submit
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed">{item.description}</p>

                {/* Officer Remarks / Feedback Banner */}
                {item.latest_rejection_remark && (
                  <div className="p-2.5 bg-rose-50 border border-rose-200 rounded text-rose-900 text-xs">
                    <strong>Scrutiny Officer Remark:</strong> {item.latest_rejection_remark}
                  </div>
                )}

                {/* Uploaded Evidence Files */}
                <div className="space-y-1.5 pt-2 border-t border-slate-100">
                  <div className="text-[10px] uppercase font-bold text-slate-500">
                    Uploaded Evidence Files ({item.evidence_files?.length || 0})
                  </div>
                  {item.evidence_files && item.evidence_files.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {item.evidence_files.map((file) => (
                        <div key={file.id} className="p-2 bg-slate-50 border border-slate-200 rounded flex items-center justify-between text-xs">
                          <div className="flex items-center gap-2 truncate">
                            <FileText className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                            <span className="truncate">{file.original_filename}</span>
                          </div>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => filesApi.downloadFile(file.id, file.original_filename)}
                            className="h-6 text-[10px] text-blue-700 hover:bg-blue-100"
                          >
                            <Download className="w-3 h-3 mr-1" />
                            View
                          </Button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-slate-400 text-xs italic">No evidence uploaded yet.</div>
                  )}
                </div>

                {/* Actions */}
                {item.status !== 'VERIFIED' && (
                  <div className="pt-2 flex justify-end">
                    <Button
                      size="sm"
                      onClick={() => openUploadModal(item)}
                      className="bg-indigo-700 hover:bg-indigo-800 text-white text-xs"
                    >
                      <Upload className="w-3.5 h-3.5 mr-1.5" />
                      Upload Evidence Document
                    </Button>
                  </div>
                )}
              </Card>
            ))
          )}
        </div>

        {/* Modal: Upload Evidence */}
        {showUploadModal && selectedItem && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full border border-slate-200 overflow-hidden">
              <div className="bg-slate-900 text-white px-4 py-3 flex items-center justify-between">
                <h3 className="font-semibold text-sm flex items-center gap-2">
                  <Upload className="w-4 h-4 text-blue-400" />
                  Upload Compliance Evidence
                </h3>
                <button onClick={() => setShowUploadModal(false)} className="text-slate-400 hover:text-white">&times;</button>
              </div>

              <form onSubmit={handleUploadEvidence} className="p-4 space-y-3 text-xs">
                <div>
                  <div className="font-bold text-slate-800 text-xs mb-1">{selectedItem.title}</div>
                  <p className="text-slate-500 text-[11px]">{selectedItem.description}</p>
                </div>

                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Select File (PDF, PNG, JPG &le; 10MB):</label>
                  <input
                    type="file"
                    accept=".pdf,.png,.jpg"
                    onChange={(e) => setEvidenceFile(e.target.files ? e.target.files[0] : null)}
                    className="w-full p-1.5 border border-slate-300 rounded text-xs"
                    required
                  />
                </div>

                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Institution Remarks / Clarification:</label>
                  <textarea
                    rows={3}
                    value={uploadRemarks}
                    onChange={(e) => setUploadRemarks(e.target.value)}
                    placeholder="Provide context regarding the uploaded proof..."
                    className="w-full p-2 border border-slate-300 rounded text-xs"
                  />
                </div>

                <div className="p-2 bg-blue-50 border border-blue-200 rounded text-blue-900 text-[11px]">
                  <strong>Submission Notice:</strong> Submitting evidence changes state to <em>Submitted</em> for regional officer verification.
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                  <Button type="button" variant="outline" size="sm" onClick={() => setShowUploadModal(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" size="sm" disabled={uploading || !evidenceFile} className="bg-indigo-700 hover:bg-indigo-800 text-white">
                    {uploading ? 'Uploading...' : 'Submit Evidence File'}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
