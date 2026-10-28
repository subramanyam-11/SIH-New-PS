'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { 
  applicationsApi, configApi, lookupApi,
  ApplicationDetail, StageHistoryItem, CommunicationItem, 
  DeficiencyTag, UserScope, ClockSegment 
} from '@/lib/api';
import { DecisionSupportBadge } from '@/components/ui/DecisionSupportBadge';
import { 
  FileText, ArrowLeft, Clock, AlertTriangle, CheckCircle2, 
  Send, RotateCcw, Award, CheckCircle, XCircle, Mail, Sparkles, 
  Building2, MapPin, User, ChevronRight, FileCheck, AlertCircle, PauseCircle, PlayCircle
} from 'lucide-react';

export default function ApplicationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const appId = parseInt(params.id as string, 10);

  const [scope, setScope] = useState<UserScope | null>(null);
  const [app, setApp] = useState<ApplicationDetail | null>(null);
  const [timeline, setTimeline] = useState<StageHistoryItem[]>([]);
  const [deficiencyTags, setDeficiencyTags] = useState<DeficiencyTag[]>([]);
  const [clockSegments, setClockSegments] = useState<ClockSegment[]>([]);
  const [clockTotals, setClockTotals] = useState<{ aicte_hours: number; inst_hours: number }>({ aicte_hours: 0, inst_hours: 0 });
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string>('');
  const [actionSuccess, setActionSuccess] = useState<string>('');

  // Modals
  const [showAdvanceModal, setShowAdvanceModal] = useState<boolean>(false);
  const [showReturnModal, setShowReturnModal] = useState<boolean>(false);
  const [showDecisionModal, setShowDecisionModal] = useState<boolean>(false);
  const [showLetterModal, setShowLetterModal] = useState<boolean>(false);
  const [showResponseModal, setShowResponseModal] = useState<boolean>(false);
  const [showCloseModal, setShowCloseModal] = useState<boolean>(false);

  // Form states
  const [advanceRemarks, setAdvanceRemarks] = useState<string>('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [returnRemarks, setReturnRemarks] = useState<string>('');
  const [decisionType, setDecisionType] = useState<'APPROVE' | 'REJECT'>('APPROVE');
  const [decisionRemarks, setDecisionRemarks] = useState<string>('');
  const [responseRemarks, setResponseRemarks] = useState<string>('');
  const [responseDocUrl, setResponseDocUrl] = useState<string>('');
  const [closureReason, setClosureReason] = useState<string>('ALL_CONDITIONS_MET');
  const [closureRemarks, setClosureRemarks] = useState<string>('');

  const loadCase = async () => {
    try {
      setLoading(true);
      const [scopeRes, appRes, timeRes, tagsRes, clockRes] = await Promise.all([
        lookupApi.getScope(),
        applicationsApi.get(appId),
        applicationsApi.getTimeline(appId),
        configApi.getDeficiencyTags(),
        applicationsApi.getClockSegments(appId).catch(() => ({ segments: [], total_aicte_hours: 0, total_institution_hours: 0, current_holder: 'WITH_AICTE' }))
      ]);
      setScope(scopeRes);
      setApp(appRes);
      setTimeline(timeRes);
      setDeficiencyTags(tagsRes);
      setClockSegments(clockRes.segments || []);
      setClockTotals({ aicte_hours: clockRes.total_aicte_hours || 0, inst_hours: clockRes.total_institution_hours || 0 });
    } catch (err: any) {
      console.error('Failed to load application dossier:', err);
      setActionError(err.response?.data?.detail || 'Failed to load case');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (appId) {
      loadCase();
    }
  }, [appId]);

  const handleAdvanceStage = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    setActionError('');
    try {
      const res = await applicationsApi.completeStage(appId, advanceRemarks);
      setActionSuccess(`✓ Stage advanced successfully: ${res.message}`);
      setShowAdvanceModal(false);
      setAdvanceRemarks('');
      await loadCase();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to advance stage');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReturnApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    setActionError('');
    try {
      const res = await applicationsApi.returnApplication(appId, selectedTags, returnRemarks);
      setActionSuccess(`✓ Deficiencies recorded: ${res.message}`);
      setShowReturnModal(false);
      setSelectedTags([]);
      setReturnRemarks('');
      await loadCase();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to return application');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRecordDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    setActionError('');
    try {
      await applicationsApi.recordDecision(appId, decisionType, decisionRemarks);
      setActionSuccess(`✓ Statutory decision recorded (${decisionType}). Sample order generated.`);
      setShowDecisionModal(false);
      setDecisionRemarks('');
      await loadCase();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to record decision');
    } finally {
      setActionLoading(false);
    }
  };

  const handleInstitutionResponse = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    setActionError('');
    try {
      await applicationsApi.respond(appId, {
        remarks: responseRemarks.trim(),
        document_url: responseDocUrl.trim() || undefined,
      });
      setActionSuccess('✓ Institution response submitted. Dossier holder moved to WITH_AICTE and re-entered re-scrutiny with fresh SLA.');
      setShowResponseModal(false);
      setResponseRemarks('');
      setResponseDocUrl('');
      await loadCase();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to submit response');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCloseApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    setActionError('');
    try {
      await applicationsApi.close(appId, {
        closure_reason: closureReason,
        closure_remarks: closureRemarks.trim() || undefined,
      });
      setActionSuccess(`✓ Case formally closed under reason: ${closureReason}. Open alerts resolved.`);
      setShowCloseModal(false);
      setClosureRemarks('');
      await loadCase();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to close case');
    } finally {
      setActionLoading(false);
    }
  };

  const handleMarkSent = async (commId: number) => {
    try {
      await applicationsApi.markCommunicationSent(appId, commId);
      await loadCase();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to mark communication as sent');
    }
  };

  const toggleTag = (code: string) => {
    if (selectedTags.includes(code)) {
      setSelectedTags(selectedTags.filter((t) => t !== code));
    } else {
      setSelectedTags([...selectedTags, code]);
    }
  };

  if (loading || !app) {
    return (
      <AppShell>
        <div className="py-20 text-center text-slate-400">
          <Clock className="w-8 h-8 animate-spin mx-auto mb-3 text-blue-700" />
          Loading statutory case dossier...
        </div>
      </AppShell>
    );
  }

  // Permission checks for action buttons
  const isAuthority = scope?.role === 'COMPETENT_AUTHORITY' || scope?.role === 'ADMIN';
  const isRegionalHead = (scope?.role === 'REGIONAL_HEAD' && scope.region_id === app.region_id) || scope?.role === 'ADMIN';
  const isResponsibleOfficer = (scope?.role === app.current_stage.responsible_role) && 
    (!scope?.region_id || scope.region_id === app.region_id);
  const isApplicantInst = scope?.role === 'INSTITUTION_USER' && scope.institution_id === app.institution_id;
  const isClosed = app.status === 'CLOSED' || app.case_holder === 'CLOSED';

  const canAdvance = !isClosed && app.status === 'IN_PROGRESS' && (
    (app.current_stage.code === 'RE_SCRUTINY' && (isApplicantInst || isRegionalHead || scope?.role === 'ADMIN')) ||
    (app.current_stage.code !== 'RE_SCRUTINY' && (isResponsibleOfficer || isRegionalHead || isAuthority))
  );

  const canReturn = !isClosed && app.status === 'IN_PROGRESS' && 
    (scope?.role === 'SCRUTINY_OFFICER' || isRegionalHead || scope?.role === 'ADMIN') &&
    (app.current_stage.code === 'SCRUTINY' || app.current_stage.code === 'SUBMITTED');

  const canDecide = !isClosed && app.status === 'IN_PROGRESS' && isAuthority && (
    app.current_stage.code === 'SCRUTINY' || 
    app.current_stage.code === 'EVC_COMPLETED' || 
    app.current_stage.code === 'SAC_SHC_REVIEW'
  );

  const canRespond = !isClosed && (app.case_holder === 'WITH_INSTITUTION') && (isApplicantInst || scope?.role === 'ADMIN');
  const canClose = (isAuthority || isRegionalHead || scope?.role === 'ADMIN') && !isClosed;

  const sequence = app.stage_path.stage_sequence;
  const currentStageIdx = sequence.indexOf(app.current_stage.code);

  return (
    <AppShell>
      <div className="space-y-5">
        {/* Navigation & Status Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-4">
          <div className="space-y-1">
            <Link href="/applications" className="text-xs text-blue-700 hover:underline flex items-center gap-1 mb-1 font-medium">
              <ArrowLeft className="w-3.5 h-3.5" /> Back to Applications List
            </Link>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-slate-900 tracking-tight font-mono">
                {app.application_number}
              </h1>
              <Badge variant={app.status === 'APPROVED' ? 'success' : app.status === 'REJECTED' ? 'danger' : app.status === 'CLOSED' ? 'neutral' : 'info'}>
                {app.status.replace('_', ' ')}
              </Badge>
              {app.case_holder === 'WITH_INSTITUTION' ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300">
                  <PauseCircle className="w-3.5 h-3.5 text-amber-600" />
                  With Institution (Clock Paused)
                </span>
              ) : (app.case_holder === 'CLOSED' || app.status === 'CLOSED') ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-bold bg-slate-200 text-slate-800 border border-slate-300">
                  <CheckCircle className="w-3.5 h-3.5 text-slate-600" />
                  Case Closed ({app.closure_reason || 'Final'})
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                  <PlayCircle className="w-3.5 h-3.5 text-blue-600" />
                  With AICTE (Active)
                </span>
              )}
              {app.escalation_required && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                  ESCALATION REQUIRED (Revert Cap Exceeded)
                </span>
              )}
            </div>
            <p className="text-xs text-slate-600 flex flex-wrap items-center gap-2">
              <span className="font-semibold text-slate-900">{app.institution.name}</span>
              <span>•</span>
              <span>{app.region_name}</span>
              <span>•</span>
              <span className="text-slate-500">AY {app.academic_year}</span>
              <span>•</span>
              <span className="text-blue-800 font-medium">{app.category.title}</span>
              <span>•</span>
              <span className="text-slate-700 font-mono bg-slate-100 px-1.5 py-0.5 rounded">
                With AICTE: <strong>{clockTotals.aicte_hours || 0}h</strong>
              </span>
              <span className="text-amber-800 font-mono bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                With Inst: <strong>{clockTotals.inst_hours || 0}h</strong>
              </span>
            </p>
          </div>

          {/* Action Toolbar */}
          <div className="flex flex-wrap items-center gap-2">
            {canRespond && (
              <Button 
                size="sm" 
                onClick={() => setShowResponseModal(true)}
                className="bg-amber-600 hover:bg-amber-700 text-white shadow-sm"
              >
                <Send className="w-4 h-4 mr-1.5" />
                Submit Institution Response
              </Button>
            )}

            {canAdvance && (
              <Button 
                size="sm" 
                onClick={() => setShowAdvanceModal(true)}
                className="bg-blue-800 hover:bg-blue-900 text-white shadow-sm"
              >
                <CheckCircle2 className="w-4 h-4 mr-1.5" />
                {app.current_stage.code === 'RE_SCRUTINY' ? 'Submit Deficiency Clarification' : 'Advance Stage'}
              </Button>
            )}

            {canReturn && (
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => setShowReturnModal(true)}
                className="border-amber-400 text-amber-900 hover:bg-amber-50"
              >
                <RotateCcw className="w-4 h-4 mr-1.5 text-amber-600" />
                Raise Deficiencies / Revert
              </Button>
            )}

            {canDecide && (
              <Button 
                size="sm" 
                onClick={() => setShowDecisionModal(true)}
                className="bg-emerald-800 hover:bg-emerald-900 text-white shadow-sm"
              >
                <Award className="w-4 h-4 mr-1.5" />
                Record Statutory Decision
              </Button>
            )}

            {canClose && (
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => setShowCloseModal(true)}
                className="border-slate-400 text-slate-700 hover:bg-slate-100 shadow-sm"
              >
                <CheckCircle className="w-4 h-4 mr-1.5 text-slate-600" />
                Close Case
              </Button>
            )}

            {app.status === 'APPROVED' && (
              <Button 
                size="sm" 
                onClick={() => setShowLetterModal(true)}
                className="bg-emerald-700 hover:bg-emerald-800 text-white"
              >
                <FileCheck className="w-4 h-4 mr-1.5" />
                View Sample Order (LoA)
              </Button>
            )}
          </div>
        </div>

        {/* Global Feedback Banners */}
        {actionSuccess && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-900 rounded text-xs flex items-center justify-between">
            <span>{actionSuccess}</span>
            <button onClick={() => setActionSuccess('')} className="text-emerald-700 font-bold">&times;</button>
          </div>
        )}
        {actionError && (
          <div className="p-3 bg-rose-50 border border-rose-200 text-rose-900 rounded text-xs flex items-center justify-between">
            <span className="font-semibold">{actionError}</span>
            <button onClick={() => setActionError('')} className="text-rose-700 font-bold">&times;</button>
          </div>
        )}

        {/* Visual Pathway Stepper */}
        <Card className="border-slate-200 bg-white">
          <CardHeader className="py-2.5 px-4 bg-slate-50 border-b border-slate-100 flex flex-row items-center justify-between">
            <div className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
              <span>Path Sequence:</span>
              <span className="text-blue-800">{app.stage_path.name}</span>
            </div>
            <div className="text-[11px] text-slate-500">
              Current Stage: <strong className="text-slate-900">{app.current_stage.name}</strong>
            </div>
          </CardHeader>
          <CardContent className="p-4 overflow-x-auto">
            <div className="flex items-center min-w-[650px] justify-between">
              {sequence.map((stCode, idx) => {
                const isCurrent = (stCode === app.current_stage.code);
                const isPassed = currentStageIdx > idx || app.status === 'APPROVED' || app.status === 'REJECTED';
                const isUpcoming = currentStageIdx < idx && app.status === 'IN_PROGRESS';

                return (
                  <div key={stCode} className="flex items-center flex-1 last:flex-none">
                    <div className="flex flex-col items-center relative">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs border-2 transition-all ${
                        isCurrent
                          ? 'border-blue-700 bg-blue-50 text-blue-900 ring-4 ring-blue-100 animate-pulse'
                          : isPassed
                          ? 'border-emerald-600 bg-emerald-600 text-white'
                          : 'border-slate-300 bg-slate-100 text-slate-400'
                      }`}>
                        {isPassed ? <CheckCircle className="w-4 h-4" /> : idx + 1}
                      </div>
                      <span className={`text-[10px] font-medium text-center mt-1.5 max-w-[85px] leading-tight ${
                        isCurrent ? 'text-blue-900 font-bold' : isPassed ? 'text-slate-700' : 'text-slate-400'
                      }`}>
                        {stCode.replace('_', ' ')}
                      </span>
                    </div>
                    {idx < sequence.length - 1 && (
                      <div className={`flex-1 h-0.5 mx-2 ${
                        currentStageIdx > idx ? 'bg-emerald-500' : 'bg-slate-200'
                      }`} />
                    )}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Top Info Grid: SLA Status Card + Case Overview */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* SLA Ageing Card */}
          <Card className={`border ${
            app.ageing_bucket === 'OVERDUE' ? 'border-rose-300 bg-rose-50/30' :
            app.ageing_bucket === 'NEAR_DUE' ? 'border-amber-300 bg-amber-50/30' :
            'border-slate-200 bg-white'
          }`}>
            <CardHeader className="py-2.5 px-4 bg-slate-50 border-b border-slate-100">
              <CardTitle className="text-xs flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-slate-800">
                  <Clock className="w-3.5 h-3.5 text-blue-800" /> Statutory SLA Ageing
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  app.ageing_bucket === 'OVERDUE' ? 'bg-rose-100 text-rose-800' :
                  app.ageing_bucket === 'NEAR_DUE' ? 'bg-amber-100 text-amber-800' :
                  app.ageing_bucket === 'COMPLETED' ? 'bg-blue-100 text-blue-800' :
                  'bg-emerald-100 text-emerald-800'
                }`}>
                  {app.ageing_bucket.replace('_', ' ')}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-3 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Days in Active Stage:</span>
                <span className="font-bold text-slate-900">{app.days_in_stage} days</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Days Remaining:</span>
                <span className={`font-bold ${app.days_remaining < 0 ? 'text-rose-700' : 'text-slate-900'}`}>
                  {app.days_remaining >= 0 ? `${app.days_remaining} days` : `${Math.abs(app.days_remaining)} days overdue`}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Statutory Limit:</span>
                <span className="text-slate-700">{app.current_stage.default_sla_days} days (APH Chapter II)</span>
              </div>

              {/* Progress bar */}
              <div>
                <div className="flex justify-between text-[10px] text-slate-500 mb-1">
                  <span>SLA Time Elapsed</span>
                  <span>{Math.min(100, Math.round(app.percentage_elapsed))}%</span>
                </div>
                <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                  <div 
                    className={`h-full transition-all ${
                      app.percentage_elapsed >= 100 ? 'bg-rose-600' :
                      app.percentage_elapsed >= 80 ? 'bg-amber-500' : 'bg-emerald-600'
                    }`}
                    style={{ width: `${Math.min(100, app.percentage_elapsed)}%` }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Institutional Compliance Card */}
          <Card className="border-slate-200 bg-white">
            <CardHeader className="py-2.5 px-4 bg-slate-50 border-b border-slate-100">
              <CardTitle className="text-xs text-slate-800 flex items-center gap-1.5">
                <Building2 className="w-3.5 h-3.5 text-blue-800" /> Applying Institution
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-2 text-xs">
              <div className="font-semibold text-slate-900">{app.institution.name}</div>
              <div className="text-slate-500">AICTE Permanent ID: <strong className="text-slate-700">{app.institution.aicte_id}</strong></div>
              <div className="text-slate-500">Jurisdiction: {app.region_name}</div>
              <div className="text-slate-500">Location: {app.institution.city}, {app.institution.state} - {app.institution.pincode}</div>
              <div className="text-slate-500">Official Contact: {app.institution.primary_email}</div>
            </CardContent>
          </Card>

          {/* Workflow Metrics Card */}
          <Card className="border-slate-200 bg-white">
            <CardHeader className="py-2.5 px-4 bg-slate-50 border-b border-slate-100">
              <CardTitle className="text-xs text-slate-800 flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5 text-blue-800" /> Integrity & Risk Score
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-3 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Clarification Revert Cycles:</span>
                <span className={`px-2 py-0.5 rounded font-mono font-bold ${
                  app.revert_count >= 2 ? 'bg-amber-100 text-amber-900 border border-amber-300' : 'bg-slate-100 text-slate-800'
                }`}>
                  {app.revert_count} of 2 allowed
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Delay Risk Level:</span>
                <span className={`font-bold ${
                  app.delay_risk_score > 0.7 ? 'text-rose-600' :
                  app.delay_risk_score > 0.4 ? 'text-amber-600' : 'text-emerald-700'
                }`}>
                  {Math.round(app.delay_risk_score * 100)}% ({app.delay_risk_score > 0.7 ? 'High' : app.delay_risk_score > 0.4 ? 'Moderate' : 'Low'})
                </span>
              </div>
              {app.risk_factors && app.risk_factors.length > 0 && (
                <div className="p-2 bg-slate-50 rounded border border-slate-200">
                  <span className="text-[10px] font-semibold text-slate-600 block mb-1">Identified Risk Flags:</span>
                  <ul className="list-disc list-inside text-[11px] text-slate-700 space-y-0.5">
                    {app.risk_factors.map((rf, idx) => (
                      <li key={idx}>{rf}</li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Main Body Split: Left (Timeline + Summary) | Right (Communications Panel) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Left Column (2 Cols) */}
          <div className="lg:col-span-2 space-y-5">
            {/* AI Synthesized Case Summary */}
            {app.case_summary && (
              <Card className="border-blue-200 bg-blue-50/20 shadow-sm">
                <CardHeader className="py-2.5 px-4 bg-blue-50/60 border-b border-blue-100 flex flex-row items-center justify-between">
                  <CardTitle className="text-xs text-blue-950 flex items-center gap-2 font-bold">
                    <Sparkles className="w-4 h-4 text-blue-700" />
                    <span>Automated Case Summary (Statutory Dossier Synthesis)</span>
                    <DecisionSupportBadge size="sm" />
                  </CardTitle>
                  <span className="text-[10px] text-slate-500">
                    Engine: {app.case_summary.generated_by}
                  </span>
                </CardHeader>
                <CardContent className="p-4 space-y-3 text-xs leading-relaxed">
                  <p className="text-slate-800 font-medium">{app.case_summary.executive_summary}</p>
                  
                  {app.case_summary.key_findings && app.case_summary.key_findings.length > 0 && (
                    <div>
                      <span className="font-semibold text-slate-700 block mb-1">Key Operational Findings:</span>
                      <ul className="list-disc list-inside text-slate-600 space-y-0.5">
                        {app.case_summary.key_findings.map((kf, i) => (
                          <li key={i}>{kf}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {app.case_summary.compliance_flags && app.case_summary.compliance_flags.length > 0 && (
                    <div className="pt-2 border-t border-blue-100">
                      <span className="font-semibold text-slate-700 block mb-1">Statutory Compliance Flags:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {app.case_summary.compliance_flags.map((flag, i) => (
                          <span key={i} className="px-2 py-0.5 bg-white border border-blue-200 rounded text-[11px] text-blue-900 font-medium">
                            {flag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Vertical Audit Timeline */}
            <Card className="border-slate-200 bg-white">
              <CardHeader className="py-2.5 px-4 bg-slate-50 border-b border-slate-100">
                <CardTitle className="text-xs text-slate-800 flex items-center gap-1.5 font-bold">
                  <Clock className="w-4 h-4 text-blue-800" />
                  Statutory Stage Movement & Audit History ({timeline.length} events)
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4">
                <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
                  {timeline.map((item, idx) => (
                    <div key={item.id} className="relative">
                      {/* Circle dot */}
                      <div className={`absolute -left-6 top-1 w-3.5 h-3.5 rounded-full border-2 bg-white ${
                        item.status === 'COMPLETED' ? 'border-emerald-600 bg-emerald-500' :
                        item.status === 'REVERTED' ? 'border-amber-600 bg-amber-500' :
                        'border-blue-600 ring-2 ring-blue-100'
                      }`} />

                      <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-1.5 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-slate-900">
                            {item.to_stage_name}
                          </span>
                          <span className="text-[11px] text-slate-500 font-mono">
                            {new Date(item.entered_at).toLocaleDateString('en-IN', {
                              day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
                            })}
                          </span>
                        </div>

                        <div className="text-slate-600 flex items-center gap-2 text-[11px]">
                          <span>Actor: <strong className="text-slate-800">{item.actor_name || 'System Docketing'}</strong> ({item.actor_role || 'DESK'})</span>
                          {item.duration_hours > 0 && (
                            <span className="text-slate-400">| Stage Dwell: {item.duration_hours}h</span>
                          )}
                        </div>

                        {item.revert_reason && (
                          <div className="p-2 bg-amber-50 border border-amber-200 rounded text-amber-900 text-[11px]">
                            <strong>Deficiency Grounds:</strong> {item.revert_reason}
                            {item.deficiency_tags && item.deficiency_tags.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-1.5">
                                {item.deficiency_tags.map((t) => (
                                  <span key={t} className="px-1.5 py-0.5 bg-amber-200/80 rounded font-mono text-[10px] font-semibold text-amber-950">
                                    {t}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Fair Pendency Clock Breakdown */}
            <Card className="border-slate-200 bg-white">
              <CardHeader className="py-2.5 px-4 bg-slate-50 border-b border-slate-100 flex flex-row items-center justify-between">
                <CardTitle className="text-xs text-slate-800 flex items-center gap-1.5 font-bold">
                  <Clock className="w-4 h-4 text-blue-800" />
                  Fair Pendency Clock Breakdown ({clockSegments.length} segments)
                </CardTitle>
                <div className="flex items-center gap-2 text-[11px]">
                  <span className="text-blue-700 font-medium">With AICTE: {clockTotals.aicte_hours || 0}h</span>
                  <span>•</span>
                  <span className="text-amber-700 font-medium">With Institution: {clockTotals.inst_hours || 0}h</span>
                </div>
              </CardHeader>
              <CardContent className="p-4 space-y-3">
                <p className="text-[11px] text-slate-500 italic">
                  Fair processing guarantee: time spent waiting for institution clarification is recorded as WITH_INSTITUTION and strictly paused from AICTE officer SLA and escalation counters.
                </p>
                {clockSegments.length === 0 ? (
                  <div className="py-4 text-center text-slate-400 text-xs">
                    No clock segments recorded yet.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {clockSegments.map((seg, idx) => (
                      <div
                        key={seg.id || idx}
                        className={`p-2.5 rounded-lg border text-xs flex items-center justify-between ${
                          seg.holder === 'WITH_INSTITUTION'
                            ? 'bg-amber-50/60 border-amber-200 text-amber-950'
                            : 'bg-blue-50/40 border-blue-200 text-slate-800'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              seg.holder === 'WITH_INSTITUTION'
                                ? 'bg-amber-200 text-amber-900'
                                : 'bg-blue-200 text-blue-900'
                            }`}
                          >
                            {seg.holder === 'WITH_INSTITUTION' ? '⏸ WITH INSTITUTION' : '▶ WITH AICTE'}
                          </span>
                          <span className="text-[11px] text-slate-600">
                            {new Date(seg.started_at).toLocaleDateString('en-IN', {
                              day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
                            })}
                            {seg.ended_at ? ` → ${new Date(seg.ended_at).toLocaleDateString('en-IN', {
                              day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
                            })}` : ' (Active)'}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          {seg.remarks && (
                            <span className="text-[11px] text-slate-500 italic truncate max-w-[200px]" title={seg.remarks}>
                              {seg.remarks}
                            </span>
                          )}
                          <span className="font-mono font-bold text-slate-800">
                            {seg.duration_hours != null ? `${seg.duration_hours}h` : 'Ongoing'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Right Column (1 Col): Draft Routine Communications */}
          <div className="space-y-5">
            <Card className="border-slate-200 bg-white shadow-sm">
              <CardHeader className="py-2.5 px-4 bg-slate-50 border-b border-slate-100 flex flex-row items-center justify-between">
                <CardTitle className="text-xs text-slate-800 flex items-center gap-1.5 font-bold">
                  <Mail className="w-4 h-4 text-blue-800" />
                  Routine Draft Communications ({app.communications?.length || 0})
                </CardTitle>
                <Badge variant="neutral">Module A</Badge>
              </CardHeader>
              <CardContent className="p-4 space-y-3">
                <p className="text-[11px] text-slate-500 italic">
                  Statutory notices generated automatically in draft state. Officers must review and dispatch; nothing is dispatched autonomously.
                </p>

                {(!app.communications || app.communications.length === 0) ? (
                  <div className="py-8 text-center text-slate-400 text-xs">
                    No communications drafted for this case yet.
                  </div>
                ) : (
                  app.communications.map((comm) => (
                    <div 
                      key={comm.id} 
                      className={`p-3 rounded-lg border text-xs space-y-2 transition-all ${
                        comm.status === 'SENT' 
                          ? 'border-emerald-200 bg-emerald-50/30' 
                          : 'border-slate-200 bg-slate-50/70 hover:border-blue-300'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-900 truncate max-w-[190px]" title={comm.subject}>
                          {comm.subject}
                        </span>
                        <Badge variant={comm.status === 'SENT' ? 'success' : 'warning'}>
                          {comm.status}
                        </Badge>
                      </div>

                      <div className="text-[11px] text-slate-500">
                        To: {comm.recipient_email}
                      </div>

                      <div className="p-2 bg-white rounded border border-slate-200 font-mono text-[10px] text-slate-700 whitespace-pre-wrap max-h-32 overflow-y-auto">
                        {comm.body}
                      </div>

                      <div className="flex items-center justify-between pt-1">
                        <span className="text-[10px] text-slate-400">
                          {new Date(comm.created_at).toLocaleDateString('en-IN', {
                            day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
                          })}
                        </span>
                        {comm.status === 'DRAFT' && (
                          <Button 
                            size="sm" 
                            variant="outline" 
                            className="h-6 text-[11px] border-blue-600 text-blue-700 hover:bg-blue-50"
                            onClick={() => handleMarkSent(comm.id)}
                          >
                            <Send className="w-3 h-3 mr-1" />
                            Dispatch Notice
                          </Button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Modal: Complete / Advance Stage */}
        {showAdvanceModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full border border-slate-200 overflow-hidden">
              <div className="bg-slate-900 text-white px-4 py-3 flex items-center justify-between">
                <h3 className="font-semibold text-sm flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  {app.current_stage.code === 'RE_SCRUTINY' ? 'Submit Deficiency Clarification' : `Advance Stage: ${app.current_stage.name}`}
                </h3>
                <button onClick={() => setShowAdvanceModal(false)} className="text-slate-400 hover:text-white">&times;</button>
              </div>
              <form onSubmit={handleAdvanceStage} className="p-4 space-y-4 text-xs">
                <p className="text-slate-600 leading-relaxed">
                  {app.current_stage.code === 'RE_SCRUTINY'
                    ? 'Submit point-by-point compliance clarifications and revised statutory attachments. Advancing returns the dossier to Scrutiny Desk for statutory verification.'
                    : `Confirm statutory clearance for '${app.current_stage.name}'. The application will automatically progress to the next statutory milestone in path '${app.stage_path.name}'.`}
                </p>

                <div>
                  <label className="font-semibold text-slate-700 block mb-1">
                    Officer / Institution Remarks
                  </label>
                  <textarea
                    rows={3}
                    placeholder="Enter statutory inspection remarks or uploaded clarification details..."
                    value={advanceRemarks}
                    onChange={(e) => setAdvanceRemarks(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-700"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                  <Button type="button" variant="outline" size="sm" onClick={() => setShowAdvanceModal(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" size="sm" disabled={actionLoading} className="bg-blue-800 hover:bg-blue-900 text-white">
                    {actionLoading ? 'Processing...' : 'Confirm & Advance'}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal: Raise Deficiencies / Revert */}
        {showReturnModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
            <div className="bg-white rounded-lg shadow-xl max-w-lg w-full border border-slate-200 overflow-hidden">
              <div className="bg-slate-900 text-white px-4 py-3 flex items-center justify-between">
                <h3 className="font-semibold text-sm flex items-center gap-2">
                  <RotateCcw className="w-4 h-4 text-amber-400" />
                  Statutory Deficiency Notice & Revert
                </h3>
                <button onClick={() => setShowReturnModal(false)} className="text-slate-400 hover:text-white">&times;</button>
              </div>
              <form onSubmit={handleReturnApplication} className="p-4 space-y-4 text-xs">
                {app.revert_count >= 1 && (
                  <div className="p-2.5 bg-amber-50 border border-amber-300 rounded text-amber-900 text-[11px] flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                    <span>
                      <strong>Warning:</strong> This application has already undergone {app.revert_count} revert cycle(s). AICTE regulations cap reverts at 2 cycles before mandatory Regional Head escalation.
                    </span>
                  </div>
                )}

                <div>
                  <label className="font-semibold text-slate-800 block mb-1.5">
                    Select Deficiency Grounds (At least 1 mandatory):
                  </label>
                  <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto p-2 bg-slate-50 border border-slate-200 rounded">
                    {deficiencyTags.map((tag) => (
                      <label 
                        key={tag.code} 
                        className={`flex items-start gap-2 p-1.5 rounded cursor-pointer border text-[11px] transition-colors ${
                          selectedTags.includes(tag.code) 
                            ? 'bg-blue-50 border-blue-300 text-blue-900 font-medium' 
                            : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={selectedTags.includes(tag.code)}
                          onChange={() => toggleTag(tag.code)}
                          className="mt-0.5 rounded text-blue-800"
                        />
                        <div>
                          <div className="font-semibold leading-tight">{tag.label}</div>
                          <div className="text-[10px] text-slate-500 font-mono">{tag.code}</div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="font-semibold text-slate-800 block mb-1">
                    Specific Written Deficiencies & Required Rectifications (Mandatory):
                  </label>
                  <textarea
                    rows={4}
                    placeholder="Enter detailed statutory reasons. Note: DEF_OTHER requires comprehensive explanation (min 15 characters)..."
                    value={returnRemarks}
                    onChange={(e) => setReturnRemarks(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-700"
                    required
                  />
                  {selectedTags.includes('DEF_OTHER') && returnRemarks.trim().length < 15 && (
                    <span className="text-[10px] text-rose-600 block mt-1">
                      DEF_OTHER requires at least 15 characters of detailed explanation.
                    </span>
                  )}
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                  <Button type="button" variant="outline" size="sm" onClick={() => setShowReturnModal(false)}>
                    Cancel
                  </Button>
                  <Button 
                    type="submit" 
                    size="sm" 
                    disabled={actionLoading || selectedTags.length === 0 || !returnRemarks.trim() || (selectedTags.includes('DEF_OTHER') && returnRemarks.trim().length < 15)} 
                    className="bg-amber-600 hover:bg-amber-700 text-white"
                  >
                    {actionLoading ? 'Recording...' : 'Issue Deficiency Notice'}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal: Competent Authority Record Decision */}
        {showDecisionModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full border border-slate-200 overflow-hidden">
              <div className="bg-slate-900 text-white px-4 py-3 flex items-center justify-between">
                <h3 className="font-semibold text-sm flex items-center gap-2">
                  <Award className="w-4 h-4 text-emerald-400" />
                  Record Final Statutory Decision (Competent Authority)
                </h3>
                <button onClick={() => setShowDecisionModal(false)} className="text-slate-400 hover:text-white">&times;</button>
              </div>
              <form onSubmit={handleRecordDecision} className="p-4 space-y-4 text-xs">
                <div className="p-2.5 bg-blue-50 border border-blue-200 rounded text-blue-900 text-[11px] leading-relaxed">
                  <strong>Authority Declaration:</strong> The automated system never grants or rejects applications autonomously. As an authorised Competent Authority, your decision finalises this case and generates the statutory council order.
                </div>

                <div>
                  <label className="font-semibold text-slate-800 block mb-2">Final Council Determination:</label>
                  <div className="grid grid-cols-2 gap-3">
                    <label className={`flex items-center gap-2 p-2.5 rounded-lg border cursor-pointer font-medium text-xs ${
                      decisionType === 'APPROVE' ? 'bg-emerald-50 border-emerald-500 text-emerald-900 ring-1 ring-emerald-400' : 'bg-white border-slate-200 text-slate-700'
                    }`}>
                      <input
                        type="radio"
                        name="decision"
                        value="APPROVE"
                        checked={decisionType === 'APPROVE'}
                        onChange={() => setDecisionType('APPROVE')}
                      />
                      <span>GRANT APPROVAL (LoA / EoA)</span>
                    </label>

                    <label className={`flex items-center gap-2 p-2.5 rounded-lg border cursor-pointer font-medium text-xs ${
                      decisionType === 'REJECT' ? 'bg-rose-50 border-rose-500 text-rose-900 ring-1 ring-rose-400' : 'bg-white border-slate-200 text-slate-700'
                    }`}>
                      <input
                        type="radio"
                        name="decision"
                        value="REJECT"
                        checked={decisionType === 'REJECT'}
                        onChange={() => setDecisionType('REJECT')}
                      />
                      <span>REJECT APPLICATION</span>
                    </label>
                  </div>
                </div>

                <div>
                  <label className="font-semibold text-slate-800 block mb-1">
                    Statutory Grounds & Justification Remarks (Mandatory):
                  </label>
                  <textarea
                    rows={4}
                    placeholder="Enter formal justification under APH 2026 regulations..."
                    value={decisionRemarks}
                    onChange={(e) => setDecisionRemarks(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-700"
                    required
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                  <Button type="button" variant="outline" size="sm" onClick={() => setShowDecisionModal(false)}>
                    Cancel
                  </Button>
                  <Button 
                    type="submit" 
                    size="sm" 
                    disabled={actionLoading || decisionRemarks.trim().length < 5} 
                    className={decisionType === 'APPROVE' ? 'bg-emerald-800 hover:bg-emerald-900 text-white' : 'bg-rose-800 hover:bg-rose-900 text-white'}
                  >
                    {actionLoading ? 'Recording...' : `Execute ${decisionType}`}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal: Sample Letter of Approval Viewer */}
        {showLetterModal && app.approval_letter_data && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
            <div className="bg-white rounded-lg shadow-2xl max-w-2xl w-full border border-slate-300 overflow-hidden flex flex-col max-h-[90vh]">
              <div className="bg-slate-900 text-white px-4 py-3 flex items-center justify-between">
                <h3 className="font-semibold text-sm flex items-center gap-2">
                  <Award className="w-4 h-4 text-emerald-400" />
                  Sample Statutory Order Viewer (LoA/EoA)
                </h3>
                <button onClick={() => setShowLetterModal(false)} className="text-slate-400 hover:text-white">&times;</button>
              </div>

              {/* Printable Council Letter Sheet */}
              <div className="p-8 overflow-y-auto space-y-6 text-xs text-slate-800 relative bg-white font-serif">
                {/* Big watermark banner */}
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none select-none opacity-[0.08] rotate-[-30deg]">
                  <span className="text-4xl font-extrabold text-slate-900 text-center leading-normal uppercase">
                    {app.approval_letter_data.watermark}
                  </span>
                </div>

                {/* Letterhead */}
                <div className="text-center border-b-2 border-slate-900 pb-4 space-y-1">
                  <div className="font-bold text-base text-slate-900 uppercase tracking-wider">
                    All India Council for Technical Education
                  </div>
                  <div className="text-[11px] text-slate-600">
                    (A Statutory Body of the Government of India, Ministry of Education)
                  </div>
                  <div className="text-[10px] text-slate-500">
                    Nelson Mandela Marg, Vasant Kunj, New Delhi - 110070 | www.aicte.gov.in
                  </div>
                </div>

                {/* Ref & Date */}
                <div className="flex justify-between items-center text-[11px] font-sans font-medium text-slate-700">
                  <div>Ref No: <strong className="text-slate-900 font-mono">{app.approval_letter_ref}</strong></div>
                  <div>Date of Issuance: <strong className="text-slate-900">{app.approval_letter_data.issued_date}</strong></div>
                </div>

                {/* Addressee */}
                <div className="space-y-0.5 font-sans text-xs">
                  <div>To,</div>
                  <div className="font-bold text-slate-900">The Principal / Director,</div>
                  <div>{app.institution.name}</div>
                  <div>{app.institution.city}, {app.institution.state} - {app.institution.pincode}</div>
                </div>

                {/* Subject */}
                <div className="p-2 bg-slate-50 border-l-4 border-slate-900 font-sans font-bold text-xs text-slate-900">
                  Subject: Grant of Extension of Approval (EoA) / Letter of Approval for Academic Year {app.academic_year} - Reg.
                </div>

                {/* Letter Body */}
                <div className="space-y-3 leading-relaxed text-slate-700 font-sans text-xs text-justify">
                  <p>
                    Sir / Madam,
                  </p>
                  <p>
                    In terms of the provisions under the All India Council for Technical Education (Grant of Approvals for Technical Institutions) Regulations, 2026 notified by the Council vide notification number F.No. AB/AICTE/REG/2026 and norms standards, procedures and conditions prescribed by the Council from time to time, I am directed to convey the statutory approval to:
                  </p>

                  <table className="w-full border-collapse border border-slate-300 text-[11px] my-3">
                    <tbody>
                      <tr className="border-b border-slate-300 bg-slate-50">
                        <td className="p-2 font-semibold w-1/3 border-r border-slate-300">Application Number</td>
                        <td className="p-2 font-mono font-bold text-blue-900">{app.application_number}</td>
                      </tr>
                      <tr className="border-b border-slate-300">
                        <td className="p-2 font-semibold border-r border-slate-300">Permanent Institute ID</td>
                        <td className="p-2 font-mono">{app.institution.aicte_id}</td>
                      </tr>
                      <tr className="border-b border-slate-300 bg-slate-50">
                        <td className="p-2 font-semibold border-r border-slate-300">Regional Directorate</td>
                        <td className="p-2">{app.region_name}</td>
                      </tr>
                      <tr>
                        <td className="p-2 font-semibold border-r border-slate-300">Approval Category</td>
                        <td className="p-2">{app.category.title}</td>
                      </tr>
                    </tbody>
                  </table>

                  <p>
                    The approval is subject to strict adherence to the provisions made in the Approval Process Handbook 2026-27 and compliance with statutory undertakings, faculty cadre ratios, and fire safety norms submitted by the institution.
                  </p>
                </div>

                {/* Sign-off */}
                <div className="pt-8 flex justify-between items-end font-sans">
                  <div className="text-[10px] text-slate-400">
                    Digital Verification Hash: <span className="font-mono">{app.application_number.slice(-8)}-OK</span>
                  </div>
                  <div className="text-right space-y-1">
                    <div className="font-bold text-slate-900">Member Secretary / Competent Authority</div>
                    <div className="text-[11px] text-slate-600">All India Council for Technical Education</div>
                  </div>
                </div>

                {/* Prominent Footer Watermark */}
                <div className="mt-8 pt-3 border-t-2 border-dashed border-amber-400 bg-amber-50 p-2 text-center text-amber-900 font-sans font-bold text-[11px] uppercase tracking-wide">
                  *** {app.approval_letter_data.watermark} ***
                </div>
              </div>

              <div className="bg-slate-100 px-4 py-3 border-t border-slate-200 flex justify-end gap-2">
                <Button size="sm" variant="outline" onClick={() => window.print()}>
                  Print Order
                </Button>
                <Button size="sm" onClick={() => setShowLetterModal(false)}>
                  Close Viewer
                </Button>
              </div>
            </div>
          </div>
        )}
        {/* Modal: Institution Response */}
        {showResponseModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
            <div className="bg-white rounded-lg shadow-xl max-w-lg w-full border border-slate-200 overflow-hidden">
              <div className="bg-slate-900 text-white px-4 py-3 flex items-center justify-between">
                <h3 className="font-semibold text-sm flex items-center gap-2">
                  <Send className="w-4 h-4 text-amber-400" />
                  Submit Institution Response & Clarifications
                </h3>
                <button onClick={() => setShowResponseModal(false)} className="text-slate-400 hover:text-white">&times;</button>
              </div>
              <form onSubmit={handleInstitutionResponse} className="p-4 space-y-4 text-xs">
                <div className="p-2.5 bg-amber-50 border border-amber-200 rounded text-amber-950 text-[11px] leading-relaxed">
                  <strong>Fair Clock Resume Notice:</strong> Submitting this response confirms compliance rectifications. The dossier holder will immediately transition from <strong>WITH_INSTITUTION</strong> back to <strong>WITH_AICTE</strong>, and re-enter Re-Scrutiny with a fresh stage SLA.
                </div>

                <div>
                  <label className="font-semibold text-slate-800 block mb-1">
                    Compliance Clarification Remarks (Mandatory):
                  </label>
                  <textarea
                    rows={4}
                    placeholder="Provide detailed point-by-point response to deficiency grounds raised..."
                    value={responseRemarks}
                    onChange={(e) => setResponseRemarks(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-700"
                    required
                  />
                </div>

                <div>
                  <label className="font-semibold text-slate-800 block mb-1">
                    Supporting Document / Link (Optional):
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. https://portal.aicte-india.org/docs/clarification-signed.pdf"
                    value={responseDocUrl}
                    onChange={(e) => setResponseDocUrl(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-700"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                  <Button type="button" variant="outline" size="sm" onClick={() => setShowResponseModal(false)}>
                    Cancel
                  </Button>
                  <Button 
                    type="submit" 
                    size="sm" 
                    disabled={actionLoading || !responseRemarks.trim()} 
                    className="bg-amber-600 hover:bg-amber-700 text-white"
                  >
                    {actionLoading ? 'Submitting...' : 'Submit Response & Resume Clock'}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal: Close Case Formally */}
        {showCloseModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
            <div className="bg-white rounded-lg shadow-xl max-w-lg w-full border border-slate-200 overflow-hidden">
              <div className="bg-slate-900 text-white px-4 py-3 flex items-center justify-between">
                <h3 className="font-semibold text-sm flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  Formally Close Statutory Case
                </h3>
                <button onClick={() => setShowCloseModal(false)} className="text-slate-400 hover:text-white">&times;</button>
              </div>
              <form onSubmit={handleCloseApplication} className="p-4 space-y-4 text-xs">
                <div className="p-2.5 bg-blue-50 border border-blue-200 rounded text-blue-900 text-[11px] leading-relaxed">
                  <strong>Statutory Undertakings Verification:</strong> Case closure is strictly blocked by the workflow engine if any statutory undertakings on this application remain open or unverified.
                </div>

                <div>
                  <label className="font-semibold text-slate-800 block mb-1.5">
                    Statutory Closure Reason (Mandatory):
                  </label>
                  <select
                    value={closureReason}
                    onChange={(e) => setClosureReason(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-700 bg-white"
                  >
                    <option value="ALL_CONDITIONS_MET">ALL_CONDITIONS_MET - All approval conditions satisfied & verified</option>
                    <option value="REJECTED_FINAL">REJECTED_FINAL - Final rejection; statutory appeals exhausted</option>
                    <option value="WITHDRAWN_BY_INSTITUTION">WITHDRAWN_BY_INSTITUTION - Voluntary withdrawal by applicant</option>
                    <option value="SUPERSEDED">SUPERSEDED - Superseded by subsequent council order / court decree</option>
                    <option value="OTHER">OTHER - Other administrative grounds (requires remarks)</option>
                  </select>
                </div>

                <div>
                  <label className="font-semibold text-slate-800 block mb-1">
                    Closure Remarks {closureReason === 'OTHER' && <span className="text-rose-600">*</span>}:
                  </label>
                  <textarea
                    rows={3}
                    placeholder="Enter formal closure justification or reference order number..."
                    value={closureRemarks}
                    onChange={(e) => setClosureRemarks(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-700"
                    required={closureReason === 'OTHER'}
                  />
                </div>

                <div className="p-2.5 bg-slate-50 border border-slate-200 rounded text-slate-600 text-[11px]">
                  <strong>System Action on Closure:</strong> Moves stage to CLOSED, halts all SLA clocks, auto-resolves any active alerts with reason "Case closed", issues email notification to applicant institution, and locks dossier as permanent immutable audit record.
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                  <Button type="button" variant="outline" size="sm" onClick={() => setShowCloseModal(false)}>
                    Cancel
                  </Button>
                  <Button 
                    type="submit" 
                    size="sm" 
                    disabled={actionLoading || (closureReason === 'OTHER' && !closureRemarks.trim())} 
                    className="bg-slate-800 hover:bg-slate-900 text-white"
                  >
                    {actionLoading ? 'Closing Case...' : 'Confirm Case Closure'}
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
