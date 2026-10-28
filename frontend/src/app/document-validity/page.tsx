'use client';

import React from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ShieldCheck, Clock } from 'lucide-react';

export default function DocumentValidityPage() {
  return (
    <AppShell>
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Lease & Document Validity Monitor</h2>
          <p className="text-xs text-slate-500">Statutory watchtower tracking land leases, building plans, and fire NOCs.</p>
        </div>

        <Card className="border-dashed border-slate-300">
          <CardHeader>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-600" />
              <CardTitle>Phase 5 Implementation: Validity Watchtower</CardTitle>
            </div>
            <Badge variant="warning">Scheduled for Phase 5</Badge>
          </CardHeader>
          <CardContent className="py-8 text-center">
            <Clock className="w-8 h-8 text-slate-400 mx-auto mb-3" />
            <p className="text-sm font-medium text-slate-700">Expiry Tracking & Advance Warning Ledger</p>
            <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
              Monitors 90/60/30/7-day advance expiry warnings, expired document blocking, and renewal certificate verification workflows.
            </p>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
