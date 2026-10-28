'use client';

import React, { useState, useEffect } from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/lib/auth';
import {
  evcApi,
  EvcVisit,
  EvcExpert,
  SuggestedExpert,
  lookupApi,
  Region,
  filesApi,
} from '@/lib/api';
import {
  CalendarCheck2,
  Calendar,
  Clock,
  UserCheck,
  Users,
  AlertTriangle,
  Upload,
  CheckCircle2,
  XCircle,
  FileText,
  Search,
  Filter,
  Eye,
  ShieldAlert,
  ChevronRight,
  Info,
  CalendarDays,
  List,
} from 'lucide-react';

export default function EvcQueuePage() {
  const { scope } = useAuth();
  const [visits, setVisits] = useState<EvcVisit[]>([]);
  const [regions, setRegions] = useState<Region[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Filters
  const [selectedRegion, setSelectedRegion] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState('');
  const [viewMode, setViewMode] = useState<'TABLE' | 'CALENDAR'>('TABLE');

  // Drawer / Modal state
  const [selectedVisit, setSelectedVisit] = useState<EvcVisit | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [suggestedExperts, setSuggestedExperts] = useState<SuggestedExpert[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [selectedExpertIds, setSelectedExpertIds] = useState<number[]>([]);

  // Scheduling inputs
  const [scheduledDate, setScheduledDate] = useState('');
  const [scheduledTime, setScheduledTime] = useState('10:00');
  const [instructions, setInstructions] = useState('');

  // Complete visit input
  const [visitSummary, setVisitSummary] = useState('');

  // Report upload input
  const [reportFile, setReportFile] = useState<File | null>(null);

  // Close visit remarks
  const [closeRemarks, setCloseRemarks] = useState('');

  // Action pending state
  const [actionLoading, setActionLoading] = useState(false);

  const fetchVisits = async () => {
    try {
      setLoading(true);
      setError('');
      const params: Record<string, any> = {};
      if (selectedRegion !== 'ALL') params.region_id = parseInt(selectedRegion, 10);
      if (selectedStatus !== 'ALL') params.status = selectedStatus;

      const data = await evcApi.listVisits(params);
      setVisits(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load EVC visits');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVisits();
  }, [selectedRegion, selectedStatus]);

  useEffect(() => {
    lookupApi.getRegions().then(setRegions).catch(() => {});
  }, []);

  const openDrawer = async (visit: EvcVisit) => {
    setSelectedVisit(visit);
    setDrawerOpen(true);
    setReportFile(null);
    setScheduledDate(visit.scheduled_date ? visit.scheduled_date.slice(0, 10) : '');
    setScheduledTime(visit.scheduled_time || '10:00');
    setVisitSummary(visit.remarks || '');
    setCloseRemarks('');

    // Pre-select existing panel if assigned
    if (visit.panel && visit.panel.length > 0) {
      setSelectedExpertIds(visit.panel.map((e) => e.id));
    } else {
      setSelectedExpertIds([]);
    }

    // Load suggested experts for decision support
    try {
      setLoadingSuggestions(true);
      const suggestions = await evcApi.getSuggestedExperts(visit.id);
      setSuggestedExperts(suggestions);
    } catch (err) {
      console.error('Failed to load expert recommendations', err);
    } finally {
      setLoadingSuggestions(false);
    }
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    setSelectedVisit(null);
  };

  const handleToggleExpert = (id: number) => {
    if (selectedExpertIds.includes(id)) {
      setSelectedExpertIds(selectedExpertIds.filter((item) => item !== id));
    } else {
      if (selectedExpertIds.length >= 3) {
        alert('An EVC panel must contain exactly 3 members. Please deselect one first.');
        return;
      }
      setSelectedExpertIds([...selectedExpertIds, id]);
    }
  };

  const handleAssignPanel = async () => {
    if (!selectedVisit) return;
    if (selectedExpertIds.length !== 3) {
      alert('Statutory rule requires exactly 3 panel members.');
      return;
    }
    setActionLoading(true);
    try {
      const updated = await evcApi.assignPanel(selectedVisit.id, selectedExpertIds);
      setSelectedVisit(updated);
      setSuccessMsg('✓ 3-member expert panel assigned successfully.');
      fetchVisits();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to assign panel');
    } finally {
      setActionLoading(false);
    }
  };

  const handleScheduleVisit = async () => {
    if (!selectedVisit || !scheduledDate) return;
    setActionLoading(true);
    try {
      const updated = await evcApi.scheduleVisit(selectedVisit.id, {
        scheduled_date: scheduledDate,
        scheduled_time: scheduledTime,
        instructions,
      });
      setSelectedVisit(updated);
      setSuccessMsg('✓ EVC inspection visit scheduled. Linked alerts auto-resolved.');
      fetchVisits();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to schedule visit');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCompleteVisit = async () => {
    if (!selectedVisit) return;
    setActionLoading(true);
    try {
      const updated = await evcApi.completeVisit(selectedVisit.id, visitSummary);
      setSelectedVisit(updated);
      setSuccessMsg('✓ Physical site visit marked as completed.');
      fetchVisits();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to mark visit completed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleUploadReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedVisit || !reportFile) return;
    setActionLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', reportFile);
      const updated = await evcApi.uploadReport(selectedVisit.id, formData);
      setSelectedVisit(updated);
      setSuccessMsg('✓ Inspection report uploaded successfully.');
      fetchVisits();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to upload report');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCloseVisit = async () => {
    if (!selectedVisit) return;
    setActionLoading(true);
    try {
      const updated = await evcApi.closeVisit(selectedVisit.id, closeRemarks);
      setSelectedVisit(updated);
      setSuccessMsg('✓ EVC visit closed. Application may now advance stage in case file.');
      fetchVisits();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to close visit');
    } finally {
      setActionLoading(false);
    }
  };

  // Filtered visits
  const filteredVisits = visits.filter((v) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      v.institution_name.toLowerCase().includes(term) ||
      v.application_number.toLowerCase().includes(term) ||
      v.region_name.toLowerCase().includes(term)
    );
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PENDING_ASSIGNMENT':
        return <Badge variant="warning">Pending Assignment</Badge>;
      case 'ASSIGNED':
        return <Badge variant="info">Panel Assigned</Badge>;
      case 'SCHEDULED':
        return <Badge variant="default" className="bg-indigo-600 text-white">Scheduled</Badge>;
      case 'VISIT_DONE':
        return <Badge variant="secondary" className="bg-purple-100 text-purple-900 border-purple-300">Visit Done</Badge>;
      case 'REPORT_RECEIVED':
        return <Badge variant="success">Report Received</Badge>;
      case 'CLOSED':
        return <Badge variant="secondary" className="bg-slate-200 text-slate-800">Closed</Badge>;
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
              <CalendarCheck2 className="w-5 h-5 text-blue-700" />
              EVC Inspection Scheduling Workbench
            </h1>
            <p className="text-xs text-slate-500">
              Module C: 3-member expert panel constitution, conflict verification, inspection dispatch, and report auditing.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="bg-slate-100 p-0.5 rounded-lg border border-slate-200 flex text-xs font-medium">
              <button
                onClick={() => setViewMode('TABLE')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-colors ${
                  viewMode === 'TABLE' ? 'bg-white shadow-sm text-blue-900 font-semibold' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <List className="w-3.5 h-3.5" />
                Queue Table
              </button>
              <button
                onClick={() => setViewMode('CALENDAR')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-colors ${
                  viewMode === 'CALENDAR' ? 'bg-white shadow-sm text-blue-900 font-semibold' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <CalendarDays className="w-3.5 h-3.5" />
                Inspection Calendar
              </button>
            </div>
          </div>
        </div>

        {/* Success Alert */}
        {successMsg && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-900 rounded text-xs flex items-center justify-between">
            <span>{successMsg}</span>
            <button onClick={() => setSuccessMsg('')} className="text-emerald-700 font-bold">&times;</button>
          </div>
        )}

        {/* Filters and Stats Strip */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <Card className="p-3 bg-white border-slate-200">
            <div className="text-[11px] font-semibold text-slate-500 uppercase">Total EVC Visits</div>
            <div className="text-xl font-bold text-slate-900 mt-0.5">{visits.length}</div>
            <div className="text-[10px] text-slate-400 mt-1">Across all approval stages</div>
          </Card>

          <Card className="p-3 bg-amber-50/50 border-amber-200">
            <div className="text-[11px] font-semibold text-amber-800 uppercase">Pending Assignment</div>
            <div className="text-xl font-bold text-amber-900 mt-0.5">
              {visits.filter((v) => v.status === 'PENDING_ASSIGNMENT').length}
            </div>
            <div className="text-[10px] text-amber-700 mt-1">Require panel constitution</div>
          </Card>

          <Card className="p-3 bg-blue-50/50 border-blue-200">
            <div className="text-[11px] font-semibold text-blue-800 uppercase">Scheduled Inspections</div>
            <div className="text-xl font-bold text-blue-900 mt-0.5">
              {visits.filter((v) => v.status === 'SCHEDULED').length}
            </div>
            <div className="text-[10px] text-blue-700 mt-1">Confirmed dates & assigned panels</div>
          </Card>

          <Card className="p-3 bg-emerald-50/50 border-emerald-200">
            <div className="text-[11px] font-semibold text-emerald-800 uppercase">Reports Received</div>
            <div className="text-xl font-bold text-emerald-900 mt-0.5">
              {visits.filter((v) => v.status === 'REPORT_RECEIVED' || v.status === 'CLOSED').length}
            </div>
            <div className="text-[10px] text-emerald-700 mt-1">Completed & awaiting committee scrutiny</div>
          </Card>
        </div>

        {/* Search & Filter Controls */}
        <div className="bg-white p-3 rounded-lg border border-slate-200 flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
          <div className="relative w-full md:w-80">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search institution, application no..."
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
                <option value="PENDING_ASSIGNMENT">Pending Assignment</option>
                <option value="ASSIGNED">Panel Assigned</option>
                <option value="SCHEDULED">Scheduled</option>
                <option value="VISIT_DONE">Visit Done</option>
                <option value="REPORT_RECEIVED">Report Received</option>
                <option value="CLOSED">Closed</option>
              </select>
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        {viewMode === 'TABLE' ? (
          <Card className="border-slate-200 bg-white shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-4">Institution & Application</th>
                    <th className="py-2.5 px-3">Region</th>
                    <th className="py-2.5 px-3">Days Waiting</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Assigned Panel (3 Experts)</th>
                    <th className="py-2.5 px-3">Inspection Date</th>
                    <th className="py-2.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {loading ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-400">Loading EVC queue...</td>
                    </tr>
                  ) : filteredVisits.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-500">No EVC inspection visits found.</td>
                    </tr>
                  ) : (
                    filteredVisits.map((visit) => (
                      <tr key={visit.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-slate-900">{visit.institution_name}</span>
                            {visit.is_new_institution && (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                                NEW INSTITUTION
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-500 mt-0.5 font-mono">
                            {visit.application_number} • Stage: {visit.stage_name}
                          </div>
                        </td>

                        <td className="py-3 px-3">
                          <span className="text-slate-800 font-medium">{visit.region_name}</span>
                        </td>

                        <td className="py-3 px-3">
                          <span className={`inline-flex items-center gap-1 font-mono font-medium ${
                            visit.days_waiting > 15 ? 'text-rose-700 font-bold' : 'text-slate-700'
                          }`}>
                            <Clock className="w-3 h-3 text-slate-400" />
                            {visit.days_waiting}d
                          </span>
                        </td>

                        <td className="py-3 px-3">
                          {getStatusBadge(visit.status)}
                        </td>

                        <td className="py-3 px-3">
                          {visit.panel && visit.panel.length === 3 ? (
                            <div className="space-y-1">
                              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-emerald-50 border border-emerald-200 rounded text-[10px] text-emerald-900 font-medium">
                                <Users className="w-3 h-3 text-emerald-700" />
                                3 Members Confirmed
                              </span>
                              <div className="text-[10px] text-slate-500 truncate max-w-[200px]">
                                {visit.panel.map((p) => p.name.split(' ')[0]).join(', ')}
                              </div>
                            </div>
                          ) : (
                            <span className="text-[11px] text-slate-400 italic">Panel not formed</span>
                          )}
                        </td>

                        <td className="py-3 px-3 font-mono text-[11px]">
                          {visit.scheduled_date ? (
                            <div className="text-indigo-900 font-medium">
                              {new Date(visit.scheduled_date).toLocaleDateString()}
                              {visit.scheduled_time && <span className="text-slate-500 text-[10px] ml-1">({visit.scheduled_time})</span>}
                            </div>
                          ) : (
                            <span className="text-slate-400">Unscheduled</span>
                          )}
                        </td>

                        <td className="py-3 px-4 text-right">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openDrawer(visit)}
                            className="h-7 text-xs border-blue-600 text-blue-700 hover:bg-blue-50"
                          >
                            <Calendar className="w-3 h-3 mr-1" />
                            Manage Visit
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        ) : (
          /* Calendar View */
          <Card className="border-slate-200 bg-white shadow-sm p-4">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-800">Inspection Schedule Calendar</h3>
                <p className="text-xs text-slate-500">Upcoming EVC site inspections scheduled by regional offices.</p>
              </div>
              <Badge variant="outline">{filteredVisits.filter((v) => v.scheduled_date).length} Visits Scheduled</Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {filteredVisits
                .filter((v) => v.scheduled_date)
                .sort((a, b) => (a.scheduled_date! > b.scheduled_date! ? 1 : -1))
                .map((v) => (
                  <div
                    key={v.id}
                    className="p-3 rounded-lg border border-slate-200 bg-slate-50 hover:border-blue-300 hover:bg-blue-50/20 transition-all flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <span className="text-[11px] font-bold text-indigo-900 font-mono flex items-center gap-1">
                          <Calendar className="w-3 h-3 text-indigo-600" />
                          {new Date(v.scheduled_date!).toLocaleDateString()}
                          {v.scheduled_time && <span className="text-slate-500 font-normal">@{v.scheduled_time}</span>}
                        </span>
                        {getStatusBadge(v.status)}
                      </div>

                      <div className="font-semibold text-xs text-slate-900">{v.institution_name}</div>
                      <div className="text-[11px] text-slate-500">{v.region_name} • App: {v.application_number}</div>

                      {v.panel && v.panel.length > 0 && (
                        <div className="mt-2 text-[10px] text-slate-600 bg-white p-1.5 rounded border border-slate-200">
                          <strong>Panel:</strong> {v.panel.map((p) => p.name).join(', ')}
                        </div>
                      )}
                    </div>

                    <div className="mt-3 pt-2 border-t border-slate-200 flex justify-end">
                      <Button size="sm" variant="ghost" onClick={() => openDrawer(v)} className="h-6 text-[11px] text-blue-700">
                        View Details &rarr;
                      </Button>
                    </div>
                  </div>
                ))}

              {filteredVisits.filter((v) => v.scheduled_date).length === 0 && (
                <div className="col-span-3 py-12 text-center text-slate-400 text-xs">
                  No upcoming inspections currently scheduled.
                </div>
              )}
            </div>
          </Card>
        )}

        {/* Sliding Scheduling Drawer */}
        {drawerOpen && selectedVisit && (
          <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/50 backdrop-blur-sm">
            <div className="bg-white w-full max-w-xl h-full shadow-2xl flex flex-col border-l border-slate-200 overflow-hidden animate-in slide-in-from-right duration-200">
              {/* Drawer Header */}
              <div className="bg-slate-900 text-white px-5 py-4 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-sm flex items-center gap-2">
                    <CalendarCheck2 className="w-4 h-4 text-blue-400" />
                    EVC Scheduling & Lifecycle Manager
                  </h3>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    {selectedVisit.institution_name} ({selectedVisit.application_number})
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
              <div className="flex-1 overflow-y-auto p-5 space-y-6 text-xs text-slate-700">
                {/* Visit Status Strip */}
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase font-semibold">Current State</span>
                    <div className="mt-0.5">{getStatusBadge(selectedVisit.status)}</div>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-slate-500 uppercase font-semibold">Region</span>
                    <div className="font-medium text-slate-800">{selectedVisit.region_name}</div>
                  </div>
                </div>

                {/* STEP 1: PANEL CONSTITUTION & CONFLICT CHECK */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-1.5">
                    <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                      <Users className="w-3.5 h-3.5 text-blue-700" />
                      Step 1: Constitute 3-Member Expert Panel
                    </h4>
                    <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                      selectedExpertIds.length === 3 ? 'bg-emerald-100 text-emerald-900' : 'bg-amber-100 text-amber-900'
                    }`}>
                      {selectedExpertIds.length} / 3 Selected
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-500">
                    Decision support: System ranks available synthetic experts and validates conflict rules. Humans confirm the final panel.
                  </p>

                  {loadingSuggestions ? (
                    <div className="py-4 text-center text-slate-400">Evaluating expert pool & conflict checks...</div>
                  ) : (
                    <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                      {suggestedExperts.map(({ expert, rank_score, has_conflict, conflict_reasons }) => {
                        const isSelected = selectedExpertIds.includes(expert.id);
                        return (
                          <div
                            key={expert.id}
                            onClick={() => !has_conflict && handleToggleExpert(expert.id)}
                            className={`p-2.5 rounded-lg border transition-all ${
                              has_conflict
                                ? 'border-rose-200 bg-rose-50/40 opacity-70 cursor-not-allowed'
                                : isSelected
                                ? 'border-blue-600 bg-blue-50/50 ring-1 ring-blue-500 cursor-pointer'
                                : 'border-slate-200 bg-white hover:border-slate-300 cursor-pointer'
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <div className="font-bold text-slate-900 flex items-center gap-1.5">
                                  {expert.name}
                                  <span className="text-[10px] font-normal text-slate-500">({expert.designation})</span>
                                </div>
                                <div className="text-[11px] text-slate-600">
                                  {expert.discipline} • {expert.home_institution}, {expert.city}
                                </div>
                                <div className="text-[10px] text-slate-500 mt-0.5">
                                  Active Concurrent Visits: {expert.active_visit_count} / 2 max
                                </div>
                              </div>

                              <div className="text-right shrink-0">
                                {has_conflict ? (
                                  <Badge variant="destructive" className="text-[10px]">Conflict</Badge>
                                ) : isSelected ? (
                                  <Badge variant="success" className="text-[10px]">Selected</Badge>
                                ) : (
                                  <span className="text-[10px] text-blue-700 font-semibold">Select</span>
                                )}
                              </div>
                            </div>

                            {/* Conflict explanations in plain words */}
                            {has_conflict && (
                              <div className="mt-1.5 p-1.5 bg-rose-100/70 border border-rose-200 rounded text-rose-900 text-[10px] space-y-0.5">
                                {conflict_reasons.map((r, idx) => (
                                  <div key={idx} className="flex items-center gap-1">
                                    <AlertTriangle className="w-2.5 h-2.5 shrink-0 text-rose-700" />
                                    <span>{r}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {selectedVisit.status === 'PENDING_ASSIGNMENT' && (
                    <Button
                      size="sm"
                      onClick={handleAssignPanel}
                      disabled={actionLoading || selectedExpertIds.length !== 3}
                      className="w-full bg-blue-800 hover:bg-blue-900 text-white"
                    >
                      {actionLoading ? 'Assigning Panel...' : 'Confirm 3-Member Panel'}
                    </Button>
                  )}
                </div>

                {/* STEP 2: DATE & TIME SCHEDULING */}
                <div className="space-y-3 pt-3 border-t border-slate-200">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-indigo-700" />
                      Step 2: Date & Time Scheduling
                    </h4>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="font-semibold text-slate-700 block mb-1">Inspection Date:</label>
                      <input
                        type="date"
                        value={scheduledDate}
                        onChange={(e) => setScheduledDate(e.target.value)}
                        className="w-full p-2 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-blue-700"
                      />
                    </div>
                    <div>
                      <label className="font-semibold text-slate-700 block mb-1">Assembly Time:</label>
                      <input
                        type="time"
                        value={scheduledTime}
                        onChange={(e) => setScheduledTime(e.target.value)}
                        className="w-full p-2 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-blue-700"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="font-semibold text-slate-700 block mb-1">Instructions to Committee:</label>
                    <textarea
                      rows={2}
                      value={instructions}
                      onChange={(e) => setInstructions(e.target.value)}
                      placeholder="Special focus areas (e.g. fire safety equipment verification, faculty attendance records)..."
                      className="w-full p-2 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-blue-700"
                    />
                  </div>

                  {['PENDING_ASSIGNMENT', 'ASSIGNED', 'SCHEDULED'].includes(selectedVisit.status) && (
                    <Button
                      size="sm"
                      onClick={handleScheduleVisit}
                      disabled={actionLoading || !scheduledDate || selectedVisit.panel.length !== 3}
                      className="w-full bg-indigo-700 hover:bg-indigo-800 text-white"
                    >
                      {actionLoading ? 'Scheduling...' : 'Confirm Inspection Date & Auto-Resolve Alerts'}
                    </Button>
                  )}
                </div>

                {/* STEP 3: PHYSICAL VISIT COMPLETION */}
                {['SCHEDULED', 'VISIT_DONE', 'REPORT_RECEIVED', 'CLOSED'].includes(selectedVisit.status) && (
                  <div className="space-y-3 pt-3 border-t border-slate-200">
                    <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-purple-700" />
                      Step 3: Physical Site Visit Execution
                    </h4>

                    {selectedVisit.visit_completed_at ? (
                      <div className="p-2.5 bg-purple-50 border border-purple-200 rounded text-purple-900 text-xs">
                        ✓ Physical site visit completed on {new Date(selectedVisit.visit_completed_at).toLocaleString()}
                        {selectedVisit.remarks && <div className="mt-1 text-[11px] text-purple-800">Summary: {selectedVisit.remarks}</div>}
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <textarea
                          rows={2}
                          value={visitSummary}
                          onChange={(e) => setVisitSummary(e.target.value)}
                          placeholder="Brief summary of physical site inspection (cadre verified, infrastructure inspected)..."
                          className="w-full p-2 border border-slate-300 rounded text-xs"
                        />
                        <Button
                          size="sm"
                          onClick={handleCompleteVisit}
                          disabled={actionLoading}
                          className="w-full bg-purple-700 hover:bg-purple-800 text-white"
                        >
                          Mark Physical Visit Completed
                        </Button>
                      </div>
                    )}
                  </div>
                )}

                {/* STEP 4: REPORT UPLOAD */}
                {['VISIT_DONE', 'REPORT_RECEIVED', 'CLOSED'].includes(selectedVisit.status) && (
                  <div className="space-y-3 pt-3 border-t border-slate-200">
                    <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                      <Upload className="w-3.5 h-3.5 text-blue-700" />
                      Step 4: Upload Committee Inspection Report
                    </h4>

                    {selectedVisit.report_file_id ? (
                      <div className="p-2.5 bg-emerald-50 border border-emerald-200 rounded text-emerald-900 text-xs flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-emerald-700" />
                          <span>Report on record: {selectedVisit.report_file_name || 'EVC_Report.pdf'}</span>
                        </div>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => filesApi.downloadFile(selectedVisit.report_file_id!)}
                          className="h-6 text-[10px] border-emerald-600 text-emerald-800 hover:bg-emerald-100"
                        >
                          Download
                        </Button>
                      </div>
                    ) : (
                      <form onSubmit={handleUploadReport} className="space-y-2">
                        <input
                          type="file"
                          accept=".pdf,.png,.jpg"
                          onChange={(e) => setReportFile(e.target.files ? e.target.files[0] : null)}
                          className="w-full p-1.5 border border-slate-300 rounded text-xs"
                          required
                        />
                        <Button
                          type="submit"
                          size="sm"
                          disabled={actionLoading || !reportFile}
                          className="w-full bg-blue-800 hover:bg-blue-900 text-white"
                        >
                          {actionLoading ? 'Uploading Report...' : 'Upload Signed EVC Report'}
                        </Button>
                      </form>
                    )}
                  </div>
                )}

                {/* STEP 5: CLOSE VISIT & TRANSITION APPLICATION */}
                {['REPORT_RECEIVED'].includes(selectedVisit.status) && (
                  <div className="space-y-3 pt-3 border-t border-slate-200">
                    <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                      <ShieldAlert className="w-3.5 h-3.5 text-emerald-700" />
                      Step 5: Finalize & Close EVC Cycle
                    </h4>

                    <div className="p-2 bg-blue-50 border border-blue-200 rounded text-blue-900 text-[11px]">
                      <strong>Statutory Governance:</strong> Closing this EVC visit concludes the inspection phase. The scrutiny officer may then advance the case to SAC/SHC in the Application workbench.
                    </div>

                    <textarea
                      rows={2}
                      value={closeRemarks}
                      onChange={(e) => setCloseRemarks(e.target.value)}
                      placeholder="Final coordinator endorsement remarks..."
                      className="w-full p-2 border border-slate-300 rounded text-xs"
                    />

                    <Button
                      size="sm"
                      onClick={handleCloseVisit}
                      disabled={actionLoading}
                      className="w-full bg-emerald-700 hover:bg-emerald-800 text-white"
                    >
                      {actionLoading ? 'Closing...' : 'Close EVC Visit'}
                    </Button>
                  </div>
                )}
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
