'use client';

import React, { useState, useEffect } from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { alertsApi, EscalationMatrix, RegionEscalationItem } from '@/lib/api';
import { Network, ArrowRight, ShieldCheck, AlertTriangle, ExternalLink } from 'lucide-react';

export default function EscalationMatrixPage() {
  const [matrix, setMatrix] = useState<EscalationMatrix | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchMatrix = async () => {
      setLoading(true);
      try {
        const data = await alertsApi.getEscalationMatrix();
        setMatrix(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchMatrix();
  }, []);

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Network className="w-6 h-6 text-blue-700" />
              <h1 className="text-2xl font-bold text-slate-900">Regional Escalation Hierarchy Matrix</h1>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              Live mapping of regional officers across the 3-tier escalation ladder: L1 (Desk Officer) → L2 (Regional Head) → L3 (Member Secretary / Competent Authority).
            </p>
          </div>
        </div>

        {/* Matrix Grid */}
        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-semibold uppercase tracking-wider text-slate-600">
                  <th className="py-3.5 px-4 w-48">Region</th>
                  <th className="py-3.5 px-4">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-slate-400" />
                      <span>Tier 1: Scrutiny / Desk Officer</span>
                    </div>
                  </th>
                  <th className="py-3.5 px-4">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-amber-500" />
                      <span>Tier 2: Regional Head</span>
                    </div>
                  </th>
                  <th className="py-3.5 px-4">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-purple-600" />
                      <span>Tier 3: Member Secretary / Council</span>
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {loading ? (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-slate-500">
                      Loading escalation hierarchy matrix...
                    </td>
                  </tr>
                ) : !matrix || matrix.regions.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-slate-500">
                      No regional hierarchy mapped.
                    </td>
                  </tr>
                ) : (
                  matrix.regions.map((reg) => (
                    <tr key={reg.region_id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-4 px-4 font-semibold text-slate-900 align-top">
                        <div className="text-sm">{reg.region_name}</div>
                        <div className="text-[11px] text-slate-400 font-mono mt-0.5">Region ID: {reg.region_id}</div>
                      </td>

                      {/* Tier 1 */}
                      <td className="py-4 px-4 align-top">
                        <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1.5">
                          <div className="font-semibold text-slate-800">{reg.l1_officer || 'Assigned Desk Officer'}</div>
                          <div className="text-[11px] text-slate-500 font-medium">Role: {reg.l1_role}</div>
                          <div className="pt-2 border-t border-slate-200 flex items-center justify-between">
                            <span className="text-[11px] text-slate-400">Open Alerts:</span>
                            <a
                              href={`/alerts?tier=1`}
                              className="inline-flex items-center gap-1 text-xs font-bold text-slate-700 bg-white px-2 py-0.5 rounded border border-slate-200 hover:bg-slate-100"
                            >
                              <span>{reg.l1_alerts_count}</span>
                              <ExternalLink className="w-2.5 h-2.5" />
                            </a>
                          </div>
                        </div>
                      </td>

                      {/* Tier 2 */}
                      <td className="py-4 px-4 align-top">
                        <div className="p-3 bg-amber-50/50 rounded-lg border border-amber-200 space-y-1.5">
                          <div className="font-semibold text-amber-950">{reg.l2_officer || 'Regional Head'}</div>
                          <div className="text-[11px] text-amber-700 font-medium">Role: {reg.l2_role}</div>
                          <div className="pt-2 border-t border-amber-200 flex items-center justify-between">
                            <span className="text-[11px] text-amber-600">Escalated Alerts:</span>
                            <a
                              href={`/alerts?tier=2`}
                              className="inline-flex items-center gap-1 text-xs font-bold text-amber-900 bg-white px-2 py-0.5 rounded border border-amber-300 hover:bg-amber-100"
                            >
                              <span>{reg.l2_alerts_count}</span>
                              <ExternalLink className="w-2.5 h-2.5" />
                            </a>
                          </div>
                        </div>
                      </td>

                      {/* Tier 3 */}
                      <td className="py-4 px-4 align-top">
                        <div className="p-3 bg-purple-50/50 rounded-lg border border-purple-200 space-y-1.5">
                          <div className="font-semibold text-purple-950">
                            {reg.l3_officer || 'Member Secretary / Competent Authority'}
                          </div>
                          <div className="text-[11px] text-purple-700 font-medium">Role: {reg.l3_role}</div>
                          <div className="pt-2 border-t border-purple-200 flex items-center justify-between">
                            <span className="text-[11px] text-purple-600">Council Breaches:</span>
                            <a
                              href={`/alerts?tier=3`}
                              className="inline-flex items-center gap-1 text-xs font-bold text-purple-900 bg-white px-2 py-0.5 rounded border border-purple-300 hover:bg-purple-100"
                            >
                              <span>{reg.l3_alerts_count}</span>
                              <ExternalLink className="w-2.5 h-2.5" />
                            </a>
                          </div>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
