'use client';

import React, { useEffect, useState } from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { configApi, AlertRule, Stage } from '@/lib/api';
import { Sliders, ShieldAlert, Clock } from 'lucide-react';

export default function RulesSettingsPage() {
  const [stages, setStages] = useState<Stage[]>([]);
  const [alertRules, setAlertRules] = useState<AlertRule[]>([]);
  const [systemConfigs, setSystemConfigs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadRules() {
      try {
        setLoading(true);
        const [stgRes, rulesRes] = await Promise.all([
          configApi.getStages(),
          configApi.getRules()
        ]);
        setStages(stgRes);
        setAlertRules(rulesRes.alert_rules);
        setSystemConfigs(rulesRes.system_configs);
      } catch (err) {
        console.error('Failed to load rules', err);
      } finally {
        setLoading(false);
      }
    }
    loadRules();
  }, []);

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">APH Rules & Configuration Center</h2>
          <p className="text-xs text-slate-500">Live regulatory timelines, SLAs, and explainable alert rules loaded from database.</p>
        </div>

        {/* Stages SLA Configuration Table */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-blue-700" />
              <div>
                <CardTitle>Configured Stage Timelines (SLAs)</CardTitle>
                <CardDescription>Default statutory calendar day limits by approval stage</CardDescription>
              </div>
            </div>
            <Badge variant="neutral">Database Backed</Badge>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 text-center text-xs text-slate-500">Loading stage SLAs...</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Stage Code</TableHead>
                    <TableHead>Stage Name</TableHead>
                    <TableHead>Default SLA (Days)</TableHead>
                    <TableHead>Responsible Role</TableHead>
                    <TableHead>Description</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {stages.map((stg) => (
                    <TableRow key={stg.id}>
                      <TableCell className="font-mono text-xs font-semibold text-slate-700">
                        {stg.code}
                      </TableCell>
                      <TableCell className="font-medium text-slate-900">
                        {stg.name}
                      </TableCell>
                      <TableCell>
                        <span className="font-semibold text-blue-900">{stg.default_sla_days} Days</span>
                      </TableCell>
                      <TableCell>
                        <Badge variant="info" size="sm">{stg.responsible_role}</Badge>
                      </TableCell>
                      <TableCell className="text-xs text-slate-500">
                        {stg.description}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Explainable Alert Rules Table */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-amber-600" />
              <div>
                <CardTitle>Configured Alert & Escalation Rules</CardTitle>
                <CardDescription>Watchdog triggers and statutory APH reference citations</CardDescription>
              </div>
            </div>
            <Badge variant="success">8 Active Rules</Badge>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 text-center text-xs text-slate-500">Loading alert rules...</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Rule Code</TableHead>
                    <TableHead>Rule Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>APH Citation Clause</TableHead>
                    <TableHead>Template Message</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {alertRules.map((rule) => (
                    <TableRow key={rule.id}>
                      <TableCell className="font-mono text-xs font-semibold text-slate-700">
                        {rule.code}
                      </TableCell>
                      <TableCell className="font-medium text-slate-900">
                        {rule.name}
                      </TableCell>
                      <TableCell>
                        <Badge variant="neutral" size="sm">{rule.alert_type}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={rule.severity === 'CRITICAL' ? 'danger' : rule.severity === 'HIGH' ? 'warning' : 'info'}
                          size="sm"
                        >
                          {rule.severity}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs font-medium text-blue-900">
                        {rule.aph_reference_clause || 'General APH 2026'}
                      </TableCell>
                      <TableCell className="text-xs text-slate-500 max-w-xs truncate">
                        {rule.template_message}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
