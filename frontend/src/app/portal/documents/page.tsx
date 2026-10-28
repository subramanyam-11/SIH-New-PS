'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  documentsApi,
  DocumentItem,
  filesApi,
} from '@/lib/api';
import {
  ShieldCheck,
  ShieldAlert,
  Upload,
  Clock,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Download,
  AlertCircle,
  Layers,
  History,
} from 'lucide-react';

export default function InstitutionDocumentsPage() {
  const { scope } = useAuth();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Upload modal state
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [renewalFile, setRenewalFile] = useState<File | null>(null);
  const [newExpiryDate, setNewExpiryDate] = useState('');
  const [uploadRemarks, setUploadRemarks] = useState('');
  const [uploading, setUploading] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await documentsApi.list();
      setDocuments(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load institutional documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const openUploadModal = (doc: DocumentItem) => {
    setSelectedDoc(doc);
    setRenewalFile(null);
    setNewExpiryDate('');
    setUploadRemarks('');
    setShowUploadModal(true);
  };

  const handleUploadRenewal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDoc || !renewalFile || !newExpiryDate) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', renewalFile);
      formData.append('new_expiry_date', newExpiryDate);
      if (uploadRemarks) formData.append('remarks', uploadRemarks);

      await documentsApi.uploadRenewal(selectedDoc.id, formData);
      setSuccessMsg(`✓ Renewal submitted for ${selectedDoc.title}. Status: Renewal submitted, awaiting verification.`);
      setShowUploadModal(false);
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to upload renewal document');
    } finally {
      setUploading(false);
    }
  };

  const getUrgencyBadge = (urgency: string, status: string) => {
    if (status === 'RENEWAL_SUBMITTED') {
      return (
        <Badge variant="warning" className="bg-amber-100 text-amber-900 border-amber-300">
          Renewal submitted, awaiting verification
        </Badge>
      );
    }

    switch (urgency) {
      case 'EXPIRED':
        return <Badge variant="destructive">Expired</Badge>;
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
              Statutory Documents & Renewal Manager
            </h1>
            <p className="text-xs text-slate-500">
              Track statutory certificate expirations and submit renewed certificates for officer verification.
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

        {/* Documents Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {loading ? (
            <div className="col-span-2 py-12 text-center text-slate-400 text-xs">Loading institutional documents...</div>
          ) : documents.length === 0 ? (
            <Card className="col-span-2 p-8 text-center text-slate-400 text-xs">
              No statutory documents currently registered for your institution.
            </Card>
          ) : (
            documents.map((doc) => (
              <Card key={doc.id} className="border-slate-200 bg-white p-4 shadow-sm space-y-3 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500">{doc.document_type}</span>
                      <h3 className="font-bold text-sm text-slate-900">{doc.title}</h3>
                    </div>
                    <span className="font-mono text-xs font-bold text-blue-900 bg-blue-100 px-2 py-0.5 rounded">
                      v{doc.version}
                    </span>
                  </div>

                  <div className="pt-2 space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Current Validity Expiry:</span>
                      <strong className="font-mono text-slate-800">{new Date(doc.expiry_date).toLocaleDateString()}</strong>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Status:</span>
                      {getUrgencyBadge(doc.urgency, doc.status)}
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Validity Remaining:</span>
                      {doc.days_to_expiry < 0 ? (
                        <span className="text-rose-700 font-bold flex items-center gap-1">
                          <AlertCircle className="w-3 h-3" />
                          Expired {Math.abs(doc.days_to_expiry)} days ago
                        </span>
                      ) : (
                        <span className={`font-semibold ${
                          doc.days_to_expiry <= 30 ? 'text-rose-700' : doc.days_to_expiry <= 60 ? 'text-amber-700' : 'text-emerald-700'
                        }`}>
                          {doc.days_to_expiry} days remaining
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Renewal State explanation */}
                  {doc.status === 'RENEWAL_SUBMITTED' && (
                    <div className="mt-3 p-2 bg-amber-50 border border-amber-200 rounded text-amber-900 text-[11px]">
                      A renewed certificate has been uploaded and is in regional review. Expiry alerts remain until approved.
                    </div>
                  )}
                </div>

                <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                  {doc.file_id ? (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => filesApi.downloadFile(doc.file_id!, doc.file_name || undefined)}
                      className="h-7 text-xs border-slate-300 hover:bg-slate-50"
                    >
                      <Download className="w-3 h-3 mr-1" />
                      View Certificate (v{doc.version})
                    </Button>
                  ) : <div />}

                  <Button
                    size="sm"
                    onClick={() => openUploadModal(doc)}
                    className="h-7 text-xs bg-emerald-700 hover:bg-emerald-800 text-white"
                  >
                    <Upload className="w-3 h-3 mr-1" />
                    Upload Renewal
                  </Button>
                </div>
              </Card>
            ))
          )}
        </div>

        {/* Modal: Upload Renewal */}
        {showUploadModal && selectedDoc && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full border border-slate-200 overflow-hidden">
              <div className="bg-slate-900 text-white px-4 py-3 flex items-center justify-between">
                <h3 className="font-semibold text-sm flex items-center gap-2">
                  <Upload className="w-4 h-4 text-emerald-400" />
                  Upload Document Renewal Certificate
                </h3>
                <button onClick={() => setShowUploadModal(false)} className="text-slate-400 hover:text-white">&times;</button>
              </div>

              <form onSubmit={handleUploadRenewal} className="p-4 space-y-3 text-xs">
                <div className="p-2.5 bg-slate-50 rounded border border-slate-200">
                  <div className="font-bold text-slate-800">{selectedDoc.title}</div>
                  <div className="text-[11px] text-slate-500">Current version: v{selectedDoc.version} • Expires: {new Date(selectedDoc.expiry_date).toLocaleDateString()}</div>
                </div>

                <div>
                  <label className="font-semibold text-slate-700 block mb-1">New Certificate Expiry Date:</label>
                  <input
                    type="date"
                    value={newExpiryDate}
                    onChange={(e) => setNewExpiryDate(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-blue-700"
                    required
                  />
                </div>

                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Renewal Certificate File (PDF, PNG, JPG &le; 10MB):</label>
                  <input
                    type="file"
                    accept=".pdf,.png,.jpg"
                    onChange={(e) => setRenewalFile(e.target.files ? e.target.files[0] : null)}
                    className="w-full p-1.5 border border-slate-300 rounded text-xs"
                    required
                  />
                </div>

                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Renewal Details / Authority Remarks:</label>
                  <textarea
                    rows={2}
                    value={uploadRemarks}
                    onChange={(e) => setUploadRemarks(e.target.value)}
                    placeholder="Issuing authority, renewal order number..."
                    className="w-full p-2 border border-slate-300 rounded text-xs"
                  />
                </div>

                <div className="p-2 bg-blue-50 border border-blue-200 rounded text-blue-900 text-[11px]">
                  <strong>Version Lifecycle Policy:</strong> Uploading creates a new version v{selectedDoc.version + 1} and marks v{selectedDoc.version} as <em>Superseded</em>.
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                  <Button type="button" variant="outline" size="sm" onClick={() => setShowUploadModal(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" size="sm" disabled={uploading || !renewalFile || !newExpiryDate} className="bg-emerald-700 hover:bg-emerald-800 text-white">
                    {uploading ? 'Uploading...' : 'Submit Renewal Certificate'}
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
