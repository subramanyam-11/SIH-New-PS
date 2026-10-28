'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  applicationsApi,
  ApplicationItem,
  ApplicationDetail,
  undertakingsApi,
  UndertakingItem,
  documentsApi,
  DocumentItem,
  filesApi,
} from '@/lib/api';
import {
  Building,
  FileText,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Upload,
  Calendar,
  Layers,
  Award,
  ShieldCheck,
  ClipboardList,
  Mail,
  PlusCircle,
  FileCheck,
  ChevronRight,
  Info,
} from 'lucide-react';

export default function InstitutionPortalPage() {
  const { scope } = useAuth();
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [selectedApp, setSelectedApp] = useState<ApplicationDetail | null>(null);
  const [undertakings, setUndertakings] = useState<UndertakingItem[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Sample order modal
  const [showOrderModal, setShowOrderModal] = useState(false);

  // New application modal
  const [showNewAppModal, setShowNewAppModal] = useState(false);
  const [newProgram, setNewProgram] = useState('Engineering & Technology');
  const [newAcademicYear, setNewAcademicYear] = useState('2026-27');
  const [submittingApp, setSubmittingApp] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      const [apps, uts, docs] = await Promise.all([
        applicationsApi.list(),
        undertakingsApi.list(),
        documentsApi.list(),
      ]);
      setApplications(apps.applications);
      setUndertakings(uts);
      setDocuments(docs);

      if (apps.applications.length > 0) {
        const detail = await applicationsApi.get(apps.applications[0].id);
        setSelectedApp(detail);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load institutional records');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSelectApp = async (id: number) => {
    try {
      const detail = await applicationsApi.get(id);
      setSelectedApp(detail);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to load application details');
    }
  };

  const handleCreateApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scope?.institution_id) return;
    setSubmittingApp(true);
    try {
      await applicationsApi.create({
        institution_id: scope.institution_id,
        category_id: 1,
        stage_path_id: 1,
      });
      setSuccessMsg('✓ New application submitted successfully to Regional Office scrutiny desk.');
      setShowNewAppModal(false);
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to submit application');
    } finally {
      setSubmittingApp(false);
    }
  };

  return (
    <AppShell>
      <div className="space-y-5">
        {/* Institutional Welcome Card */}
        <div className="bg-gradient-to-r from-slate-900 to-blue-950 text-white rounded-lg p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] uppercase font-bold tracking-wider text-blue-300">
                AICTE Official Institution Portal
              </span>
              <span className="text-slate-400">•</span>
              <Badge variant="outline" className="border-blue-400 text-blue-200 text-[10px]">
                Applicant Self-Service Desk
              </Badge>
            </div>
            <h1 className="text-xl font-bold tracking-tight text-white">
              {scope?.institution_name || 'Apex Institute of Technology'}
            </h1>
            <p className="text-xs text-slate-300 mt-1">
              Authorized User: <strong>{scope?.full_name}</strong> | Regional Desk: <strong>{scope?.region_name || 'Northern RO'}</strong>
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              onClick={() => setShowNewAppModal(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white shadow-sm text-xs"
            >
              <PlusCircle className="w-3.5 h-3.5 mr-1.5" />
              Submit New Application
            </Button>
          </div>
        </div>

        {/* Success Alert */}
        {successMsg && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-900 rounded text-xs flex items-center justify-between">
            <span>{successMsg}</span>
            <button onClick={() => setSuccessMsg('')} className="text-emerald-700 font-bold">&times;</button>
          </div>
        )}

        {/* Quick Stat Tiles */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <Card className="p-3 bg-white border-slate-200">
            <div className="text-[11px] font-semibold text-slate-500 uppercase">My Applications</div>
            <div className="text-xl font-bold text-slate-900 mt-0.5">{applications.length}</div>
            <div className="text-[10px] text-slate-400 mt-1">Active regulatory submissions</div>
          </Card>

          <Card className="p-3 bg-white border-slate-200">
            <div className="text-[11px] font-semibold text-slate-500 uppercase">Statutory Undertakings</div>
            <div className="text-xl font-bold text-slate-900 mt-0.5">
              {undertakings.length}
              {undertakings.filter((u) => u.is_overdue && u.status !== 'VERIFIED').length > 0 && (
                <span className="text-xs text-rose-700 ml-1.5 font-normal">
                  ({undertakings.filter((u) => u.is_overdue && u.status !== 'VERIFIED').length} Overdue)
                </span>
              )}
            </div>
            <div className="text-[10px] text-slate-400 mt-1">
              <a href="/portal/undertakings" className="text-blue-700 font-semibold hover:underline">
                View & Upload Evidence &rarr;
              </a>
            </div>
          </Card>

          <Card className="p-3 bg-white border-slate-200">
            <div className="text-[11px] font-semibold text-slate-500 uppercase">Monitored Documents</div>
            <div className="text-xl font-bold text-slate-900 mt-0.5">{documents.length}</div>
            <div className="text-[10px] text-slate-400 mt-1">
              <a href="/portal/documents" className="text-emerald-700 font-semibold hover:underline">
                View Expiries & Renewals &rarr;
              </a>
            </div>
          </Card>
        </div>

        {/* Main Application Tracker */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left Column: Applications List */}
          <div className="space-y-3">
            <div className="font-bold text-xs text-slate-800 uppercase tracking-wider">
              Submitted Applications
            </div>

            {applications.map((app) => (
              <div
                key={app.id}
                onClick={() => handleSelectApp(app.id)}
                className={`p-3 rounded-lg border transition-all cursor-pointer ${
                  selectedApp?.id === app.id
                    ? 'border-blue-600 bg-blue-50/40 ring-1 ring-blue-500 shadow-xs'
                    : 'border-slate-200 bg-white hover:border-slate-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-xs text-slate-900">{app.application_number}</span>
                  <Badge variant={app.status === 'APPROVED' ? 'success' : app.status === 'REJECTED' ? 'destructive' : 'info'} className="text-[10px]">
                    {app.status}
                  </Badge>
                </div>

                <div className="text-xs font-medium text-slate-700 mt-1">
                  Stage: <strong>{app.current_stage_name}</strong>
                </div>

                <div className="text-[11px] text-slate-500 mt-0.5">
                  Academic Year: {app.academic_year} • Path: {app.stage_path_name}
                </div>
              </div>
            ))}

            {applications.length === 0 && (
              <div className="p-4 bg-white border border-dashed border-slate-300 rounded text-center text-slate-400 text-xs">
                No active applications filed.
              </div>
            )}
          </div>

          {/* Right Column: Case Milestone Stepper & Details */}
          <div className="lg:col-span-2 space-y-4">
            {selectedApp ? (
              <Card className="border-slate-200 bg-white shadow-sm p-4 space-y-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between pb-3 border-b border-slate-200 gap-2">
                  <div>
                    <div className="font-mono text-sm font-bold text-slate-900">{selectedApp.application_number}</div>
                    <div className="text-xs text-slate-500">
                      Current Stage: <span className="font-semibold text-blue-900">{selectedApp.current_stage.name}</span>
                    </div>
                  </div>

                  {selectedApp.status === 'APPROVED' && selectedApp.approval_letter_data && (
                    <Button
                      size="sm"
                      onClick={() => setShowOrderModal(true)}
                      className="bg-emerald-700 hover:bg-emerald-800 text-white text-xs"
                    >
                      <Award className="w-3.5 h-3.5 mr-1.5" />
                      View Sample Order (LoA)
                    </Button>
                  )}
                </div>

                {/* Milestone Stepper */}
                <div className="space-y-2">
                  <div className="text-[11px] font-bold text-slate-600 uppercase">Statutory Progress Stepper</div>
                  <div className="grid grid-cols-4 gap-2 text-center text-xs">
                    {selectedApp.stage_path.stage_sequence.map((stageCode, idx) => {
                      const isCurrent = stageCode === selectedApp.current_stage.code;
                      const isPassed = idx < selectedApp.stage_path.stage_sequence.indexOf(selectedApp.current_stage.code) || selectedApp.status === 'APPROVED';

                      return (
                        <div
                          key={stageCode}
                          className={`p-2.5 rounded-lg border text-xs ${
                            isCurrent
                              ? 'border-blue-600 bg-blue-50 text-blue-900 font-bold ring-1 ring-blue-400'
                              : isPassed
                              ? 'border-emerald-300 bg-emerald-50 text-emerald-900'
                              : 'border-slate-200 bg-slate-50 text-slate-400'
                          }`}
                        >
                          <div className="text-[10px] font-mono mb-0.5">Stage {idx + 1}</div>
                          <div className="truncate">{stageCode.replace(/_/g, ' ')}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Active Deficiency Notices / Compliance Flags */}
                {selectedApp.case_summary?.compliance_flags && selectedApp.case_summary.compliance_flags.length > 0 && (
                  <div className="p-3 bg-amber-50 border border-amber-300 rounded-lg text-amber-900 space-y-1.5">
                    <div className="font-bold flex items-center gap-1.5 text-xs">
                      <AlertTriangle className="w-4 h-4 text-amber-700" />
                      Statutory Deficiencies / Scrutiny Flags
                    </div>
                    <p className="text-[11px] leading-relaxed">
                      The regional scrutiny officer has noted compliance deficiencies. Please review and address them:
                    </p>
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {selectedApp.case_summary.compliance_flags.map((tag) => (
                        <span key={tag} className="px-2 py-0.5 bg-white border border-amber-300 rounded text-[11px] font-semibold text-amber-900">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Statutory SLA Info */}
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase font-semibold">Stage Deadline</span>
                    <strong className="text-slate-800 font-mono">
                      {selectedApp.stage_due_date ? new Date(selectedApp.stage_due_date).toLocaleDateString() : 'N/A'}
                    </strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase font-semibold">SLA Ageing Bucket</span>
                    <Badge variant={selectedApp.ageing_bucket === 'OVERDUE' ? 'destructive' : selectedApp.ageing_bucket === 'NEAR_DUE' ? 'warning' : 'success'}>
                      {selectedApp.ageing_bucket}
                    </Badge>
                  </div>
                </div>

                {/* Official Communications Sent to Institution */}
                <div className="space-y-2 pt-2 border-t border-slate-200">
                  <div className="text-[11px] font-bold text-slate-600 uppercase flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5 text-slate-500" />
                    Formal Notices & Letters Dispatched
                  </div>

                  {selectedApp.communications && selectedApp.communications.length > 0 ? (
                    <div className="space-y-1.5">
                      {selectedApp.communications.map((comm) => (
                        <div key={comm.id} className="p-2.5 bg-slate-50 border border-slate-200 rounded text-xs">
                          <div className="flex items-center justify-between font-semibold text-slate-800">
                            <span>{comm.subject}</span>
                            <span className="text-[10px] text-slate-400 font-normal">
                              {new Date(comm.created_at).toLocaleDateString()}
                            </span>
                          </div>
                          <div className="text-[11px] text-slate-600 mt-1 whitespace-pre-wrap font-sans">
                            {comm.body}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-slate-400 text-xs italic py-2">No formal notices dispatched yet.</div>
                  )}
                </div>
              </Card>
            ) : (
              <div className="p-8 bg-white border border-slate-200 rounded text-center text-slate-400 text-xs">
                Select an application from the left to inspect stage tracker and notices.
              </div>
            )}
          </div>
        </div>

        {/* Modal: Submit New Application */}
        {showNewAppModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full border border-slate-200 overflow-hidden">
              <div className="bg-slate-900 text-white px-4 py-3 flex items-center justify-between">
                <h3 className="font-semibold text-sm flex items-center gap-2">
                  <PlusCircle className="w-4 h-4 text-blue-400" />
                  Submit New Approval Application
                </h3>
                <button onClick={() => setShowNewAppModal(false)} className="text-slate-400 hover:text-white">&times;</button>
              </div>

              <form onSubmit={handleCreateApplication} className="p-4 space-y-3 text-xs">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Academic Year:</label>
                  <input
                    type="text"
                    value={newAcademicYear}
                    onChange={(e) => setNewAcademicYear(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded text-xs"
                    required
                  />
                </div>

                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Discipline / Program:</label>
                  <select
                    value={newProgram}
                    onChange={(e) => setNewProgram(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded text-xs"
                  >
                    <option value="Engineering & Technology">Engineering & Technology</option>
                    <option value="Management (MBA/PGDM)">Management (MBA/PGDM)</option>
                    <option value="Pharmacy">Pharmacy</option>
                    <option value="Architecture & Planning">Architecture & Planning</option>
                    <option value="Applied Arts & Crafts">Applied Arts & Crafts</option>
                  </select>
                </div>

                <div className="p-2.5 bg-blue-50 border border-blue-200 rounded text-blue-900 text-[11px]">
                  <strong>Applicant Declaration:</strong> Submitting this formal application initiates stage 1 scrutiny at the regional desk under AICTE Approval Process Handbook (sample reference).
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                  <Button type="button" variant="outline" size="sm" onClick={() => setShowNewAppModal(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" size="sm" disabled={submittingApp} className="bg-blue-800 hover:bg-blue-900 text-white">
                    {submittingApp ? 'Submitting...' : 'File Application'}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal: Sample Order Viewer */}
        {showOrderModal && selectedApp?.approval_letter_data && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
            <div className="bg-white rounded-lg shadow-2xl max-w-2xl w-full border border-slate-300 overflow-hidden flex flex-col max-h-[90vh]">
              <div className="bg-slate-900 text-white px-4 py-3 flex items-center justify-between">
                <h3 className="font-semibold text-sm flex items-center gap-2">
                  <Award className="w-4 h-4 text-emerald-400" />
                  View Sample Order (LoA)
                </h3>
                <button onClick={() => setShowOrderModal(false)} className="text-slate-400 hover:text-white">&times;</button>
              </div>

              <div className="p-8 overflow-y-auto space-y-6 text-xs text-slate-800 relative bg-white font-serif">
                {/* SAMPLE WATERMARK */}
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none select-none opacity-[0.08] rotate-[-30deg]">
                  <span className="text-4xl font-extrabold text-slate-900 text-center leading-normal uppercase">
                    {selectedApp.approval_letter_data.watermark}
                  </span>
                </div>

                <div className="text-center border-b-2 border-slate-900 pb-4 space-y-1">
                  <div className="font-bold text-base text-slate-900 uppercase tracking-wider">
                    All India Council for Technical Education
                  </div>
                  <div className="text-[11px] text-slate-600">
                    Nelson Mandela Marg, Vasant Kunj, New Delhi - 110070
                  </div>
                </div>

                <div className="flex justify-between text-xs font-mono">
                  <span>Order Ref: {selectedApp.approval_letter_data.letter_number}</span>
                  <span>Date: {new Date(selectedApp.approval_letter_data.issued_at).toLocaleDateString()}</span>
                </div>

                <div className="space-y-2">
                  <div className="font-bold">To: The Principal / Director,</div>
                  <div>{selectedApp.approval_letter_data.institution_name}</div>
                </div>

                <div className="font-bold text-center underline uppercase">
                  Subject: Grant of Extension of Approval (EoA) / Letter of Approval (LoA) for Academic Year {selectedApp.academic_year}
                </div>

                <p className="leading-relaxed">
                  In terms of the provisions under the All India Council for Technical Education (Grant of Approvals for Technical Institutions) Regulations, and based on the recommendations of the Executive Committee, approval of the Council is hereby conveyed.
                </p>

                <div className="pt-4 border-t border-slate-200 text-right">
                  <div className="font-bold">Member Secretary / Competent Authority</div>
                  <div className="text-[11px] text-slate-500">All India Council for Technical Education</div>
                </div>
              </div>

              <div className="p-3 bg-slate-50 border-t border-slate-200 flex justify-end">
                <Button size="sm" variant="outline" onClick={() => setShowOrderModal(false)}>
                  Close Sample Order
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
