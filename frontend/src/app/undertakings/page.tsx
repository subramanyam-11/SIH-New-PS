'use client';

import React from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ClipboardList, Clock } from 'lucide-react';

export default function UndertakingsPage() {
  return (
    <AppShell>
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Undertakings & Compliance Ledger</h2>
          <p className="text-xs text-slate-500">Post-approval conditions, deadline monitoring, and evidence verification.</p>
        </div>

        <Card className="border-dashed border-slate-300">
          <CardHeader>
            <div className="flex items-center gap-2">
              <ClipboardList className="w-5 h-5 text-indigo-600" />
              <CardTitle>Phase 5 Implementation: Compliance Tracker</CardTitle>
            </div>
            <Badge variant="warning">Scheduled for Phase 5</Badge>
          </CardHeader>
          <CardContent className="py-8 text-center">
            <Clock className="w-8 h-8 text-slate-400 mx-auto mb-3" />
            <p className="text-sm font-medium text-slate-700">Digital Undertakings Registry</p>
            <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
              Tracks time-bound statutory undertakings, institution evidence uploads, verification signoffs, and escalation of overdue commitments.
            </p>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
