'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { lookupApi, configApi, alertsApi, Institution, Region, StagePath, AlertSummary } from '@/lib/api';
import {
  ShieldAlert,
  Clock,
  Calendar,
  Layers,
  FileCheck2,
  Building,
  CheckCircle2,
  AlertTriangle,
  ArrowRight
} from 'lucide-react';

export default function HomePage() {
  const { scope } = useAuth();
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [stagePaths, setStagePaths] = useState<StagePath[]>([]);
  const [regions, setRegions] = useState<Region[]>([]);
  const [alertSummary, setAlertSummary] = useState<AlertSummary | null>(null);
  const [loadingData, setLoadingData] = useState(true);

  useEffect(() => {
    async function loadFoundationData() {
      try {
        setLoadingData(true);
        const [instRes, pathsRes, regRes, alertSummaryRes] = await Promise.all([
          lookupApi.getInstitutions(),
          configApi.getStagePaths(),
          lookupApi.getRegions(),
          alertsApi.getSummary().catch(() => null),
        ]);
        setInstitutions(instRes);
        setStagePaths(pathsRes);
        setRegions(regRes);
        setAlertSummary(alertSummaryRes);
      } catch (err) {
        console.error('Error fetching foundation data', err);
      } finally {
        setLoadingData(false);
      }
    }

    if (scope) {
      loadFoundationData();
    }
  }, [scope]);

  if (!scope) return null;

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Welcome Banner */}
        <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs uppercase font-semibold tracking-wider text-slate-500">
                Workspace Overview
              </span>
              <span className="text-slate-300">•</span>
              <Badge variant="info" size="sm">{scope.role}</Badge>
            </div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">
              Welcome back, {scope.full_name}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              {scope.region_name ? `Assigned Region: ${scope.region_name}` : 'National Directorate Headquarters (Central)'}
              {scope.institution_name ? ` | Institution: ${scope.institution_name}` : ''}
            </p>
          </div>

          <div className="flex items-center gap-3 self-start md:self-auto">
            <div className="text-right hidden sm:block">
              <div className="text-xs font-semibold text-slate-800">Academic Year 2026-27</div>
              <div className="text-[11px] text-slate-500">Cycle Status: Active Scrutiny</div>
            </div>
          </div>
        </div>

        {/* Operational Placeholder KPI Cards (Phase 2 Foundation) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <div className="text-xs font-medium text-slate-500">Active Applications</div>
                <div className="text-2xl font-bold text-slate-800 mt-1">
                  {loadingData ? '-' : institutions.length}
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">Visible within your RBAC scope</div>
              </div>
              <div className="p-2.5 rounded-lg bg-blue-50 text-blue-700">
                <FileCheck2 className="w-5 h-5" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <div className="text-xs font-medium text-slate-500">Configured APH Paths</div>
                <div className="text-2xl font-bold text-slate-800 mt-1">
                  {loadingData ? '-' : stagePaths.length}
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">Statutory approval routes</div>
              </div>
              <div className="p-2.5 rounded-lg bg-indigo-50 text-indigo-700">
                <Layers className="w-5 h-5" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <div className="text-xs font-medium text-slate-500">Regional Jurisdictions</div>
                <div className="text-2xl font-bold text-slate-800 mt-1">
                  {loadingData ? '-' : regions.length}
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">AICTE Regional Offices</div>
              </div>
              <div className="p-2.5 rounded-lg bg-emerald-50 text-emerald-700">
                <Building className="w-5 h-5" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <div className="text-xs font-medium text-slate-500">Open Compliance Alerts</div>
                <div className="text-2xl font-bold text-slate-800 mt-1">
                  {loadingData || !alertSummary ? '—' : alertSummary.total_open}
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  {alertSummary ? (
                    <span className="flex items-center gap-1">
                      <span className="text-red-600 font-semibold">{alertSummary.by_severity['CRITICAL'] || 0} Crit</span>
                      <span>•</span>
                      <span className="text-amber-600 font-semibold">{alertSummary.by_severity['HIGH'] || 0} High</span>
                      <span>•</span>
                      <span className="text-blue-600 font-semibold">{alertSummary.by_severity['MEDIUM'] || 0} Med</span>
                    </span>
                  ) : (
                    '3-tier escalation ladder active'
                  )}
                </div>
              </div>
              <a
                href="/alerts"
                className="p-2.5 rounded-lg bg-amber-50 text-amber-700 hover:bg-amber-100 transition-colors"
                title="View All Alerts"
              >
                <AlertTriangle className="w-5 h-5" />
              </a>
            </CardContent>
          </Card>
        </div>

        {/* Scoped Institutions Table */}
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Registered Institutions in Scope</CardTitle>
              <CardDescription>
                {scope.is_institution
                  ? 'Showing your verified institutional profile'
                  : scope.is_regional
                  ? `Showing institutions allocated under ${scope.region_name}`
                  : 'Showing all institutions across regional directorates'}
              </CardDescription>
            </div>
            <Badge variant="neutral">{institutions.length} Recorded</Badge>
          </CardHeader>

          <CardContent className="p-0">
            {loadingData ? (
              <div className="p-8 text-center text-xs text-slate-500">Loading directory...</div>
            ) : institutions.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">No institutions found within scope.</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>AICTE Permanent ID</TableHead>
                    <TableHead>Institution Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead>Contact Email</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {institutions.map((inst) => (
                    <TableRow key={inst.id}>
                      <TableCell className="font-mono text-xs font-semibold text-blue-900">
                        {inst.aicte_id}
                      </TableCell>
                      <TableCell className="font-medium text-slate-900">
                        {inst.name}
                      </TableCell>
                      <TableCell className="text-xs text-slate-600">
                        {inst.institution_type}
                      </TableCell>
                      <TableCell>
                        <Badge variant="neutral" size="sm">{inst.category}</Badge>
                      </TableCell>
                      <TableCell className="text-xs text-slate-600">
                        {inst.city}, {inst.state}
                      </TableCell>
                      <TableCell className="text-xs font-mono text-slate-500">
                        {inst.primary_email}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Configured Approval Pathways */}
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Configured APH Statutory Pathways</CardTitle>
              <CardDescription>Official routing pathways stored in database configuration</CardDescription>
            </div>
            <Badge variant="success">APH 2026-27 Compliant</Badge>
          </CardHeader>

          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Path Code</TableHead>
                  <TableHead>Path Name</TableHead>
                  <TableHead>Stage Sequence</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {stagePaths.map((path) => (
                  <TableRow key={path.id}>
                    <TableCell className="font-mono text-xs font-semibold text-slate-700">
                      {path.code}
                    </TableCell>
                    <TableCell className="font-medium text-slate-900">
                      {path.name}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {path.stage_sequence.map((stg, idx) => (
                          <span key={stg} className="inline-flex items-center text-[10px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded border border-slate-200">
                            {idx + 1}. {stg}
                          </span>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="success" size="sm">Active</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
