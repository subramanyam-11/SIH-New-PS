'use client';

import React, { useState, useEffect } from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/lib/auth';
import {
  reportsApi,
  PendencyReportData,
  EvcReportData,
  UndertakingReportData,
  DocumentReportData,
  RegionalPerformanceData,
  InstitutionHealthDossier,
  OverdueCasesReportData,
  OverdueItem,
  lookupApi,
  Region,
  Institution,
} from '@/lib/api';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import {
  BarChart3,
  CalendarCheck2,
  ClipboardList,
  ShieldCheck,
  Building2,
  Download,
  Filter,
  FileSpreadsheet,
  FileText,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Layers,
  ShieldAlert,
  Award,
} from 'lucide-react';

const COLORS = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

export default function ReportsPage() {
  const { scope } = useAuth();
  const [activeTab, setActiveTab] = useState<
    'PENDENCY' | 'OVERDUE' | 'EVC' | 'UNDERTAKINGS' | 'DOCUMENTS' | 'REGIONAL' | 'HEALTH'
  >('PENDENCY');

  // Filters
  const [selectedRegion, setSelectedRegion] = useState<string>('ALL');
  const [regions, setRegions] = useState<Region[]>([]);
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [selectedInstitutionId, setSelectedInstitutionId] = useState<number>(1);
  const [overdueTypeFilter, setOverdueTypeFilter] = useState<string>('ALL');

  // Data states
  const [pendencyData, setPendencyData] = useState<PendencyReportData | null>(null);
  const [overdueData, setOverdueData] = useState<OverdueCasesReportData | null>(null);
  const [evcData, setEvcData] = useState<EvcReportData | null>(null);
  const [undertakingData, setUndertakingData] = useState<UndertakingReportData | null>(null);
  const [documentData, setDocumentData] = useState<DocumentReportData | null>(null);
  const [regionalData, setRegionalData] = useState<RegionalPerformanceData | null>(null);
  const [healthData, setHealthData] = useState<InstitutionHealthDossier | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    lookupApi.getRegions().then(setRegions).catch(() => {});
    lookupApi.getInstitutions().then((data) => {
      setInstitutions(data);
      if (data.length > 0) setSelectedInstitutionId(data[0].id);
    }).catch(() => {});
  }, []);

  const loadActiveReport = async () => {
    setLoading(true);
    setError('');
    const regId = selectedRegion !== 'ALL' ? parseInt(selectedRegion, 10) : undefined;
    try {
      if (activeTab === 'PENDENCY') {
        const data = await reportsApi.getPendency(regId);
        setPendencyData(data);
      } else if (activeTab === 'OVERDUE') {
        const params: Record<string, any> = {};
        if (regId) params.region_id = regId;
        if (overdueTypeFilter !== 'ALL') params.type = overdueTypeFilter;
        const data = await reportsApi.getOverdue(params);
        setOverdueData(data);
      } else if (activeTab === 'EVC') {
        const data = await reportsApi.getEvc(regId);
        setEvcData(data);
      } else if (activeTab === 'UNDERTAKINGS') {
        const data = await reportsApi.getUndertakings(regId);
        setUndertakingData(data);
      } else if (activeTab === 'DOCUMENTS') {
        const data = await reportsApi.getDocuments(regId);
        setDocumentData(data);
      } else if (activeTab === 'REGIONAL') {
        const data = await reportsApi.getRegionalPerformance();
        setRegionalData(data);
      } else if (activeTab === 'HEALTH') {
        if (selectedInstitutionId) {
          const data = await reportsApi.getInstitutionHealth(selectedInstitutionId);
          setHealthData(data);
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to calculate report metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadActiveReport();
  }, [activeTab, selectedRegion, selectedInstitutionId, overdueTypeFilter]);

  const handleDownloadCsv = () => {
    const regId = selectedRegion !== 'ALL' ? parseInt(selectedRegion, 10) : undefined;
    let reportKey = activeTab.toLowerCase();
    if (activeTab === 'REGIONAL') reportKey = 'regional_performance';
    if (activeTab === 'OVERDUE') reportKey = 'overdue';
    const url = reportsApi.getCsvExportUrl(reportKey, regId);
    window.open(url, '_blank');
  };

  const handleDownloadPdf = () => {
    const regId = selectedRegion !== 'ALL' ? parseInt(selectedRegion, 10) : undefined;
    let reportKey = activeTab.toLowerCase();
    if (activeTab === 'REGIONAL') reportKey = 'regional_performance';
    if (activeTab === 'OVERDUE') reportKey = 'overdue';
    const url = reportsApi.getPdfExportUrl(reportKey, regId);
    window.open(url, '_blank');
  };

  return (
    <AppShell>
      <div className="space-y-4">
        {/* Header Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-blue-700" />
              Executive Audit & Statutory Reports Suite
            </h1>
            <p className="text-xs text-slate-500">
              Module F: Real-time DB-calculated audit metrics, pendency ageing, compliance rate, and regulatory exports.
            </p>
          </div>

          {/* Export Controls */}
          <div className="flex items-center gap-2">
            {activeTab !== 'HEALTH' && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleDownloadCsv}
                className="h-8 text-xs border-emerald-600 text-emerald-800 hover:bg-emerald-50"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 mr-1 text-emerald-700" />
                Export CSV
              </Button>
            )}

            {['PENDENCY', 'REGIONAL', 'OVERDUE'].includes(activeTab) && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleDownloadPdf}
                className="h-8 text-xs border-rose-600 text-rose-800 hover:bg-rose-50"
              >
                <FileText className="w-3.5 h-3.5 mr-1 text-rose-700" />
                Export PDF
              </Button>
            )}
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex flex-wrap border-b border-slate-200 gap-1 bg-white p-1 rounded-lg shadow-xs text-xs font-medium">
          <button
            onClick={() => setActiveTab('PENDENCY')}
            className={`px-3 py-2 rounded-md transition-colors ${
              activeTab === 'PENDENCY' ? 'bg-blue-900 text-white font-semibold' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Pendency & Ageing
          </button>
          <button
            onClick={() => setActiveTab('OVERDUE')}
            className={`px-3 py-2 rounded-md transition-colors flex items-center gap-1.5 ${
              activeTab === 'OVERDUE' ? 'bg-rose-900 text-white font-semibold' : 'text-rose-700 hover:bg-rose-50'
            }`}
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Overdue Cases (Audit)</span>
          </button>
          <button
            onClick={() => setActiveTab('EVC')}
            className={`px-3 py-2 rounded-md transition-colors ${
              activeTab === 'EVC' ? 'bg-blue-900 text-white font-semibold' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            EVC Turnaround
          </button>
          <button
            onClick={() => setActiveTab('UNDERTAKINGS')}
            className={`px-3 py-2 rounded-md transition-colors ${
              activeTab === 'UNDERTAKINGS' ? 'bg-blue-900 text-white font-semibold' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Undertakings Compliance
          </button>
          <button
            onClick={() => setActiveTab('DOCUMENTS')}
            className={`px-3 py-2 rounded-md transition-colors ${
              activeTab === 'DOCUMENTS' ? 'bg-blue-900 text-white font-semibold' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Document Validity
          </button>
          <button
            onClick={() => setActiveTab('REGIONAL')}
            className={`px-3 py-2 rounded-md transition-colors ${
              activeTab === 'REGIONAL' ? 'bg-blue-900 text-white font-semibold' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Regional Performance Matrix
          </button>
          <button
            onClick={() => setActiveTab('HEALTH')}
            className={`px-3 py-2 rounded-md transition-colors ${
              activeTab === 'HEALTH' ? 'bg-blue-900 text-white font-semibold' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Institution Health Dossier
          </button>
        </div>

        {/* Scope Filters */}
        <div className="bg-white p-3 rounded-lg border border-slate-200 flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span className="font-semibold text-slate-700">Audit Scope Filter:</span>
          </div>

          <div className="flex items-center gap-3">
            {activeTab !== 'HEALTH' && (
              <div className="flex items-center gap-1.5">
                <span className="text-slate-500 font-medium text-[11px]">Region:</span>
                <select
                  value={selectedRegion}
                  onChange={(e) => setSelectedRegion(e.target.value)}
                  className="p-1.5 border border-slate-200 rounded text-xs focus:ring-1 focus:ring-blue-700"
                >
                  <option value="ALL">National Aggregate (All Regions)</option>
                  {regions.map((r) => (
                    <option key={r.id} value={r.id}>{r.name}</option>
                  ))}
                </select>
              </div>
            )}

            {activeTab === 'OVERDUE' && (
              <div className="flex items-center gap-1.5">
                <span className="text-slate-500 font-medium text-[11px]">Type:</span>
                <select
                  value={overdueTypeFilter}
                  onChange={(e) => setOverdueTypeFilter(e.target.value)}
                  className="p-1.5 border border-slate-200 rounded text-xs focus:ring-1 focus:ring-blue-700"
                >
                  <option value="ALL">All Overdue Entity Types</option>
                  <option value="APPLICATION">Applications (AICTE-Held Only)</option>
                  <option value="EVC_VISIT">EVC Inspection Visits</option>
                  <option value="UNDERTAKING">Statutory Undertakings</option>
                  <option value="DOCUMENT">Statutory Documents (FDR/Lease/NOC)</option>
                </select>
              </div>
            )}

            {activeTab === 'HEALTH' && (
              <div className="flex items-center gap-1.5">
                <span className="text-slate-500 font-medium text-[11px]">Select Institution:</span>
                <select
                  value={selectedInstitutionId}
                  onChange={(e) => setSelectedInstitutionId(parseInt(e.target.value, 10))}
                  className="p-1.5 border border-slate-200 rounded text-xs focus:ring-1 focus:ring-blue-700 max-w-xs truncate"
                >
                  {institutions.map((inst) => (
                    <option key={inst.id} value={inst.id}>{inst.name} ({inst.aicte_id})</option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>

        {/* Error notification */}
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 text-rose-900 rounded text-xs">
            {error}
          </div>
        )}

        {/* Loading Spinner */}
        {loading && (
          <div className="py-12 text-center text-slate-400 text-xs">
            Calculating statistical metrics directly from database records...
          </div>
        )}

        {/* REPORT 1: PENDENCY & AGEING */}
        {!loading && activeTab === 'PENDENCY' && pendencyData && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Card className="p-4 bg-white border-slate-200">
                <div className="text-xs text-slate-500 font-semibold uppercase">Pending In-Progress</div>
                <div className="text-2xl font-bold text-slate-900 mt-1">{pendencyData.total_pending}</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Across active scrutiny cycles</div>
              </Card>

              <Card className="p-4 bg-blue-50/50 border-blue-200">
                <div className="text-xs text-blue-800 font-semibold uppercase">With AICTE (Active)</div>
                <div className="text-2xl font-bold text-blue-900 mt-1">{pendencyData.with_aicte_count ?? 0}</div>
                <div className="text-[11px] text-blue-700 mt-0.5">Officer scrutiny SLA ticking</div>
              </Card>

              <Card className="p-4 bg-amber-50/50 border-amber-200">
                <div className="text-xs text-amber-800 font-semibold uppercase">With Inst. (Paused)</div>
                <div className="text-2xl font-bold text-amber-900 mt-1">{pendencyData.with_institution_count ?? 0}</div>
                <div className="text-[11px] text-amber-700 mt-0.5">SLA paused awaiting response</div>
              </Card>

              <Card className="p-4 bg-rose-50/50 border-rose-200">
                <div className="text-xs text-rose-800 font-semibold uppercase">Overdue Applications</div>
                <div className="text-2xl font-bold text-rose-900 mt-1">{pendencyData.total_overdue}</div>
                <div className="text-[11px] text-rose-700 mt-0.5">Breached statutory stage SLA</div>
              </Card>
            </div>

            {/* Stage Chart */}
            <Card className="p-4 bg-white border-slate-200">
              <CardTitle className="text-sm font-bold text-slate-800 mb-4">
                Applications by Approval Stage & Fair Clock Distribution (Stacked Bars)
              </CardTitle>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={pendencyData.by_stage}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="stage" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="with_aicte" stackId="clock" name="With AICTE (Active Clock)" fill="#1e40af" radius={[0, 0, 0, 0]} />
                    <Bar dataKey="with_institution" stackId="clock" name="With Institution (Paused)" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="overdue_count" name="Overdue Count" fill="#dc2626" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Stage Table */}
            <Card className="border-slate-200 bg-white overflow-hidden shadow-sm">
              <div className="p-3 bg-slate-50 border-b border-slate-200 font-bold text-xs text-slate-800">
                Approval Stage Dwell Time & Fair Clock Pendency Matrix
              </div>
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50/50 text-slate-600 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-4">Approval Stage</th>
                    <th className="py-2.5 px-3">Total Pending</th>
                    <th className="py-2.5 px-3">With AICTE</th>
                    <th className="py-2.5 px-3">With Institution</th>
                    <th className="py-2.5 px-3">Avg Days in Stage</th>
                    <th className="py-2.5 px-4 text-right">Overdue Breaches</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {pendencyData.by_stage.map((s, idx) => (
                    <tr key={idx} className="hover:bg-slate-50">
                      <td className="py-2.5 px-4 font-semibold text-slate-900">{s.stage}</td>
                      <td className="py-2.5 px-3 font-mono font-bold">{s.count}</td>
                      <td className="py-2.5 px-3 font-mono text-blue-800">{s.with_aicte ?? 0}</td>
                      <td className="py-2.5 px-3 font-mono text-amber-800">{s.with_institution ?? 0}</td>
                      <td className="py-2.5 px-3 font-mono">{s.avg_days} days</td>
                      <td className="py-2.5 px-4 text-right font-mono font-bold text-rose-700">{s.overdue_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </div>
        )}

        {/* REPORT: OVERDUE CASES (STATUTORY AUDIT) */}
        {!loading && activeTab === 'OVERDUE' && overdueData && (
          <div className="space-y-4">
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <Card className="p-4 bg-rose-50/60 border-rose-200">
                <div className="text-xs text-rose-800 font-semibold uppercase">Total Overdue Items</div>
                <div className="text-2xl font-bold text-rose-900 mt-1">{overdueData.summary.total_overdue}</div>
                <div className="text-[11px] text-rose-700 mt-0.5">Across all statutory entities</div>
              </Card>

              <Card className="p-4 bg-white border-slate-200">
                <div className="text-xs text-slate-500 font-semibold uppercase">Applications (AICTE)</div>
                <div className="text-2xl font-bold text-slate-900 mt-1">{overdueData.summary.applications_overdue}</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Active AICTE clock breached</div>
              </Card>

              <Card className="p-4 bg-white border-slate-200">
                <div className="text-xs text-slate-500 font-semibold uppercase">EVC Visits</div>
                <div className="text-2xl font-bold text-slate-900 mt-1">{overdueData.summary.evc_visits_overdue}</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Visits exceeding APH limits</div>
              </Card>

              <Card className="p-4 bg-white border-slate-200">
                <div className="text-xs text-slate-500 font-semibold uppercase">Undertakings</div>
                <div className="text-2xl font-bold text-slate-900 mt-1">{overdueData.summary.undertakings_overdue}</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Unverified / breached due dates</div>
              </Card>

              <Card className="p-4 bg-white border-slate-200">
                <div className="text-xs text-slate-500 font-semibold uppercase">Expired Documents</div>
                <div className="text-2xl font-bold text-slate-900 mt-1">{overdueData.summary.documents_overdue}</div>
                <div className="text-[11px] text-slate-400 mt-0.5">FDR, NOC or Lease expired</div>
              </Card>
            </div>

            {/* Overdue Items by Type Chart */}
            <Card className="p-4 bg-white border-slate-200">
              <CardTitle className="text-sm font-bold text-slate-800 mb-4">
                Statutory Overdue Breaches by Entity Type
              </CardTitle>
              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={[
                      { name: 'Applications', count: overdueData.summary.applications_overdue, fill: '#dc2626' },
                      { name: 'EVC Visits', count: overdueData.summary.evc_visits_overdue, fill: '#f59e0b' },
                      { name: 'Undertakings', count: overdueData.summary.undertakings_overdue, fill: '#8b5cf6' },
                      { name: 'Documents', count: overdueData.summary.documents_overdue, fill: '#06b6d4' },
                    ]}
                  >
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="count" name="Overdue Count" radius={[4, 4, 0, 0]}>
                      {[
                        { fill: '#dc2626' },
                        { fill: '#f59e0b' },
                        { fill: '#8b5cf6' },
                        { fill: '#06b6d4' },
                      ].map((entry, idx) => (
                        <Cell key={`cell-${idx}`} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Overdue Items Table */}
            <Card className="border-slate-200 bg-white overflow-hidden shadow-sm">
              <div className="p-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between font-bold text-xs text-slate-800">
                <span>Comprehensive Statutory Overdue Dossier ({overdueData.items.length} records)</span>
                <span className="text-[11px] text-slate-500 font-normal">Every record and count queried live from DB</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50/50 text-slate-600 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-2.5 px-3">Ref Number</th>
                      <th className="py-2.5 px-3">Entity Type</th>
                      <th className="py-2.5 px-3">Title / Subject</th>
                      <th className="py-2.5 px-3">Institution & Region</th>
                      <th className="py-2.5 px-3">Holder</th>
                      <th className="py-2.5 px-3">Responsible Desk</th>
                      <th className="py-2.5 px-3">Statutory Due</th>
                      <th className="py-2.5 px-3 text-center">Days Overdue</th>
                      <th className="py-2.5 px-3 text-center">Escalation</th>
                      <th className="py-2.5 px-3 text-right">Linked Alert</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {overdueData.items.length === 0 ? (
                      <tr>
                        <td colSpan={10} className="py-8 text-center text-slate-400">
                          ✓ No overdue breaches found for the selected scope!
                        </td>
                      </tr>
                    ) : (
                      overdueData.items.map((item) => (
                        <tr key={item.id} className="hover:bg-rose-50/30">
                          <td className="py-2.5 px-3 font-mono font-semibold text-blue-800">
                            {item.reference_number}
                          </td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                item.type === 'APPLICATION'
                                  ? 'bg-blue-100 text-blue-800'
                                  : item.type === 'EVC_VISIT'
                                  ? 'bg-amber-100 text-amber-800'
                                  : item.type === 'UNDERTAKING'
                                  ? 'bg-purple-100 text-purple-800'
                                  : 'bg-cyan-100 text-cyan-800'
                              }`}
                            >
                              {item.type}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 max-w-[200px] truncate" title={item.title}>
                            {item.title}
                          </td>
                          <td className="py-2.5 px-3 max-w-[180px]">
                            <div className="font-medium text-slate-900 truncate" title={item.institution_name}>
                              {item.institution_name}
                            </div>
                            <div className="text-[10px] text-slate-500">{item.region_name}</div>
                          </td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                                item.case_holder === 'WITH_INSTITUTION'
                                  ? 'bg-amber-100 text-amber-900'
                                  : 'bg-blue-50 text-blue-800'
                              }`}
                            >
                              {item.case_holder === 'WITH_INSTITUTION' ? 'Institution' : 'AICTE'}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-slate-700">{item.officer_name}</td>
                          <td className="py-2.5 px-3 font-mono text-[11px] text-slate-600">
                            {item.due_date ? new Date(item.due_date).toLocaleDateString('en-IN') : 'N/A'}
                          </td>
                          <td className="py-2.5 px-3 text-center font-mono font-bold text-rose-700">
                            +{item.days_overdue}d
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-800 font-mono text-[10px] font-semibold">
                              Tier {item.escalation_level}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            {item.linked_alert_id ? (
                              <span className="font-mono text-[11px] text-rose-700 font-semibold">
                                #{item.linked_alert_id} ({item.linked_alert_severity})
                              </span>
                            ) : (
                              <span className="text-slate-400 text-[10px]">None</span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        )}

        {/* REPORT 2: EVC STATUS */}
        {!loading && activeTab === 'EVC' && evcData && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <Card className="p-4 bg-white border-slate-200">
                <div className="text-xs text-slate-500 font-semibold uppercase">Total EVC Inspections</div>
                <div className="text-2xl font-bold text-slate-900 mt-1">{evcData.total_visits}</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Visits in state machine</div>
              </Card>

              <Card className="p-4 bg-emerald-50/50 border-emerald-200">
                <div className="text-xs text-emerald-800 font-semibold uppercase">Avg Turnaround Time</div>
                <div className="text-2xl font-bold text-emerald-900 mt-1">{evcData.average_turnaround_days} Days</div>
                <div className="text-[11px] text-emerald-700 mt-0.5">From queue assignment to signed report</div>
              </Card>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card className="p-4 bg-white border-slate-200">
                <CardTitle className="text-sm font-bold text-slate-800 mb-4">Inspection State Distribution</CardTitle>
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={evcData.by_status}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                      <XAxis dataKey="status" tick={{ fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Bar dataKey="count" fill="#4f46e5" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>

              <Card className="border-slate-200 bg-white overflow-hidden shadow-sm">
                <div className="p-3 bg-slate-50 border-b border-slate-200 font-bold text-xs text-slate-800">
                  EVC Regional Activity Breakdown
                </div>
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50/50 text-slate-600 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-2.5 px-4">Region</th>
                      <th className="py-2.5 px-3">Total Visits</th>
                      <th className="py-2.5 px-4 text-right">Completed</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {evcData.by_region.map((r, idx) => (
                      <tr key={idx} className="hover:bg-slate-50">
                        <td className="py-2.5 px-4 font-semibold text-slate-900">{r.region}</td>
                        <td className="py-2.5 px-3 font-mono">{r.count}</td>
                        <td className="py-2.5 px-4 text-right font-mono font-bold text-emerald-700">{r.completed}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </div>
          </div>
        )}

        {/* REPORT 3: UNDERTAKINGS */}
        {!loading && activeTab === 'UNDERTAKINGS' && undertakingData && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <Card className="p-4 bg-white border-slate-200">
                <div className="text-xs text-slate-500 font-semibold uppercase">Total Conditions</div>
                <div className="text-2xl font-bold text-slate-900 mt-1">{undertakingData.total_undertakings}</div>
              </Card>

              <Card className="p-4 bg-emerald-50/50 border-emerald-200">
                <div className="text-xs text-emerald-800 font-semibold uppercase">Verified Satisfied</div>
                <div className="text-2xl font-bold text-emerald-900 mt-1">{undertakingData.verified_count}</div>
              </Card>

              <Card className="p-4 bg-rose-50/50 border-rose-200">
                <div className="text-xs text-rose-800 font-semibold uppercase">Overdue</div>
                <div className="text-2xl font-bold text-rose-900 mt-1">{undertakingData.overdue_count}</div>
              </Card>

              <Card className="p-4 bg-purple-50/50 border-purple-200">
                <div className="text-xs text-purple-800 font-semibold uppercase">Compliance Rate</div>
                <div className="text-2xl font-bold text-purple-900 mt-1">{undertakingData.compliance_rate_pct}%</div>
              </Card>
            </div>

            <Card className="border-slate-200 bg-white overflow-hidden shadow-sm">
              <div className="p-3 bg-slate-50 border-b border-slate-200 font-bold text-xs text-slate-800">
                Regional Undertaking Compliance Matrix
              </div>
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50/50 text-slate-600 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-4">Region</th>
                    <th className="py-2.5 px-3">Total Conditions</th>
                    <th className="py-2.5 px-3">Complied / Verified</th>
                    <th className="py-2.5 px-4 text-right">Overdue</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {undertakingData.by_region.map((r, idx) => (
                    <tr key={idx} className="hover:bg-slate-50">
                      <td className="py-2.5 px-4 font-semibold text-slate-900">{r.region}</td>
                      <td className="py-2.5 px-3 font-mono">{r.total}</td>
                      <td className="py-2.5 px-3 font-mono text-emerald-700 font-bold">{r.compliant}</td>
                      <td className="py-2.5 px-4 text-right font-mono text-rose-700 font-bold">{r.overdue}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </div>
        )}

        {/* REPORT 4: DOCUMENTS */}
        {!loading && activeTab === 'DOCUMENTS' && documentData && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <Card className="p-4 bg-white border-slate-200">
                <div className="text-xs text-slate-500 font-semibold uppercase">Total Certificates</div>
                <div className="text-2xl font-bold text-slate-900 mt-1">{documentData.total_documents}</div>
              </Card>

              <Card className="p-4 bg-emerald-50/50 border-emerald-200">
                <div className="text-xs text-emerald-800 font-semibold uppercase">Valid & Active</div>
                <div className="text-2xl font-bold text-emerald-900 mt-1">{documentData.valid_count}</div>
              </Card>

              <Card className="p-4 bg-amber-50/50 border-amber-200">
                <div className="text-xs text-amber-800 font-semibold uppercase">Expiring &le;60d</div>
                <div className="text-2xl font-bold text-amber-900 mt-1">{documentData.expiring_soon_count}</div>
              </Card>

              <Card className="p-4 bg-rose-50/50 border-rose-200">
                <div className="text-xs text-rose-800 font-semibold uppercase">Expired</div>
                <div className="text-2xl font-bold text-rose-900 mt-1">{documentData.expired_count}</div>
              </Card>
            </div>

            <Card className="p-4 bg-white border-slate-200">
              <CardTitle className="text-sm font-bold text-slate-800 mb-4">Validity Distribution by Certificate Type</CardTitle>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={documentData.by_type}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="type" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="valid" name="Valid" fill="#10b981" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="expiring" name="Expiring Soon" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="expired" name="Expired" fill="#ef4444" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        )}

        {/* REPORT 5: REGIONAL PERFORMANCE MATRIX */}
        {!loading && activeTab === 'REGIONAL' && regionalData && (
          <div className="space-y-4">
            <Card className="p-4 bg-white border-slate-200">
              <CardTitle className="text-sm font-bold text-slate-800 mb-4">
                Regional SLA Breach Rates (%) & Cycle Times
              </CardTitle>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={regionalData.regions}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="region_code" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="sla_breach_rate_pct" name="SLA Breach Rate (%)" fill="#dc2626" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="avg_days_per_stage" name="Avg Days / Stage" fill="#2563eb" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card className="border-slate-200 bg-white overflow-hidden shadow-sm">
              <div className="p-3 bg-slate-50 border-b border-slate-200 font-bold text-xs text-slate-800">
                Official AICTE Regional Performance & Compliance Matrix
              </div>
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50/50 text-slate-600 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-4">Region Name</th>
                    <th className="py-2.5 px-3">Headquarters</th>
                    <th className="py-2.5 px-3">Total Apps</th>
                    <th className="py-2.5 px-3">With AICTE</th>
                    <th className="py-2.5 px-3">With Inst.</th>
                    <th className="py-2.5 px-3">Closed</th>
                    <th className="py-2.5 px-3">Avg Days/Stage</th>
                    <th className="py-2.5 px-3">SLA Breach %</th>
                    <th className="py-2.5 px-3">Alerts Raised</th>
                    <th className="py-2.5 px-4 text-right">Alerts Resolved</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {regionalData.regions.map((reg) => (
                    <tr key={reg.region_id} className="hover:bg-slate-50">
                      <td className="py-2.5 px-4 font-semibold text-slate-900">{reg.region_name}</td>
                      <td className="py-2.5 px-3">{reg.headquarters}</td>
                      <td className="py-2.5 px-3 font-mono font-bold">{reg.total_applications}</td>
                      <td className="py-2.5 px-3 font-mono text-blue-700">{reg.with_aicte_count ?? 0}</td>
                      <td className="py-2.5 px-3 font-mono text-amber-700">{reg.with_institution_count ?? 0}</td>
                      <td className="py-2.5 px-3 font-mono text-slate-600">{reg.closed_count ?? 0}</td>
                      <td className="py-2.5 px-3 font-mono">{reg.avg_days_per_stage}d</td>
                      <td className={`py-2.5 px-3 font-mono font-bold ${
                        reg.sla_breach_rate_pct > 20 ? 'text-rose-700' : 'text-slate-800'
                      }`}>
                        {reg.sla_breach_rate_pct}%
                      </td>
                      <td className="py-2.5 px-3 font-mono text-amber-700">{reg.alerts_raised}</td>
                      <td className="py-2.5 px-4 text-right font-mono text-emerald-700 font-bold">{reg.alerts_resolved}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </div>
        )}

        {/* REPORT 6: INSTITUTION HEALTH DOSSIER */}
        {!loading && activeTab === 'HEALTH' && healthData && (
          <div className="space-y-4">
            {/* Dossier Banner */}
            <div className="p-4 bg-gradient-to-r from-slate-900 to-blue-950 text-white rounded-lg shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-bold">{healthData.institution.name}</h2>
                  <Badge variant="outline" className="border-blue-400 text-blue-200">
                    {healthData.institution.aicte_id}
                  </Badge>
                </div>
                <p className="text-xs text-slate-300 mt-1">
                  {healthData.institution.city}, {healthData.institution.state} • Type: {healthData.institution.institution_type}
                </p>
              </div>

              <div className="flex items-center gap-4 bg-white/10 p-3 rounded-lg border border-white/20">
                <div className="text-right">
                  <div className="text-[10px] uppercase font-bold text-slate-300">Statutory Health Score</div>
                  <div className="text-xs font-semibold text-emerald-300">{healthData.health_rating}</div>
                </div>
                <div className="w-14 h-14 rounded-full bg-slate-900 border-2 border-emerald-400 flex items-center justify-center font-bold text-xl text-white">
                  {healthData.health_score}
                </div>
              </div>
            </div>

            {/* Health Stat Indicators */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Card className="p-3 bg-white border-slate-200">
                <div className="text-[10px] text-slate-500 uppercase font-bold">Applications on File</div>
                <div className="text-xl font-bold text-slate-900 mt-0.5">{healthData.stats.total_applications}</div>
              </Card>

              <Card className="p-3 bg-white border-slate-200">
                <div className="text-[10px] text-slate-500 uppercase font-bold">Open Undertakings</div>
                <div className="text-xl font-bold text-slate-900 mt-0.5">
                  {healthData.stats.open_undertakings}
                  {healthData.stats.overdue_undertakings > 0 && (
                    <span className="text-xs text-rose-700 ml-1.5 font-normal">
                      ({healthData.stats.overdue_undertakings} overdue)
                    </span>
                  )}
                </div>
              </Card>

              <Card className="p-3 bg-white border-slate-200">
                <div className="text-[10px] text-slate-500 uppercase font-bold">Expired Documents</div>
                <div className={`text-xl font-bold mt-0.5 ${healthData.stats.expired_documents > 0 ? 'text-rose-700' : 'text-slate-900'}`}>
                  {healthData.stats.expired_documents}
                </div>
              </Card>

              <Card className="p-3 bg-white border-slate-200">
                <div className="text-[10px] text-slate-500 uppercase font-bold">Complaint-Free History</div>
                <div className="mt-1 flex items-center gap-1.5 text-xs font-bold text-emerald-700">
                  <Award className="w-4 h-4 text-emerald-600" />
                  Statutory Good Standing
                </div>
              </Card>
            </div>

            {/* Dossier Tabs / Listings */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Active Conditions */}
              <Card className="border-slate-200 bg-white p-3 shadow-sm">
                <h4 className="font-bold text-xs text-slate-800 mb-2 flex items-center gap-1.5">
                  <ClipboardList className="w-3.5 h-3.5 text-indigo-700" />
                  Statutory Undertakings ({healthData.undertakings.length})
                </h4>
                <div className="space-y-2 max-h-56 overflow-y-auto">
                  {healthData.undertakings.map((u) => (
                    <div key={u.id} className="p-2 rounded border border-slate-200 bg-slate-50 text-xs flex justify-between items-center">
                      <div>
                        <div className="font-semibold text-slate-900">{u.title}</div>
                        <div className="text-[10px] text-slate-500">Due: {new Date(u.due_date).toLocaleDateString()}</div>
                      </div>
                      <Badge variant={u.status === 'VERIFIED' ? 'success' : 'secondary'} className="text-[10px]">
                        {u.status}
                      </Badge>
                    </div>
                  ))}
                  {healthData.undertakings.length === 0 && (
                    <div className="text-slate-400 text-xs italic py-4 text-center">No undertakings recorded.</div>
                  )}
                </div>
              </Card>

              {/* Monitored Documents */}
              <Card className="border-slate-200 bg-white p-3 shadow-sm">
                <h4 className="font-bold text-xs text-slate-800 mb-2 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-700" />
                  Monitored Certificates ({healthData.documents.length})
                </h4>
                <div className="space-y-2 max-h-56 overflow-y-auto">
                  {healthData.documents.map((d) => (
                    <div key={d.id} className="p-2 rounded border border-slate-200 bg-slate-50 text-xs flex justify-between items-center">
                      <div>
                        <div className="font-semibold text-slate-900">{d.title} (v{d.version})</div>
                        <div className="text-[10px] text-slate-500">Expires: {new Date(d.expiry_date).toLocaleDateString()}</div>
                      </div>
                      <Badge variant={d.urgency === 'EXPIRED' ? 'destructive' : d.urgency === 'VALID' ? 'success' : 'warning'} className="text-[10px]">
                        {d.status}
                      </Badge>
                    </div>
                  ))}
                  {healthData.documents.length === 0 && (
                    <div className="text-slate-400 text-xs italic py-4 text-center">No documents recorded.</div>
                  )}
                </div>
              </Card>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
