'use client';

import React from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { BarChart3, Clock } from 'lucide-react';

export default function ReportsPage() {
  return (
    <AppShell>
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Reports & Regional Performance Analytics</h2>
          <p className="text-xs text-slate-500">Cross-regional aging distribution, bottleneck detection, and executive exports.</p>
        </div>

        <Card className="border-dashed border-slate-300">
          <CardHeader>
            <div className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-purple-600" />
              <CardTitle>Phase 5 Implementation: Executive Reporting Suite</CardTitle>
            </div>
            <Badge variant="warning">Scheduled for Phase 5</Badge>
          </CardHeader>
          <CardContent className="py-8 text-center">
            <Clock className="w-8 h-8 text-slate-400 mx-auto mb-3" />
            <p className="text-sm font-medium text-slate-700">Analytics & Audit Report Generator</p>
            <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
              Visualizes cycle times across regions, stage dwell times, officer workload distribution, and regulatory audit trail exports.
            </p>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
