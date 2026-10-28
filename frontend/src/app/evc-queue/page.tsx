'use client';

import React from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { CalendarCheck2, Clock } from 'lucide-react';

export default function EvcQueuePage() {
  return (
    <AppShell>
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">EVC Inspection Queue</h2>
          <p className="text-xs text-slate-500">Panel scheduling, date assignment, and inspection report turnaround.</p>
        </div>

        <Card className="border-dashed border-slate-300">
          <CardHeader>
            <div className="flex items-center gap-2">
              <CalendarCheck2 className="w-5 h-5 text-amber-600" />
              <CardTitle>Phase 5 Implementation: EVC Scheduling Workbench</CardTitle>
            </div>
            <Badge variant="warning">Scheduled for Phase 5</Badge>
          </CardHeader>
          <CardContent className="py-8 text-center">
            <Clock className="w-8 h-8 text-slate-400 mx-auto mb-3" />
            <p className="text-sm font-medium text-slate-700">Expert Panel Scheduling Queue</p>
            <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
              Tracks applications needing EVC inspections, panel assignment, date pickers, report uploads, and the Tour Optimization hint.
            </p>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
