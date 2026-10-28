'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { 
  applicationsApi, lookupApi, configApi,
  ApplicationItem, Region, Stage, ApplicationCategory, UserScope 
} from '@/lib/api';
import { 
  FileText, Search, Filter, Clock, AlertTriangle, CheckCircle, 
  PlusCircle, ArrowRight, RefreshCw, FastForward, Building2, MapPin
} from 'lucide-react';

export default function ApplicationsListPage() {
  const router = useRouter();
  const [scope, setScope] = useState<UserScope | null>(null);
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [regions, setRegions] = useState<Region[]>([]);
  const [stages, setStages] = useState<Stage[]>([]);
  const [categories, setCategories] = useState<ApplicationCategory[]>([]);

  // Filters & Pagination
  const [search, setSearch] = useState<string>('');
  const [stageFilter, setStageFilter] = useState<string>('');
  const [bucketFilter, setBucketFilter] = useState<string>('');
  const [regionFilter, setRegionFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const limit = 15;

  // Modals
  const [showNewModal, setShowNewModal] = useState<boolean>(false);
  const [showClockModal, setShowClockModal] = useState<boolean>(false);
  const [clockHours, setClockHours] = useState<number>(48);
  const [clockMessage, setClockMessage] = useState<string>('');
  const [submittingApp, setSubmittingApp] = useState<boolean>(false);
  const [newAppForm, setNewAppForm] = useState({
    institution_id: 1,
    category_id: 1
  });

  const loadData = async () => {
    try {
      setLoading(true);
      const [scopeRes, regsRes, stagesRes, catsRes] = await Promise.all([
        lookupApi.getScope(),
        lookupApi.getRegions(),
        configApi.getStages(),
        applicationsApi.getCategories()
      ]);
      setScope(scopeRes);
      setRegions(regsRes);
      setStages(stagesRes);
      setCategories(catsRes);

      const params: Record<string, any> = {
        skip: (page - 1) * limit,
        limit: limit
      };
      if (search.trim()) params.search = search.trim();
      if (stageFilter) params.stage = stageFilter;
      if (bucketFilter) params.ageing_bucket = bucketFilter;
      if (regionFilter) params.region_id = parseInt(regionFilter);
      if (statusFilter) params.status = statusFilter;

      const appRes = await applicationsApi.list(params);
      setApplications(appRes.applications);
      setTotal(appRes.total);
    } catch (err) {
      console.error('Failed to load applications list:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [page, stageFilter, bucketFilter, regionFilter, statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadData();
  };

  const handleAdvanceClock = async () => {
    try {
      const res = await applicationsApi.advanceClock(clockHours);
      setClockMessage(`✓ Simulated time advanced by ${res.advanced_hours} hours.`);
      setTimeout(() => {
        setClockMessage('');
        setShowClockModal(false);
        loadData();
      }, 1200);
    } catch (err: any) {
      setClockMessage(err.response?.data?.detail || 'Failed to advance clock.');
    }
  };

  const handleResetClock = async () => {
    try {
      await applicationsApi.resetClock();
      setClockMessage('✓ Simulated time reset to real-time UTC.');
      setTimeout(() => {
        setClockMessage('');
        setShowClockModal(false);
        loadData();
      }, 1200);
    } catch (err: any) {
      setClockMessage(err.response?.data?.detail || 'Failed to reset clock.');
    }
  };

  const handleCreateApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingApp(true);
    try {
      const created = await applicationsApi.create({
        institution_id: Number(newAppForm.institution_id),
        category_id: Number(newAppForm.category_id)
      });
      setShowNewModal(false);
      router.push(`/applications/${created.id}`);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to submit application');
    } finally {
      setSubmittingApp(false);
    }
  };

  const getBucketBadge = (bucket: string) => {
    switch (bucket) {
      case 'ON_TIME':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">On Time</span>;
      case 'NEAR_DUE':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">Near Breach</span>;
      case 'OVERDUE':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-200 animate-pulse">Overdue</span>;
      case 'COMPLETED':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">Concluded</span>;
      default:
        return <Badge variant="neutral">{bucket}</Badge>;
    }
  };

  const getStatusBadge = (status: string) => {
    if (status === 'APPROVED') {
      return <Badge variant="success">Approved</Badge>;
    }
    if (status === 'REJECTED') {
      return <Badge variant="danger">Rejected</Badge>;
    }
    return <Badge variant="info">In Progress</Badge>;
  };

  return (
    <AppShell>
      <div className="space-y-5">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-4">
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-800" />
              Applications Dossier & Lifecycle Management
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              Active statutory workflows across 5 AICTE Regional Offices. Enforces APH 2026 SLAs and revert ceilings.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {scope?.role === 'ADMIN' && (
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => setShowClockModal(true)}
                className="text-amber-800 border-amber-300 hover:bg-amber-50"
              >
                <FastForward className="w-4 h-4 mr-1 text-amber-600" />
                Demo Clock (+48h)
              </Button>
            )}
            {(scope?.is_institution || scope?.role === 'ADMIN') && (
              <Button 
                size="sm" 
                onClick={() => setShowNewModal(true)}
                className="bg-blue-800 hover:bg-blue-900 text-white"
              >
                <PlusCircle className="w-4 h-4 mr-1" />
                New Application
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={loadData}>
              <RefreshCw className="w-4 h-4 text-slate-600" />
            </Button>
          </div>
        </div>

        {/* Filters Toolbar */}
        <Card className="bg-slate-50/70 border-slate-200">
          <CardContent className="p-3">
            <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 md:grid-cols-6 gap-2">
              <div className="md:col-span-2 relative">
                <Search className="w-4 h-4 absolute left-2.5 top-2.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search application number or institute..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-xs rounded border border-slate-300 bg-white focus:outline-none focus:ring-1 focus:ring-blue-700"
                />
              </div>

              <div>
                <select
                  value={stageFilter}
                  onChange={(e) => { setStageFilter(e.target.value); setPage(1); }}
                  className="w-full py-1.5 px-2 text-xs rounded border border-slate-300 bg-white focus:outline-none focus:ring-1 focus:ring-blue-700"
                >
                  <option value="">All Stages</option>
                  {stages.map((s) => (
                    <option key={s.id} value={s.code}>{s.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <select
                  value={bucketFilter}
                  onChange={(e) => { setBucketFilter(e.target.value); setPage(1); }}
                  className="w-full py-1.5 px-2 text-xs rounded border border-slate-300 bg-white focus:outline-none focus:ring-1 focus:ring-blue-700"
                >
                  <option value="">All SLA Statuses</option>
                  <option value="ON_TIME">On Time</option>
                  <option value="NEAR_DUE">Near Due (80%+)</option>
                  <option value="OVERDUE">Overdue (Breached)</option>
                  <option value="COMPLETED">Concluded</option>
                </select>
              </div>

              <div>
                <select
                  value={regionFilter}
                  onChange={(e) => { setRegionFilter(e.target.value); setPage(1); }}
                  className="w-full py-1.5 px-2 text-xs rounded border border-slate-300 bg-white focus:outline-none focus:ring-1 focus:ring-blue-700"
                  disabled={scope?.is_regional}
                >
                  <option value="">All Regions</option>
                  {regions.map((r) => (
                    <option key={r.id} value={r.id.toString()}>{r.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <select
                  value={statusFilter}
                  onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
                  className="w-full py-1.5 px-2 text-xs rounded border border-slate-300 bg-white focus:outline-none focus:ring-1 focus:ring-blue-700"
                >
                  <option value="">All Statuses</option>
                  <option value="IN_PROGRESS">In Progress</option>
                  <option value="APPROVED">Approved</option>
                  <option value="REJECTED">Rejected</option>
                </select>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Applications Data Table */}
        <Card className="border-slate-200 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-100 border-b border-slate-200 text-slate-700 font-semibold uppercase tracking-wider">
                  <th className="py-2.5 px-3">App Number</th>
                  <th className="py-2.5 px-3">Institution & Region</th>
                  <th className="py-2.5 px-3">Pathway</th>
                  <th className="py-2.5 px-3">Current Stage</th>
                  <th className="py-2.5 px-3">SLA Status</th>
                  <th className="py-2.5 px-3 text-center">Dwell / Rem.</th>
                  <th className="py-2.5 px-3 text-center">Reverts</th>
                  <th className="py-2.5 px-3 text-center">Risk</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {loading ? (
                  <tr>
                    <td colSpan={9} className="py-12 text-center text-slate-400">
                      <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-blue-700" />
                      Loading dossiers...
                    </td>
                  </tr>
                ) : applications.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="py-12 text-center text-slate-400">
                      No applications found matching the selected filter criteria.
                    </td>
                  </tr>
                ) : (
                  applications.map((app) => (
                    <tr 
                      key={app.id} 
                      className={`hover:bg-slate-50/80 transition-colors ${
                        app.escalation_required ? 'bg-amber-50/40' : ''
                      }`}
                    >
                      <td className="py-2.5 px-3 font-mono font-semibold text-blue-800">
                        <Link href={`/applications/${app.id}`} className="hover:underline flex items-center gap-1">
                          {app.application_number}
                          {app.escalation_required && (
                            <span title="Escalation Required: Revert Cap Exceeded">
                              <AlertTriangle className="w-3.5 h-3.5 text-amber-600 inline" />
                            </span>
                          )}
                        </Link>
                      </td>
                      <td className="py-2.5 px-3 max-w-[220px]">
                        <div className="font-medium text-slate-900 truncate" title={app.institution_name}>
                          {app.institution_name}
                        </div>
                        <div className="text-[10px] text-slate-500 flex items-center gap-1 mt-0.5">
                          <MapPin className="w-2.5 h-2.5 text-slate-400" />
                          {app.region_name}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 max-w-[140px]">
                        <span className="text-[11px] text-slate-600 block truncate" title={app.stage_path_name}>
                          {app.stage_path_name.replace('Path ', 'P')}
                        </span>
                        <span className="text-[10px] text-slate-400 truncate block">
                          {app.category_title}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="font-medium text-slate-800 block text-[11px]">
                          {app.current_stage_name}
                        </span>
                        <span className="text-[10px] text-slate-500">
                          Desk: {app.assigned_officer_name || 'Central Queue'}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        {getBucketBadge(app.ageing_bucket)}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <div className="font-semibold text-slate-800">
                          {app.days_in_stage}d in stage
                        </div>
                        <div className="text-[10px] text-slate-500">
                          {app.days_remaining >= 0 ? `${app.days_remaining}d rem.` : `${Math.abs(app.days_remaining)}d overdue`}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <span className={`inline-block px-1.5 py-0.5 rounded text-[11px] font-mono ${
                          app.revert_count >= 2 ? 'bg-amber-100 text-amber-900 font-bold' : 'bg-slate-100 text-slate-700'
                        }`}>
                          {app.revert_count} / 2
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <span className={`text-[11px] font-semibold ${
                          app.delay_risk_score > 0.7 ? 'text-rose-600 font-bold' :
                          app.delay_risk_score > 0.4 ? 'text-amber-600' : 'text-slate-500'
                        }`}>
                          {Math.round(app.delay_risk_score * 100)}%
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <Link href={`/applications/${app.id}`}>
                          <Button variant="ghost" size="sm" className="h-7 text-xs text-blue-700 hover:text-blue-900 hover:bg-blue-50">
                            Dossier
                            <ArrowRight className="w-3 h-3 ml-1" />
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div className="bg-slate-50 border-t border-slate-200 px-4 py-2.5 flex items-center justify-between text-xs text-slate-600">
            <div>
              Showing {applications.length > 0 ? (page - 1) * limit + 1 : 0} to {Math.min(page * limit, total)} of {total} records
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </Button>
              <span className="px-2 font-medium">Page {page} of {Math.max(1, Math.ceil(total / limit))}</span>
              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs"
                disabled={page * limit >= total}
                onClick={() => setPage(page + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        </Card>

        {/* Modal: New Application */}
        {showNewModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full border border-slate-200 overflow-hidden">
              <div className="bg-slate-900 text-white px-4 py-3 flex items-center justify-between">
                <h3 className="font-semibold text-sm flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-blue-400" />
                  Initiate New Technical Approval Application
                </h3>
                <button onClick={() => setShowNewModal(false)} className="text-slate-400 hover:text-white">&times;</button>
              </div>
              <form onSubmit={handleCreateApplication} className="p-4 space-y-4 text-xs">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Applying Institution</label>
                  <select
                    value={newAppForm.institution_id}
                    onChange={(e) => setNewAppForm({ ...newAppForm, institution_id: parseInt(e.target.value) })}
                    className="w-full p-2 border border-slate-300 rounded bg-white text-xs"
                    required
                  >
                    <option value={1}>Apex Institute of Technology, Kanpur (RO_NORTH)</option>
                    <option value={4}>Sahyadri College of Engineering & Tech, Pune (RO_WEST)</option>
                    <option value={7}>Kaveri Institute of Technology, Coimbatore (RO_SOUTH)</option>
                    <option value={10}>Kalinga Institute of Engineering, Bhubaneswar (RO_EAST)</option>
                    <option value={13}>Malwa Institute of Technology, Indore (RO_CENTRAL)</option>
                  </select>
                </div>

                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Approval Category</label>
                  <select
                    value={newAppForm.category_id}
                    onChange={(e) => setNewAppForm({ ...newAppForm, category_id: parseInt(e.target.value) })}
                    className="w-full p-2 border border-slate-300 rounded bg-white text-xs"
                    required
                  >
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>{c.title}</option>
                    ))}
                  </select>
                </div>

                <div className="p-2.5 bg-blue-50 border border-blue-200 rounded text-blue-900 text-[11px] leading-relaxed">
                  <strong>Statutory Notice:</strong> Submitting creates a legal dossier docketed under APH 2026. The initial stage timer commences immediately and alerts Regional Scrutiny officers.
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                  <Button type="button" variant="outline" size="sm" onClick={() => setShowNewModal(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" size="sm" disabled={submittingApp} className="bg-blue-800 hover:bg-blue-900 text-white">
                    {submittingApp ? 'Submitting...' : 'Docket & Launch Workflow'}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal: Demo Time Travel Clock */}
        {showClockModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
            <div className="bg-white rounded-lg shadow-xl max-w-sm w-full border border-slate-200 overflow-hidden">
              <div className="bg-slate-900 text-white px-4 py-3 flex items-center justify-between">
                <h3 className="font-semibold text-sm flex items-center gap-2">
                  <FastForward className="w-4 h-4 text-amber-400" />
                  Presentation Time Travel (Demo Clock)
                </h3>
                <button onClick={() => setShowClockModal(false)} className="text-slate-400 hover:text-white">&times;</button>
              </div>
              <div className="p-4 space-y-4 text-xs">
                <p className="text-slate-600">
                  Simulate passing statutory deadlines to demonstrate SLA near-breach warnings and overdue alerts across the national dashboard.
                </p>

                <div className="flex gap-2">
                  <Button 
                    type="button" 
                    variant="outline" 
                    size="sm" 
                    className="flex-1 border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-900"
                    onClick={() => { setClockHours(24); handleAdvanceClock(); }}
                  >
                    +24 Hours
                  </Button>
                  <Button 
                    type="button" 
                    variant="outline" 
                    size="sm" 
                    className="flex-1 border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-900"
                    onClick={() => { setClockHours(48); handleAdvanceClock(); }}
                  >
                    +48 Hours
                  </Button>
                  <Button 
                    type="button" 
                    variant="outline" 
                    size="sm" 
                    className="flex-1 border-rose-300 bg-rose-50 hover:bg-rose-100 text-rose-900"
                    onClick={() => { setClockHours(120); handleAdvanceClock(); }}
                  >
                    +5 Days
                  </Button>
                </div>

                <div className="pt-2 border-t border-slate-100 flex justify-between items-center">
                  <Button type="button" variant="ghost" size="sm" onClick={handleResetClock} className="text-slate-500 hover:text-slate-800">
                    Reset to Real-Time
                  </Button>
                  <Button type="button" variant="outline" size="sm" onClick={() => setShowClockModal(false)}>
                    Close
                  </Button>
                </div>

                {clockMessage && (
                  <div className="p-2 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded text-center font-medium">
                    {clockMessage}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
