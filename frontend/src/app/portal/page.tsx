'use client';

import React from 'react';
import { useAuth } from '@/lib/auth';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Building, FileText, Clock, ShieldAlert } from 'lucide-react';

export default function InstitutionPortalPage() {
  const { scope } = useAuth();

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Institutional Welcome Card */}
        <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs uppercase font-semibold tracking-wider text-slate-500">
                Institution Self-Service Portal
              </span>
              <span className="text-slate-300">•</span>
              <Badge variant="neutral" size="sm">Applicant View</Badge>
            </div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">
              {scope?.institution_name || 'Registered Institution Portal'}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Authorized Signatory: {scope?.full_name} | Region: {scope?.region_name || 'Northern RO'}
            </p>
          </div>
        </div>

        {/* Status Tracker Placeholder */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Building className="w-5 h-5 text-blue-700" />
              <div>
                <CardTitle>Application Milestone Tracker</CardTitle>
                <CardDescription>Real-time statutory status for Academic Year 2026-27</CardDescription>
              </div>
            </div>
            <Badge variant="info">Phase 3 Integration</Badge>
          </CardHeader>
          <CardContent className="py-8 text-center border-t border-slate-100">
            <Clock className="w-8 h-8 text-slate-400 mx-auto mb-3" />
            <p className="text-sm font-medium text-slate-700">Self-Service Application & Compliance Hub</p>
            <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
              In Phase 3 to 5, applicant institutions will view their active application stepper, reply directly to deficiency notices with uploaded files, track conditional undertaking deadlines, and upload renewed land leases.
            </p>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
