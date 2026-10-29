'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth';
import { apiClient } from '@/lib/api';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { DecisionSupportBadge } from '@/components/ui/DecisionSupportBadge';
import { Filter, RefreshCw, AlertTriangle, Clock, Layers, Users, Building, ShieldAlert } from 'lucide-react';

interface BottleneckItem {
  stage_code: string;
  stage_name: string;
  region_id: number;
  region_name: string;
  open_cases: number;
  avg_aicte_days: number;
  avg_institution_days: number;
  sla_days: number;
  ratio_aicte_sla: number;
  overdue_count: number;
  overdue_rate: number;
  share_of_total_delay: number;
  reason: string;
  low_sample: boolean;
}

interface GridCell {
  avg_days: number;
  sla_days: number;
  ratio: number;
  count: number;
}

interface GridRow {
  region_id: number;
  region_name: string;
  stages: Record<string, GridCell>;
}

interface OfficerBottleneck {
  officer_id: number;
  officer_name: string;
  open_cases: number;
  avg_aicte_days: number;
  overdue_count: number;
  low_sample: boolean;
}

interface BottleneckResponse {
  bottlenecks: BottleneckItem[];
  stage_region_grid: GridRow[];
  officer_bottlenecks: OfficerBottleneck[];
  total_open: number;
  total_overdue: number;
  total_delay_days: number;
  analysis_note: string;
  disclaimer: string;
}

interface RegionItem {
  id: number;
  name: string;
  code: string;
}

export default function BottlenecksPage() {
  const { scope } = useAuth();
  const [data, setData] = useState<BottleneckResponse | null>(null);
  const [regions, setRegions] = useState<RegionItem[]>([]);
  const [selectedRegion, setSelectedRegion] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBottlenecks = async (regionId?: string) => {
    try {
      setLoading(true);
      setError(null);
      const query = regionId ? `?region_id=${regionId}` : '';
      const res = await apiClient.get<BottleneckResponse>(`/bottlenecks${query}`);
      setData(res.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load bottleneck analysis.');
    } finally {
      setLoading(false);
    }
  };

  const fetchRegions = async () => {
    try {
      const res = await apiClient.get<RegionItem[]>('/regions');
      setRegions(res.data);
    } catch (e) {
      // Ignore region load error
    }
  };

  useEffect(() => {
    fetchRegions();
    fetchBottlenecks();
  }, []);

  const handleRegionChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    setSelectedRegion(val);
    fetchBottlenecks(val || undefined);
  };

  // Collect all unique stage codes across grid rows
  const stageCodes = Array.from(
    new Set(data?.stage_region_grid.flatMap((row) => Object.keys(row.stages)) || [])
  );

  return (
    <div className="space-y-6">
      {/* Header with Title and Reusable Decision Support Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Regulatory Bottleneck Finder
            </h1>
            <DecisionSupportBadge size="sm" />
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Stage, regional jurisdiction, and officer queue delay concentration analysis. Time with institution is reported separately.
          </p>
        </div>

        {/* Filter & Refresh */}
        <div className="flex items-center gap-2">
          {(!scope?.is_regional || scope?.role === 'ADMIN' || scope?.role === 'BUREAU_OFFICER') && (
            <div className="flex items-center gap-1.5 bg-white border border-slate-300 rounded-md px-2.5 py-1.5 text-xs shadow-xs">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <select
                aria-label="Filter by Regional Jurisdiction"
                value={selectedRegion}
                onChange={handleRegionChange}
                className="bg-transparent text-slate-700 font-medium focus:outline-hidden"
              >
                <option value="">All Regions</option>
                {regions.map((r) => (
                  <option key={r.id} value={r.id.toString()}>
                    {r.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={() => fetchBottlenecks(selectedRegion || undefined)}
            className="flex items-center gap-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 px-3 py-1.5 rounded-md text-xs font-medium shadow-xs transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
          {error}
        </div>
      )}

      {/* Summary KPI Strip */}
      {data && (
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <Card className="p-4 border-slate-200">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">Active Open Cases</span>
              <Layers className="w-4 h-4 text-blue-600" />
            </div>
            <div className="mt-2 text-2xl font-bold text-slate-900">{data.total_open}</div>
            <div className="text-[11px] text-slate-500 mt-1">Currently in regulatory workflow</div>
          </Card>

          <Card className="p-4 border-slate-200">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">Overdue SLA Cases</span>
              <AlertTriangle className="w-4 h-4 text-amber-600" />
            </div>
            <div className="mt-2 text-2xl font-bold text-amber-900">{data.total_overdue}</div>
            <div className="text-[11px] text-slate-500 mt-1">Exceeded statutory stage SLA limit</div>
          </Card>

          <Card className="p-4 border-slate-200">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">Total Delay Accumulation</span>
              <Clock className="w-4 h-4 text-red-600" />
            </div>
            <div className="mt-2 text-2xl font-bold text-red-900">{data.total_delay_days} days</div>
            <div className="text-[11px] text-slate-500 mt-1">Excludes WITH_INSTITUTION paused time</div>
          </Card>

          <Card className="p-4 border-slate-200">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">Fairness Guarantee</span>
              <Building className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="mt-2 text-sm font-semibold text-emerald-900">Separate Clocks</div>
            <div className="text-[11px] text-slate-500 mt-1">Institution response time audited separately</div>
          </Card>
        </div>
      )}

      {/* Ranked Bottlenecks Section */}
      <Card className="p-5 border-slate-200">
        <div className="flex items-center justify-between pb-3 border-b border-slate-200">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Top Delay Concentrations</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Ranked by share of total regulatory delay and overdue rate. Groups with fewer than 3 cases are flagged as low sample.
            </p>
          </div>
          <Badge variant="outline" className="text-xs font-normal text-slate-600">
            Synthetic skew present for demonstration
          </Badge>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70 text-slate-600 font-semibold">
                <th className="py-2.5 px-3">Stage / Department</th>
                <th className="py-2.5 px-3">Region</th>
                <th className="py-2.5 px-3 text-right">Open Cases</th>
                <th className="py-2.5 px-3 text-right">Avg AICTE Days</th>
                <th className="py-2.5 px-3 text-right">SLA Limit</th>
                <th className="py-2.5 px-3 text-right">Ratio (Days/SLA)</th>
                <th className="py-2.5 px-3 text-right">Overdue Rate</th>
                <th className="py-2.5 px-3 text-right">Share of Delay</th>
                <th className="py-2.5 px-3">Primary Diagnosis</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.bottlenecks && data.bottlenecks.length > 0 ? (
                data.bottlenecks.map((item, idx) => (
                  <tr key={`${item.stage_code}_${item.region_id}`} className="hover:bg-slate-50/50">
                    <td className="py-3 px-3 font-medium text-slate-900">
                      {item.stage_name}
                      {item.low_sample && (
                        <span className="ml-2 inline-flex items-center px-1.5 py-0.2 text-[10px] rounded bg-slate-100 text-slate-600 border border-slate-200">
                          Low sample
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3 text-slate-600">{item.region_name}</td>
                    <td className="py-3 px-3 text-right font-medium text-slate-900">{item.open_cases}</td>
                    <td className="py-3 px-3 text-right text-slate-700">
                      <span className="font-semibold text-slate-900">{item.avg_aicte_days}</span> d
                      <span className="text-[10px] text-slate-400 block">
                        inst: {item.avg_institution_days}d
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right text-slate-500">{item.sla_days} d</td>
                    <td className="py-3 px-3 text-right font-semibold">
                      <span
                        className={`inline-block px-1.5 py-0.5 rounded text-[11px] ${
                          item.ratio_aicte_sla > 1.2
                            ? 'bg-red-50 text-red-800 border border-red-200'
                            : item.ratio_aicte_sla > 0.9
                            ? 'bg-amber-50 text-amber-800 border border-amber-200'
                            : 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                        }`}
                      >
                        {item.ratio_aicte_sla}x
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right text-slate-700 font-medium">
                      {item.overdue_rate}%
                      <span className="text-[10px] text-slate-400 block">
                        ({item.overdue_count} of {item.open_cases})
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right font-semibold text-slate-900">
                      {item.share_of_total_delay}%
                    </td>
                    <td className="py-3 px-3 text-slate-600 max-w-xs leading-relaxed text-[11px]">
                      {item.reason}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-slate-400">
                    No bottleneck data available.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Region-by-Stage Heat Grid */}
      {data?.stage_region_grid && data.stage_region_grid.length > 0 && (
        <Card className="p-5 border-slate-200">
          <div className="pb-3 border-b border-slate-200">
            <h2 className="text-base font-semibold text-slate-900">
              Regional Jurisdiction vs Stage Dwell Matrix
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Heat ratio computed as (Average AICTE-Held Working Days / Statutory Stage SLA). Values above 1.0 indicate statutory delay.
            </p>
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-slate-600">
                  <th className="py-2.5 px-3 text-left font-semibold">Region</th>
                  {stageCodes.map((code) => (
                    <th key={code} className="py-2.5 px-3 text-center font-semibold">
                      {code}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.stage_region_grid.map((row) => (
                  <tr key={row.region_id} className="hover:bg-slate-50/50">
                    <td className="py-2.5 px-3 font-medium text-slate-900">{row.region_name}</td>
                    {stageCodes.map((code) => {
                      const cell = row.stages[code];
                      if (!cell) {
                        return (
                          <td key={code} className="py-2.5 px-3 text-center text-slate-300">
                            -
                          </td>
                        );
                      }
                      const ratio = cell.ratio;
                      let bgClass = 'bg-slate-50 text-slate-600';
                      if (ratio >= 1.5) bgClass = 'bg-red-100 text-red-900 font-bold border border-red-300';
                      else if (ratio >= 1.0) bgClass = 'bg-red-50 text-red-800 font-medium border border-red-200';
                      else if (ratio >= 0.75) bgClass = 'bg-amber-50 text-amber-800 border border-amber-200';
                      else bgClass = 'bg-emerald-50 text-emerald-800 border border-emerald-200';

                      return (
                        <td key={code} className="py-2.5 px-3 text-center">
                          <div className={`inline-block px-2 py-1 rounded text-xs ${bgClass}`}>
                            <div className="text-[11px] font-semibold">{cell.ratio}x</div>
                            <div className="text-[10px] opacity-75">
                              {cell.avg_days}d ({cell.count})
                            </div>
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Officer Workload Queue Distribution */}
      {data?.officer_bottlenecks && data.officer_bottlenecks.length > 0 && (
        <Card className="p-5 border-slate-200">
          <div className="pb-3 border-b border-slate-200">
            <h2 className="text-base font-semibold text-slate-900">Officer Workload & Queue Delay</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Assigned open case volume and average pendency per reviewing officer.
            </p>
          </div>

          <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {data.officer_bottlenecks.map((officer) => (
              <div
                key={officer.officer_id}
                className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-900">{officer.officer_name}</span>
                    {officer.low_sample && (
                      <span className="text-[10px] text-slate-400 border border-slate-200 rounded px-1">
                        Low sample
                      </span>
                    )}
                  </div>
                  <div className="mt-2 flex items-center justify-between text-slate-600">
                    <span>Open applications:</span>
                    <span className="font-semibold text-slate-900">{officer.open_cases}</span>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-slate-600">
                    <span>Average AICTE dwell:</span>
                    <span className="font-semibold text-slate-900">{officer.avg_aicte_days} days</span>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-slate-600">
                    <span>Overdue cases:</span>
                    <span className={`font-semibold ${officer.overdue_count > 0 ? 'text-red-700' : 'text-slate-900'}`}>
                      {officer.overdue_count}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Footer Disclaimer */}
      <div className="p-3 bg-slate-100 rounded-lg text-[11px] text-slate-600 flex items-start gap-2 border border-slate-200">
        <ShieldAlert className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-slate-800">Decision Support Only: </span>
          Synthetic queue skews were seeded in this demonstration to highlight EVC queue and officer workload concentration. Time WITH_INSTITUTION is audited separately and never penalized against AICTE officers. Statutory scrutiny, inspections, and final decisions stay strictly with authorized human officials.
        </div>
      </div>
    </div>
  );
}
