'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth';
import { apiClient } from '@/lib/api';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { DecisionSupportBadge } from '@/components/ui/DecisionSupportBadge';
import {
  Sliders,
  TrendingDown,
  CalendarCheck2,
  Users,
  ShieldAlert,
  ArrowRight,
  Info,
  CheckCircle2,
  Clock,
  Sparkles
} from 'lucide-react';

interface MovingForwardCase {
  rank: number;
  application_id: number;
  application_number: string;
  institution_name: string;
  region_name: string;
  current_dwell_days: number;
  cleared_in_week: number;
  cleared_by: string;
}

interface WeeklyProjection {
  week: number;
  baseline_cleared: number;
  baseline_backlog: number;
  scenario_cleared: number;
  scenario_backlog: number;
}

interface WhatIfResponse {
  inputs: {
    region_id: number | null;
    region_name: string;
    extra_visits_per_week: number;
    extra_staffing_capacity: number;
    horizon_weeks: number;
  };
  assumptions: {
    baseline_completion_rate_per_week: number;
    scenario_completion_rate_per_week: number;
    added_visits_per_staff_unit: number;
    historical_sample_weeks: number;
    note: string;
  };
  summary: {
    current_backlog: number;
    current_avg_wait_days: number;
    baseline_projected_backlog: number;
    scenario_projected_backlog: number;
    baseline_cases_cleared: number;
    scenario_cases_cleared: number;
    additional_cases_cleared: number;
    avoided_overdue_alerts: number;
    backlog_reduction_percent: number;
  };
  weekly_projection: WeeklyProjection[];
  cases_moving_forward: MovingForwardCase[];
  disclaimer: string;
}

interface RegionItem {
  id: number;
  name: string;
  code: string;
}

export default function WhatIfPlannerPage() {
  const { scope } = useAuth();
  const [regions, setRegions] = useState<RegionItem[]>([]);
  const [selectedRegion, setSelectedRegion] = useState<string>('');
  const [extraVisits, setExtraVisits] = useState<number>(3);
  const [extraStaffing, setExtraStaffing] = useState<number>(1);
  const [horizonWeeks, setHorizonWeeks] = useState<number>(4);

  const [data, setData] = useState<WhatIfResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRegions = async () => {
    try {
      const res = await apiClient.get<RegionItem[]>('/regions');
      setRegions(res.data);
    } catch (e) {
      // Ignore region load error
    }
  };

  const runSimulation = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.post<WhatIfResponse>('/planner/simulate', {
        region_id: selectedRegion ? parseInt(selectedRegion, 10) : null,
        extra_visits_per_week: extraVisits,
        extra_staffing_capacity: extraStaffing,
        horizon_weeks: horizonWeeks,
      });
      setData(res.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to execute capacity simulation.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRegions();
  }, []);

  useEffect(() => {
    runSimulation();
  }, [selectedRegion, extraVisits, extraStaffing, horizonWeeks]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              What-If Capacity Planner (EVC Inspections)
            </h1>
            <DecisionSupportBadge size="sm" />
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Counterfactual capacity and staffing simulation for Expert Visit Committee queues. Strictly read-only modeling.
          </p>
        </div>

        <Badge variant="outline" className="text-xs font-medium text-blue-700 bg-blue-50 border-blue-200 self-start sm:self-auto">
          Strictly Read-Only Modeling
        </Badge>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
          {error}
        </div>
      )}

      {/* Control Panel: Simulation Sliders */}
      <Card className="p-5 border-slate-200 bg-slate-50/50">
        <div className="flex items-center gap-2 pb-3 border-b border-slate-200">
          <Sliders className="w-4 h-4 text-blue-600" />
          <h2 className="text-sm font-semibold text-slate-900">Simulation Levers & Scope</h2>
          <span className="text-[11px] text-slate-400 ml-auto">Adjust levers to view instantaneous projected impacts</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mt-4">
          {/* Region selector */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Regional Jurisdiction
            </label>
            <select
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
              disabled={scope?.is_regional && scope?.role !== 'ADMIN' && scope?.role !== 'BUREAU_OFFICER'}
              className="w-full bg-white border border-slate-300 rounded-md px-3 py-2 text-xs font-medium text-slate-800 shadow-xs focus:ring-1 focus:ring-blue-500"
            >
              <option value="">All Regions</option>
              {regions.map((r) => (
                <option key={r.id} value={r.id.toString()}>
                  {r.name}
                </option>
              ))}
            </select>
            <span className="text-[10px] text-slate-400 mt-1 block">Scope of EVC queue</span>
          </div>

          {/* Lever 1: Extra visits per week */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-slate-700">Extra Visits / Week</label>
              <span className="text-xs font-bold text-blue-700 bg-blue-100 px-2 py-0.5 rounded">
                +{extraVisits} visits/wk
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={10}
              step={1}
              value={extraVisits}
              onChange={(e) => setExtraVisits(parseInt(e.target.value, 10))}
              className="w-full accent-blue-600 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400 mt-1">
              <span>0 (Baseline)</span>
              <span>+5</span>
              <span>+10</span>
            </div>
          </div>

          {/* Lever 2: Extra staffing capacity */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-slate-700">Extra Staffing Capacity</label>
              <span className="text-xs font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">
                +{extraStaffing} officers
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={5}
              step={1}
              value={extraStaffing}
              onChange={(e) => setExtraStaffing(parseInt(e.target.value, 10))}
              className="w-full accent-emerald-600 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400 mt-1">
              <span>0 (Current)</span>
              <span>+2</span>
              <span>+5</span>
            </div>
          </div>

          {/* Lever 3: Planning Horizon */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-slate-700">Planning Horizon</label>
              <span className="text-xs font-bold text-indigo-700 bg-indigo-100 px-2 py-0.5 rounded">
                {horizonWeeks} weeks
              </span>
            </div>
            <input
              type="range"
              min={1}
              max={8}
              step={1}
              value={horizonWeeks}
              onChange={(e) => setHorizonWeeks(parseInt(e.target.value, 10))}
              className="w-full accent-indigo-600 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400 mt-1">
              <span>1 week</span>
              <span>4 weeks</span>
              <span>8 weeks</span>
            </div>
          </div>
        </div>
      </Card>

      {/* KPI Comparison Cards: Baseline vs Scenario */}
      {data && (
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <Card className="p-4 border-slate-200">
            <span className="text-xs font-medium text-slate-500">Queue Backlog</span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-slate-900">{data.summary.scenario_projected_backlog}</span>
              <span className="text-xs text-slate-400 line-through">
                {data.summary.baseline_projected_backlog} baseline
              </span>
            </div>
            <div className="text-[11px] text-emerald-700 font-medium mt-1">
              -{data.summary.backlog_reduction_percent}% reduction vs current
            </div>
          </Card>

          <Card className="p-4 border-slate-200">
            <span className="text-xs font-medium text-slate-500">Cases Cleared</span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-emerald-800">
                {data.summary.scenario_cases_cleared}
              </span>
              <span className="text-xs text-slate-500">
                (+{data.summary.additional_cases_cleared} additional)
              </span>
            </div>
            <div className="text-[11px] text-slate-500 mt-1">
              Over {horizonWeeks} week horizon
            </div>
          </Card>

          <Card className="p-4 border-slate-200">
            <span className="text-xs font-medium text-slate-500">Avoided Overdue Alerts</span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-indigo-800">
                {data.summary.avoided_overdue_alerts}
              </span>
              <span className="text-xs text-slate-500">prevented</span>
            </div>
            <div className="text-[11px] text-indigo-700 mt-1">
              Statutory breaches avoided by faster inspection
            </div>
          </Card>

          <Card className="p-4 border-slate-200">
            <span className="text-xs font-medium text-slate-500">Weekly Throughput Rate</span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-blue-900">
                {data.assumptions.scenario_completion_rate_per_week}
              </span>
              <span className="text-xs text-slate-400">
                /wk (vs {data.assumptions.baseline_completion_rate_per_week} base)
              </span>
            </div>
            <div className="text-[11px] text-slate-500 mt-1">
              Inspections completed per 7-day cycle
            </div>
          </Card>
        </div>
      )}

      {/* Projection Chart & Trajectory */}
      {data && data.weekly_projection.length > 0 && (
        <Card className="p-5 border-slate-200">
          <div className="pb-3 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-900">
                Backlog Depletion Trajectory ({data.inputs.region_name})
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Week-by-week backlog progression under baseline capacity vs simulation scenario.
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded bg-slate-300 inline-block" />
                <span className="text-slate-600">Baseline Backlog</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded bg-blue-600 inline-block" />
                <span className="text-slate-900 font-medium">Scenario Backlog</span>
              </div>
            </div>
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold">
                  <th className="py-2.5 px-3">Timeline</th>
                  <th className="py-2.5 px-3 text-right">Baseline Weekly Cleared</th>
                  <th className="py-2.5 px-3 text-right">Baseline Remaining Backlog</th>
                  <th className="py-2.5 px-3 text-right">Scenario Weekly Cleared</th>
                  <th className="py-2.5 px-3 text-right">Scenario Remaining Backlog</th>
                  <th className="py-2.5 px-3">Backlog Depletion Visual</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.weekly_projection.map((wp) => {
                  const maxBacklog = Math.max(data.summary.current_backlog, 1);
                  const baseWidth = Math.round((wp.baseline_backlog / maxBacklog) * 100);
                  const scenWidth = Math.round((wp.scenario_backlog / maxBacklog) * 100);

                  return (
                    <tr key={wp.week} className="hover:bg-slate-50/50">
                      <td className="py-3 px-3 font-semibold text-slate-900">Week {wp.week}</td>
                      <td className="py-3 px-3 text-right text-slate-600">{wp.baseline_cleared} cases</td>
                      <td className="py-3 px-3 text-right font-medium text-slate-700">{wp.baseline_backlog} cases</td>
                      <td className="py-3 px-3 text-right font-semibold text-blue-700">
                        {wp.scenario_cleared} cases
                      </td>
                      <td className="py-3 px-3 text-right font-bold text-slate-900">
                        {wp.scenario_backlog} cases
                      </td>
                      <td className="py-3 px-3 w-1/3">
                        <div className="space-y-1">
                          <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                            <div className="bg-slate-400 h-2 rounded-full" style={{ width: `${baseWidth}%` }} />
                          </div>
                          <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                            <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${scenWidth}%` }} />
                          </div>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Cases Moving Forward in Simulation */}
      {data?.cases_moving_forward && data.cases_moving_forward.length > 0 && (
        <Card className="p-5 border-slate-200">
          <div className="pb-3 border-b border-slate-200">
            <h2 className="text-base font-semibold text-slate-900">
              Applications Advancing Under Simulated Capacity
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              FIFO order queue simulation: Applications that would exit the EVC queue during this {horizonWeeks}-week horizon.
            </p>
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold">
                  <th className="py-2.5 px-3">Queue Rank</th>
                  <th className="py-2.5 px-3">Application Number</th>
                  <th className="py-2.5 px-3">Institution Name</th>
                  <th className="py-2.5 px-3">Region</th>
                  <th className="py-2.5 px-3 text-right">Current Dwell</th>
                  <th className="py-2.5 px-3 text-center">Projected Exit Week</th>
                  <th className="py-2.5 px-3">Capacity Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.cases_moving_forward.map((c) => (
                  <tr key={c.application_id} className="hover:bg-slate-50/50">
                    <td className="py-2.5 px-3 font-medium text-slate-500">#{c.rank}</td>
                    <td className="py-2.5 px-3 font-semibold text-blue-900">{c.application_number}</td>
                    <td className="py-2.5 px-3 text-slate-700">{c.institution_name}</td>
                    <td className="py-2.5 px-3 text-slate-600">{c.region_name}</td>
                    <td className="py-2.5 px-3 text-right text-slate-800 font-medium">
                      {c.current_dwell_days} days
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <span className="inline-block px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                        Week {c.cleared_in_week}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-600 text-[11px]">
                      {c.cleared_by}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Assumptions & Methodology Block */}
      {data?.assumptions && (
        <Card className="p-4 border-slate-200 bg-slate-50 text-xs">
          <div className="flex items-center gap-2 font-semibold text-slate-800 mb-2">
            <Info className="w-4 h-4 text-blue-600" />
            <span>Underlying Mathematical Modeling & Assumptions</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-slate-600">
            <div>
              <span className="font-medium text-slate-700">Baseline Completion Rate: </span>
              {data.assumptions.baseline_completion_rate_per_week} visits/week (measured from last {data.assumptions.historical_sample_weeks} weeks of real event timestamps).
            </div>
            <div>
              <span className="font-medium text-slate-700">Staffing Productivity Multiplier: </span>
              +{data.assumptions.added_visits_per_staff_unit} visits per added staff unit per week.
            </div>
            <div>
              <span className="font-medium text-slate-700">Queue Processing Policy: </span>
              FIFO (First-In, First-Out) by stage entry date, respecting regional jurisdictions.
            </div>
          </div>
        </Card>
      )}

      {/* Footer Disclaimer */}
      <div className="p-3 bg-slate-100 rounded-lg text-[11px] text-slate-600 flex items-start gap-2 border border-slate-200">
        <ShieldAlert className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-slate-800">Decision Support Only: </span>
          {data?.disclaimer || "Estimate, decision support only. Automation assists planning; statutory inspection scheduling and decision authority remain strictly with authorized officers."}
        </div>
      </div>
    </div>
  );
}
