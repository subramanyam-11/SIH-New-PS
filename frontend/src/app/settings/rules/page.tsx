'use client';

import React, { useEffect, useState } from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { useAuth } from '@/lib/auth';
import {
  configApi,
  adminApi,
  AlertRule,
  EscalationRuleItem,
  Stage
} from '@/lib/api';
import {
  Sliders,
  ShieldAlert,
  Clock,
  Network,
  Edit2,
  Check,
  X,
  AlertTriangle,
  RotateCcw
} from 'lucide-react';

export default function RulesSettingsPage() {
  const { scope } = useAuth();
  const [activeTab, setActiveTab] = useState<'STAGES' | 'ALERT_RULES' | 'ESCALATION_RULES'>('ALERT_RULES');

  const [stages, setStages] = useState<Stage[]>([]);
  const [alertRules, setAlertRules] = useState<AlertRule[]>([]);
  const [escalationRules, setEscalationRules] = useState<EscalationRuleItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Edit Alert Rule Modal
  const [editingAlertRule, setEditingAlertRule] = useState<AlertRule | null>(null);
  const [alertSeverity, setAlertSeverity] = useState<string>('HIGH');
  const [alertIsActive, setAlertIsActive] = useState<boolean>(true);
  const [alertTemplate, setAlertTemplate] = useState<string>('');
  const [alertAph, setAlertAph] = useState<string>('');
  const [savingAlertRule, setSavingAlertRule] = useState<boolean>(false);
  const [alertRuleSuccess, setAlertRuleSuccess] = useState<string | null>(null);

  // Edit Escalation Rule Modal
  const [editingEscRule, setEditingEscRule] = useState<EscalationRuleItem | null>(null);
  const [escDelayDays, setEscDelayDays] = useState<number>(2);
  const [escAction, setEscAction] = useState<string>('');
  const [savingEscRule, setSavingEscRule] = useState<boolean>(false);
  const [escRuleSuccess, setEscRuleSuccess] = useState<string | null>(null);

  const isAdmin = scope?.role === 'ADMIN';

  const loadData = async () => {
    try {
      setLoading(true);
      const [stgRes, alertRulesRes, escRulesRes] = await Promise.all([
        configApi.getStages(),
        adminApi.getAlertRules(),
        adminApi.getEscalationRules(),
      ]);
      setStages(stgRes);
      setAlertRules(alertRulesRes);
      setEscalationRules(escRulesRes);
    } catch (err) {
      console.error('Failed to load rules', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const openEditAlertRule = (rule: AlertRule) => {
    setEditingAlertRule(rule);
    setAlertSeverity(rule.severity);
    setAlertIsActive(rule.is_active);
    setAlertTemplate(rule.template_message);
    setAlertAph(rule.aph_reference_clause || '');
    setAlertRuleSuccess(null);
  };

  const handleSaveAlertRule = async () => {
    if (!editingAlertRule) return;
    setSavingAlertRule(true);
    try {
      await adminApi.updateAlertRule(editingAlertRule.id, {
        severity: alertSeverity,
        is_active: alertIsActive,
        template_message: alertTemplate,
        aph_reference_clause: alertAph,
      });
      setAlertRuleSuccess(`Updated ${editingAlertRule.code} successfully. Audit log recorded.`);
      setTimeout(() => {
        setAlertRuleSuccess(null);
        setEditingAlertRule(null);
      }, 1500);
      loadData();
    } catch (err) {
      console.error(err);
    } finally {
      setSavingAlertRule(false);
    }
  };

  const openEditEscRule = (rule: EscalationRuleItem) => {
    setEditingEscRule(rule);
    setEscDelayDays(rule.trigger_delay_days);
    setEscAction(rule.action_required);
    setEscRuleSuccess(null);
  };

  const handleSaveEscRule = async () => {
    if (!editingEscRule) return;
    setSavingEscRule(true);
    try {
      await adminApi.updateEscalationRule(editingEscRule.id, {
        trigger_delay_days: escDelayDays,
        action_required: escAction,
      });
      setEscRuleSuccess(`Updated Tier ${editingEscRule.tier_level} escalation rule successfully.`);
      setTimeout(() => {
        setEscRuleSuccess(null);
        setEditingEscRule(null);
      }, 1500);
      loadData();
    } catch (err) {
      console.error(err);
    } finally {
      setSavingEscRule(false);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">APH Rules & Escalation Configuration</h2>
          <p className="text-xs text-slate-500">
            Database-backed thresholds, escalation delays, and SLA rules. Thresholds come from the database, never from hard-coded values.
          </p>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
          <button
            onClick={() => setActiveTab('ALERT_RULES')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
              activeTab === 'ALERT_RULES'
                ? 'bg-blue-900 text-white'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Statutory Alert Rules (8 Seeded)
          </button>
          <button
            onClick={() => setActiveTab('ESCALATION_RULES')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
              activeTab === 'ESCALATION_RULES'
                ? 'bg-blue-900 text-white'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            3-Tier Escalation Delays
          </button>
          <button
            onClick={() => setActiveTab('STAGES')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
              activeTab === 'STAGES'
                ? 'bg-blue-900 text-white'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Stage SLAs
          </button>
        </div>

        {/* TAB 1: ALERT RULES */}
        {activeTab === 'ALERT_RULES' && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-amber-600" />
                <div>
                  <CardTitle>Statutory Alert Engine Rules</CardTitle>
                  <CardDescription>
                    Deterministic evaluation logic for SLA breaches, overdue EVCs, expiring documents, and undertakings.
                  </CardDescription>
                </div>
              </div>
              <Badge variant="neutral">8 Active Rules</Badge>
            </CardHeader>
            <CardContent className="p-0">
              {loading ? (
                <div className="p-6 text-center text-xs text-slate-500">Loading rules...</div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Rule Code</TableHead>
                      <TableHead>Rule Name</TableHead>
                      <TableHead>Entity</TableHead>
                      <TableHead>Severity</TableHead>
                      <TableHead>APH Clause Reference</TableHead>
                      <TableHead>Status</TableHead>
                      {isAdmin && <TableHead className="text-right">Action</TableHead>}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {alertRules.map((rule) => (
                      <TableRow key={rule.id}>
                        <TableCell className="font-mono text-xs font-semibold text-slate-800">
                          {rule.code}
                        </TableCell>
                        <TableCell className="font-medium text-slate-900 text-xs">
                          {rule.name}
                        </TableCell>
                        <TableCell className="text-xs text-slate-500 font-mono">
                          {rule.entity_type}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              rule.severity === 'CRITICAL'
                                ? 'danger'
                                : rule.severity === 'HIGH'
                                ? 'warning'
                                : 'info'
                            }
                            size="sm"
                          >
                            {rule.severity}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs text-slate-600 font-mono">
                          {rule.aph_reference_clause || 'APH 2026 Manual'}{' '}
                          <span className="text-[10px] text-amber-700">(sample reference)</span>
                        </TableCell>
                        <TableCell>
                          <Badge variant={rule.is_active ? 'success' : 'neutral'} size="sm">
                            {rule.is_active ? 'Active' : 'Disabled'}
                          </Badge>
                        </TableCell>
                        {isAdmin && (
                          <TableCell className="text-right">
                            <button
                              onClick={() => openEditAlertRule(rule)}
                              className="text-xs text-blue-600 hover:text-blue-800 font-medium inline-flex items-center gap-1"
                            >
                              <Edit2 className="w-3 h-3" />
                              <span>Configure</span>
                            </button>
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        )}

        {/* TAB 2: ESCALATION RULES */}
        {activeTab === 'ESCALATION_RULES' && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div className="flex items-center gap-2">
                <Network className="w-5 h-5 text-purple-700" />
                <div>
                  <CardTitle>Escalation Delay Hierarchy</CardTitle>
                  <CardDescription>
                    Trigger days to escalate unresolved alerts from L1 Scrutiny Officer → L2 Regional Head → L3 Competent Authority.
                  </CardDescription>
                </div>
              </div>
              <Badge variant="neutral">Database Backed</Badge>
            </CardHeader>
            <CardContent className="p-0">
              {loading ? (
                <div className="p-6 text-center text-xs text-slate-500">Loading escalation delays...</div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Alert Rule</TableHead>
                      <TableHead>Escalation Tier</TableHead>
                      <TableHead>Target Authority</TableHead>
                      <TableHead>Trigger Delay (Days Open)</TableHead>
                      <TableHead>Action Notice</TableHead>
                      {isAdmin && <TableHead className="text-right">Action</TableHead>}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {escalationRules.map((rule) => (
                      <TableRow key={rule.id}>
                        <TableCell className="font-mono text-xs font-semibold text-slate-800">
                          {rule.rule_code || `Rule #${rule.alert_rule_id}`}
                        </TableCell>
                        <TableCell>
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${
                            rule.tier_level === 1
                              ? 'bg-slate-100 text-slate-700 border-slate-300'
                              : rule.tier_level === 2
                              ? 'bg-amber-100 text-amber-800 border-amber-300'
                              : 'bg-purple-100 text-purple-800 border-purple-300'
                          }`}>
                            Tier {rule.tier_level}
                          </span>
                        </TableCell>
                        <TableCell className="font-semibold text-slate-800 text-xs">
                          {rule.target_role === 'COMPETENT_AUTHORITY'
                            ? 'Member Secretary / Competent Authority'
                            : rule.target_role}
                        </TableCell>
                        <TableCell className="text-xs font-bold text-blue-900">
                          {rule.trigger_delay_days === 0 ? 'Immediate (0d)' : `${rule.trigger_delay_days} Calendar Days`}
                        </TableCell>
                        <TableCell className="text-xs text-slate-600">
                          {rule.action_required}
                        </TableCell>
                        {isAdmin && (
                          <TableCell className="text-right">
                            <button
                              onClick={() => openEditEscRule(rule)}
                              className="text-xs text-blue-600 hover:text-blue-800 font-medium inline-flex items-center gap-1"
                            >
                              <Edit2 className="w-3 h-3" />
                              <span>Edit</span>
                            </button>
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        )}

        {/* TAB 3: STAGES */}
        {activeTab === 'STAGES' && (
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Clock className="w-5 h-5 text-blue-700" />
                <div>
                  <CardTitle>Configured Stage Timelines (SLAs)</CardTitle>
                  <CardDescription>Default statutory calendar day limits by approval stage</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
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
                      <TableCell className="font-medium text-slate-900 text-xs">
                        {stg.name}
                      </TableCell>
                      <TableCell>
                        <span className="font-semibold text-blue-900 text-xs">{stg.default_sla_days} Days</span>
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
            </CardContent>
          </Card>
        )}

        {/* MODAL: Configure Alert Rule */}
        {editingAlertRule && (
          <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
            <Card className="w-full max-w-lg p-6 space-y-4">
              <div className="flex items-center justify-between border-b pb-2">
                <h3 className="text-base font-bold text-slate-900">
                  Configure Alert Rule: {editingAlertRule.code}
                </h3>
                <button onClick={() => setEditingAlertRule(null)} className="text-slate-400 hover:text-slate-700">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {alertRuleSuccess && (
                <div className="text-xs text-emerald-700 bg-emerald-50 p-2.5 rounded border border-emerald-200">
                  {alertRuleSuccess}
                </div>
              )}

              <div className="space-y-3 text-xs">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Severity Level</label>
                  <select
                    value={alertSeverity}
                    onChange={(e) => setAlertSeverity(e.target.value)}
                    className="w-full p-2 rounded border border-slate-300 bg-white"
                  >
                    <option value="CRITICAL">CRITICAL</option>
                    <option value="HIGH">HIGH</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="INFO">INFO</option>
                  </select>
                </div>

                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Rule Activation Status</label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={alertIsActive}
                      onChange={(e) => setAlertIsActive(e.target.checked)}
                      className="rounded text-blue-600"
                    />
                    <span>Active and evaluated on every scheduler run</span>
                  </label>
                </div>

                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Template Notification Message</label>
                  <textarea
                    value={alertTemplate}
                    onChange={(e) => setAlertTemplate(e.target.value)}
                    rows={2}
                    className="w-full p-2 rounded border border-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="font-semibold text-slate-700 block mb-1">APH Reference Clause</label>
                  <input
                    type="text"
                    value={alertAph}
                    onChange={(e) => setAlertAph(e.target.value)}
                    className="w-full p-2 rounded border border-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <span className="text-[10px] text-slate-400 block mt-0.5">
                    Will display with &quot;(sample reference)&quot; badge unless marked verified in system config.
                  </span>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t">
                <Button variant="ghost" size="sm" onClick={() => setEditingAlertRule(null)}>
                  Cancel
                </Button>
                <Button size="sm" onClick={handleSaveAlertRule} disabled={savingAlertRule}>
                  {savingAlertRule ? 'Saving...' : 'Save Configuration'}
                </Button>
              </div>
            </Card>
          </div>
        )}

        {/* MODAL: Configure Escalation Rule */}
        {editingEscRule && (
          <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
            <Card className="w-full max-w-lg p-6 space-y-4">
              <div className="flex items-center justify-between border-b pb-2">
                <h3 className="text-base font-bold text-slate-900">
                  Configure Tier {editingEscRule.tier_level} Escalation Delay
                </h3>
                <button onClick={() => setEditingEscRule(null)} className="text-slate-400 hover:text-slate-700">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {escRuleSuccess && (
                <div className="text-xs text-emerald-700 bg-emerald-50 p-2.5 rounded border border-emerald-200">
                  {escRuleSuccess}
                </div>
              )}

              <div className="space-y-3 text-xs">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Target Officer Role</label>
                  <div className="p-2 bg-slate-100 rounded text-slate-800 font-semibold">
                    {editingEscRule.target_role}
                  </div>
                </div>

                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Trigger Delay (Calendar Days)</label>
                  <input
                    type="number"
                    min={0}
                    max={30}
                    value={escDelayDays}
                    onChange={(e) => setEscDelayDays(Number(e.target.value))}
                    className="w-full p-2 rounded border border-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <span className="text-[10px] text-slate-400 block mt-0.5">
                    Days after alert creation without resolution before escalating to this tier.
                  </span>
                </div>

                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Statutory Action Notice Wording</label>
                  <textarea
                    value={escAction}
                    onChange={(e) => setEscAction(e.target.value)}
                    rows={2}
                    className="w-full p-2 rounded border border-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t">
                <Button variant="ghost" size="sm" onClick={() => setEditingEscRule(null)}>
                  Cancel
                </Button>
                <Button size="sm" onClick={handleSaveEscRule} disabled={savingEscRule}>
                  {savingEscRule ? 'Saving...' : 'Save Escalation Delay'}
                </Button>
              </div>
            </Card>
          </div>
        )}
      </div>
    </AppShell>
  );
}
