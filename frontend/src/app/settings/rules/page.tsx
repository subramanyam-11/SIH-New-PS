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
  holidaysApi,
  riskApi,
  AlertRule,
  EscalationRuleItem,
  Stage,
  HolidayItem,
  RiskWeightsConfig
} from '@/lib/api';
import { DecisionSupportBadge } from '@/components/ui/DecisionSupportBadge';
import {
  Sliders,
  ShieldAlert,
  Clock,
  Network,
  Edit2,
  Check,
  X,
  AlertTriangle,
  RotateCcw,
  Calendar,
  Trash2,
  Plus,
  Scale,
  Sparkles
} from 'lucide-react';

export default function RulesSettingsPage() {
  const { scope } = useAuth();
  const [activeTab, setActiveTab] = useState<'STAGES' | 'ALERT_RULES' | 'ESCALATION_RULES' | 'HOLIDAYS' | 'RISK_WEIGHTS'>('ALERT_RULES');

  const [stages, setStages] = useState<Stage[]>([]);
  const [alertRules, setAlertRules] = useState<AlertRule[]>([]);
  const [escalationRules, setEscalationRules] = useState<EscalationRuleItem[]>([]);
  const [holidays, setHolidays] = useState<HolidayItem[]>([]);
  const [weekendDays, setWeekendDays] = useState<number[]>([5, 6]);
  const [loading, setLoading] = useState<boolean>(true);

  // Risk weights state (Phase 7 Innovation)
  const [riskWeights, setRiskWeights] = useState<Record<string, number>>({
    age_against_time_limit: 40,
    past_returns: 25,
    officer_workload: 20,
    current_stage: 15,
  });
  const [riskThresholds, setRiskThresholds] = useState<Record<string, number>>({ medium: 40, high: 70 });
  const [savingRiskWeights, setSavingRiskWeights] = useState<boolean>(false);
  const [riskWeightsSuccess, setRiskWeightsSuccess] = useState<string | null>(null);
  const [riskWeightsError, setRiskWeightsError] = useState<string | null>(null);

  // Live preview simulator state
  const [previewAgeRatio, setPreviewAgeRatio] = useState<number>(0.8); // 80% SLA
  const [previewReturns, setPreviewReturns] = useState<number>(1); // 1 return
  const [previewWorkload, setPreviewWorkload] = useState<number>(8); // 8 open cases
  const [previewStageRatio, setPreviewStageRatio] = useState<number>(0.8); // 0.8 EVC baseline

  // Holiday form
  const [holidayDate, setHolidayDate] = useState<string>('');
  const [holidayName, setHolidayName] = useState<string>('');
  const [holidayType, setHolidayType] = useState<string>('NATIONAL');
  const [addingHoliday, setAddingHoliday] = useState<boolean>(false);
  const [holidayMessage, setHolidayMessage] = useState<string | null>(null);

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
      const [stgRes, alertRulesRes, escRulesRes, holRes, wkRes, riskWeightsRes] = await Promise.all([
        configApi.getStages(),
        adminApi.getAlertRules(),
        adminApi.getEscalationRules(),
        holidaysApi.getHolidays().catch(() => []),
        holidaysApi.getWeekendConfig().catch(() => ({ weekend_days: [5, 6], weekend_names: ['Saturday', 'Sunday'] })),
        riskApi.getWeights().catch(() => null),
      ]);
      setStages(stgRes);
      setAlertRules(alertRulesRes);
      setEscalationRules(escRulesRes);
      setHolidays(holRes);
      setWeekendDays(wkRes.weekend_days || [5, 6]);
      if (riskWeightsRes?.weights) {
        setRiskWeights(riskWeightsRes.weights);
      }
      if (riskWeightsRes?.thresholds) {
        setRiskThresholds(riskWeightsRes.thresholds);
      }
    } catch (err) {
      console.error('Failed to load rules', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveRiskWeights = async () => {
    const total =
      Number(riskWeights.age_against_time_limit) +
      Number(riskWeights.past_returns) +
      Number(riskWeights.officer_workload) +
      Number(riskWeights.current_stage);

    if (total !== 100) {
      setRiskWeightsError(`Total weights sum to ${total}%. The four factor weights must sum to exactly 100%.`);
      return;
    }

    setSavingRiskWeights(true);
    setRiskWeightsError(null);
    setRiskWeightsSuccess(null);
    try {
      await riskApi.updateWeights({ weights: riskWeights, thresholds: riskThresholds });
      setRiskWeightsSuccess('Risk score weights saved successfully. Audit log record generated.');
      setTimeout(() => setRiskWeightsSuccess(null), 5000);
    } catch (err: any) {
      setRiskWeightsError(err.response?.data?.detail || 'Failed to update risk weights');
    } finally {
      setSavingRiskWeights(false);
    }
  };

  const handleAddHoliday = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!holidayDate || !holidayName.trim()) return;
    setAddingHoliday(true);
    setHolidayMessage(null);
    try {
      await holidaysApi.addHoliday({
        holiday_date: holidayDate,
        name: holidayName.trim(),
        holiday_type: holidayType,
      });
      setHolidayMessage('✓ Holiday added successfully. Audit entry created.');
      setHolidayDate('');
      setHolidayName('');
      const updated = await holidaysApi.getHolidays();
      setHolidays(updated);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to add holiday');
    } finally {
      setAddingHoliday(false);
    }
  };

  const handleDeleteHoliday = async (id: number) => {
    if (!confirm('Are you sure you want to delete this holiday?')) return;
    try {
      await holidaysApi.deleteHoliday(id);
      setHolidays(holidays.filter((h) => h.id !== id));
      setHolidayMessage('✓ Holiday removed. Audit entry created.');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete holiday');
    }
  };

  const handleToggleWeekend = async (day: number) => {
    const updated = weekendDays.includes(day)
      ? weekendDays.filter((d) => d !== day)
      : [...weekendDays, day].sort();
    setWeekendDays(updated);
    try {
      await holidaysApi.updateWeekendConfig(updated);
      setHolidayMessage('✓ Weekend days configuration updated. Audit entry created.');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update weekend configuration');
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
        <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 pb-2">
          <button
            onClick={() => setActiveTab('ALERT_RULES')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
              activeTab === 'ALERT_RULES'
                ? 'bg-blue-900 text-white'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Statutory Alert Rules ({alertRules.length || 12} Active)
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
          <button
            onClick={() => setActiveTab('HOLIDAYS')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5 ${
              activeTab === 'HOLIDAYS'
                ? 'bg-blue-900 text-white'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Calendar className="w-3.5 h-3.5" />
            <span>Working Days & Holidays</span>
          </button>
          <button
            onClick={() => setActiveTab('RISK_WEIGHTS')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5 ${
              activeTab === 'RISK_WEIGHTS'
                ? 'bg-blue-900 text-white'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Sliders className="w-3.5 h-3.5 text-amber-400" />
            <span>Risk Score Weights & Formulas</span>
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

        {/* TAB 4: WORKING DAYS & HOLIDAYS */}
        {activeTab === 'HOLIDAYS' && (
          <div className="space-y-4">
            {/* Regulatory Basis Notice */}
            <Card className="border-blue-200 bg-blue-50/30">
              <CardContent className="p-4 flex items-start gap-3 text-xs leading-relaxed text-blue-950">
                <div className="p-1.5 bg-blue-100 rounded text-blue-800 shrink-0">
                  <Calendar className="w-4 h-4" />
                </div>
                <div>
                  <span className="font-bold">Working-Day SLA Basis (Build Plan v2, Sec. 9): </span>
                  Stage SLAs, EVC scheduling windows, and alert escalation delays count <strong>WORKING DAYS</strong> only. Saturdays, Sundays (or configured weekend days), and listed official holidays pause the countdown. Statutory document expirations (leases, FDRs, NOCs) remain calendar days, with automatic non-working day notes attached whenever a due date falls on a holiday or weekend.
                </div>
              </CardContent>
            </Card>

            {holidayMessage && (
              <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs flex items-center justify-between">
                <span>{holidayMessage}</span>
                <button onClick={() => setHolidayMessage(null)} className="text-emerald-700 font-bold">&times;</button>
              </div>
            )}

            {/* Weekend Configuration */}
            <Card>
              <CardHeader className="py-3 px-4 bg-slate-50 border-b flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-sm">Configurable Non-Working Weekend Days</CardTitle>
                  <CardDescription className="text-xs">Select which weekdays count as statutory non-working days</CardDescription>
                </div>
                <Badge variant="neutral">system_config: weekend_days</Badge>
              </CardHeader>
              <CardContent className="p-4 text-xs">
                <div className="flex flex-wrap gap-4">
                  {[
                    { day: 0, name: 'Monday' },
                    { day: 1, name: 'Tuesday' },
                    { day: 2, name: 'Wednesday' },
                    { day: 3, name: 'Thursday' },
                    { day: 4, name: 'Friday' },
                    { day: 5, name: 'Saturday' },
                    { day: 6, name: 'Sunday' },
                  ].map((d) => (
                    <label key={d.day} className="flex items-center gap-2 cursor-pointer font-medium">
                      <input
                        type="checkbox"
                        checked={weekendDays.includes(d.day)}
                        onChange={() => handleToggleWeekend(d.day)}
                        className="rounded text-blue-800"
                        disabled={!isAdmin}
                      />
                      <span className={weekendDays.includes(d.day) ? 'font-bold text-blue-900' : 'text-slate-600'}>
                        {d.name}
                      </span>
                    </label>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Add Holiday Form (Admin Only) */}
            {isAdmin && (
              <Card>
                <CardHeader className="py-3 px-4 bg-slate-50 border-b">
                  <CardTitle className="text-sm flex items-center gap-1.5">
                    <Plus className="w-4 h-4 text-blue-700" />
                    <span>Add Official Holiday</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4">
                  <form onSubmit={handleAddHoliday} className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs items-end">
                    <div>
                      <label className="font-semibold text-slate-700 block mb-1">Holiday Date</label>
                      <input
                        type="date"
                        value={holidayDate}
                        onChange={(e) => setHolidayDate(e.target.value)}
                        className="w-full p-2 border border-slate-300 rounded bg-white"
                        required
                      />
                    </div>
                    <div>
                      <label className="font-semibold text-slate-700 block mb-1">Holiday Name</label>
                      <input
                        type="text"
                        placeholder="e.g. Republic Day"
                        value={holidayName}
                        onChange={(e) => setHolidayName(e.target.value)}
                        className="w-full p-2 border border-slate-300 rounded bg-white"
                        required
                      />
                    </div>
                    <div>
                      <label className="font-semibold text-slate-700 block mb-1">Holiday Type</label>
                      <select
                        value={holidayType}
                        onChange={(e) => setHolidayType(e.target.value)}
                        className="w-full p-2 border border-slate-300 rounded bg-white"
                      >
                        <option value="NATIONAL">NATIONAL (All Regions)</option>
                        <option value="REGIONAL">REGIONAL (State Specific)</option>
                      </select>
                    </div>
                    <div>
                      <Button type="submit" size="sm" disabled={addingHoliday} className="w-full bg-blue-800 hover:bg-blue-900 text-white">
                        {addingHoliday ? 'Adding...' : 'Add Holiday'}
                      </Button>
                    </div>
                  </form>
                </CardContent>
              </Card>
            )}

            {/* Official Holiday List Table */}
            <Card className="overflow-hidden shadow-sm">
              <CardHeader className="py-3 px-4 bg-slate-50 border-b flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-sm">Official AICTE Statutory Calendar Holidays</CardTitle>
                  <CardDescription className="text-xs">
                    Sample holiday list, to be replaced by the official AICTE calendar ({holidays.length} seeded dates)
                  </CardDescription>
                </div>
                <Badge variant="neutral">Database: holidays</Badge>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Holiday Name</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Region Jurisdiction</TableHead>
                      {isAdmin && <TableHead className="text-right">Action</TableHead>}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {holidays.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} className="py-6 text-center text-slate-400 text-xs">
                          No holidays recorded in calendar table.
                        </TableCell>
                      </TableRow>
                    ) : (
                      holidays.map((h) => (
                        <TableRow key={h.id}>
                          <TableCell className="font-mono text-xs font-semibold text-slate-800">
                            {h.holiday_date}
                          </TableCell>
                          <TableCell className="font-medium text-slate-900 text-xs">
                            {h.name}
                          </TableCell>
                          <TableCell>
                            <Badge variant={h.holiday_type === 'NATIONAL' ? 'info' : 'neutral'} size="sm">
                              {h.holiday_type}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-xs text-slate-600">
                            {h.region_name || 'All India (National)'}
                          </TableCell>
                          {isAdmin && (
                            <TableCell className="text-right">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleDeleteHoliday(h.id)}
                                className="h-7 text-xs text-rose-600 hover:text-rose-800 hover:bg-rose-50"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </Button>
                            </TableCell>
                          )}
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        )}

        {/* TAB 5: RISK WEIGHTS & FORMULAS (Phase 7 Innovation) */}
        {activeTab === 'RISK_WEIGHTS' && (
          <div className="space-y-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <div className="flex items-center gap-2">
                  <Scale className="w-5 h-5 text-indigo-600" />
                  <div>
                    <div className="flex items-center gap-2">
                      <CardTitle>Delay Risk Score Factor Weights & Baseline Formula</CardTitle>
                      <DecisionSupportBadge label="Decision Support Baseline" />
                    </div>
                    <CardDescription className="text-xs text-slate-500 mt-0.5">
                      Configurable 4-factor statutory weights stored in system_config. Transparent, rule-based baseline.
                    </CardDescription>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {Number(riskWeights.age_against_time_limit) +
                    Number(riskWeights.past_returns) +
                    Number(riskWeights.officer_workload) +
                    Number(riskWeights.current_stage) === 100 ? (
                    <Badge variant="success">Total: 100% Balanced</Badge>
                  ) : (
                    <Badge variant="danger">
                      Total: {Number(riskWeights.age_against_time_limit) +
                        Number(riskWeights.past_returns) +
                        Number(riskWeights.officer_workload) +
                        Number(riskWeights.current_stage)}% (Must equal 100%)
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Statutory disclaimer banner */}
                <div className="p-3.5 bg-amber-50/70 border border-amber-200 rounded-lg text-xs text-amber-900 flex items-start gap-2.5">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold">Statutory Notice:</span> Rule-based baseline; can be trained on real AICTE data later.
                    This risk score provides early operational decision support to prevent SLA breaches. It never automatically approves, rejects, moves, reverts, or closes any application.
                  </div>
                </div>

                {riskWeightsSuccess && (
                  <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 font-medium">
                    {riskWeightsSuccess}
                  </div>
                )}
                {riskWeightsError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 font-medium">
                    {riskWeightsError}
                  </div>
                )}

                {/* 4 Factor Configuration Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Factor 1: Age Against SLA Limit */}
                  <div className="p-4 border border-slate-200 rounded-lg bg-slate-50/50 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="font-semibold text-xs text-slate-900">1. Age Against Stage Time Limit</div>
                      <span className="font-mono font-bold text-xs bg-blue-100 text-blue-900 px-2 py-0.5 rounded">
                        {riskWeights.age_against_time_limit} pts
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500">
                      AICTE-held working days in current stage divided by stage SLA, capped at 150%. Paused institution time is strictly excluded.
                    </p>
                    <div className="flex items-center gap-3">
                      <input
                        type="range"
                        min="0"
                        max="80"
                        step="1"
                        value={riskWeights.age_against_time_limit}
                        onChange={(e) =>
                          setRiskWeights({ ...riskWeights, age_against_time_limit: Number(e.target.value) })
                        }
                        disabled={!isAdmin}
                        className="flex-1"
                      />
                      <input
                        type="number"
                        min="0"
                        max="100"
                        value={riskWeights.age_against_time_limit}
                        onChange={(e) =>
                          setRiskWeights({ ...riskWeights, age_against_time_limit: Number(e.target.value) })
                        }
                        disabled={!isAdmin}
                        className="w-16 p-1 text-xs border border-slate-300 rounded font-mono text-center font-bold"
                      />
                    </div>
                  </div>

                  {/* Factor 2: Past Returns */}
                  <div className="p-4 border border-slate-200 rounded-lg bg-slate-50/50 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="font-semibold text-xs text-slate-900">2. Past Returns (Reverts to Institution)</div>
                      <span className="font-mono font-bold text-xs bg-indigo-100 text-indigo-900 px-2 py-0.5 rounded">
                        {riskWeights.past_returns} pts
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500">
                      revert_count divided by configurable revert cap (default 2). Reflects application friction and prior deficiencies.
                    </p>
                    <div className="flex items-center gap-3">
                      <input
                        type="range"
                        min="0"
                        max="80"
                        step="1"
                        value={riskWeights.past_returns}
                        onChange={(e) =>
                          setRiskWeights({ ...riskWeights, past_returns: Number(e.target.value) })
                        }
                        disabled={!isAdmin}
                        className="flex-1"
                      />
                      <input
                        type="number"
                        min="0"
                        max="100"
                        value={riskWeights.past_returns}
                        onChange={(e) =>
                          setRiskWeights({ ...riskWeights, past_returns: Number(e.target.value) })
                        }
                        disabled={!isAdmin}
                        className="w-16 p-1 text-xs border border-slate-300 rounded font-mono text-center font-bold"
                      />
                    </div>
                  </div>

                  {/* Factor 3: Officer Workload */}
                  <div className="p-4 border border-slate-200 rounded-lg bg-slate-50/50 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="font-semibold text-xs text-slate-900">3. Officer Active Queue Workload</div>
                      <span className="font-mono font-bold text-xs bg-amber-100 text-amber-900 px-2 py-0.5 rounded">
                        {riskWeights.officer_workload} pts
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500">
                      Open active applications of assigned officer divided by configurable capacity limit (default 12).
                    </p>
                    <div className="flex items-center gap-3">
                      <input
                        type="range"
                        min="0"
                        max="80"
                        step="1"
                        value={riskWeights.officer_workload}
                        onChange={(e) =>
                          setRiskWeights({ ...riskWeights, officer_workload: Number(e.target.value) })
                        }
                        disabled={!isAdmin}
                        className="flex-1"
                      />
                      <input
                        type="number"
                        min="0"
                        max="100"
                        value={riskWeights.officer_workload}
                        onChange={(e) =>
                          setRiskWeights({ ...riskWeights, officer_workload: Number(e.target.value) })
                        }
                        disabled={!isAdmin}
                        className="w-16 p-1 text-xs border border-slate-300 rounded font-mono text-center font-bold"
                      />
                    </div>
                  </div>

                  {/* Factor 4: Current Stage Baseline */}
                  <div className="p-4 border border-slate-200 rounded-lg bg-slate-50/50 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="font-semibold text-xs text-slate-900">4. Current Stage Baseline Weight</div>
                      <span className="font-mono font-bold text-xs bg-purple-100 text-purple-900 px-2 py-0.5 rounded">
                        {riskWeights.current_stage} pts
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500">
                      Per-stage baseline multiplier from config (EVC / SAC / SHC carry higher inherent logistical delay risk).
                    </p>
                    <div className="flex items-center gap-3">
                      <input
                        type="range"
                        min="0"
                        max="80"
                        step="1"
                        value={riskWeights.current_stage}
                        onChange={(e) =>
                          setRiskWeights({ ...riskWeights, current_stage: Number(e.target.value) })
                        }
                        disabled={!isAdmin}
                        className="flex-1"
                      />
                      <input
                        type="number"
                        min="0"
                        max="100"
                        value={riskWeights.current_stage}
                        onChange={(e) =>
                          setRiskWeights({ ...riskWeights, current_stage: Number(e.target.value) })
                        }
                        disabled={!isAdmin}
                        className="w-16 p-1 text-xs border border-slate-300 rounded font-mono text-center font-bold"
                      />
                    </div>
                  </div>
                </div>

                {/* Save Button for Admin */}
                {isAdmin && (
                  <div className="flex items-center justify-between pt-4 border-t border-slate-200">
                    <div className="text-xs text-slate-500">
                      Any weight modification will generate an immutable audit log and take effect on next recomputation.
                    </div>
                    <Button
                      size="sm"
                      onClick={handleSaveRiskWeights}
                      disabled={
                        savingRiskWeights ||
                        Number(riskWeights.age_against_time_limit) +
                          Number(riskWeights.past_returns) +
                          Number(riskWeights.officer_workload) +
                          Number(riskWeights.current_stage) !== 100
                      }
                      className="bg-blue-900 hover:bg-blue-800"
                    >
                      {savingRiskWeights ? 'Saving Weights...' : 'Save & Publish Risk Weights'}
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Interactive Live Simulator Card */}
            <Card className="border-indigo-200 bg-indigo-50/20">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-indigo-700" />
                  <div>
                    <CardTitle className="text-base font-bold text-slate-900">
                      Interactive Delay Risk Formula Live Preview
                    </CardTitle>
                    <CardDescription className="text-xs text-slate-600 mt-0.5">
                      Simulate how these factor weights score a hypothetical case in real-time
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                  <div>
                    <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                      Stage SLA Consumed ({Math.round(previewAgeRatio * 100)}%)
                    </label>
                    <input
                      type="range"
                      min="0.1"
                      max="1.5"
                      step="0.05"
                      value={previewAgeRatio}
                      onChange={(e) => setPreviewAgeRatio(Number(e.target.value))}
                      className="w-full"
                    />
                    <span className="text-[10px] text-slate-500 font-mono">
                      Points: {(Math.min(1.5, previewAgeRatio) * riskWeights.age_against_time_limit).toFixed(1)} / {riskWeights.age_against_time_limit}
                    </span>
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                      Reverts / Returns ({previewReturns} of 2 max)
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="2"
                      step="1"
                      value={previewReturns}
                      onChange={(e) => setPreviewReturns(Number(e.target.value))}
                      className="w-full"
                    />
                    <span className="text-[10px] text-slate-500 font-mono">
                      Points: {((Math.min(previewReturns, 2) / 2) * riskWeights.past_returns).toFixed(1)} / {riskWeights.past_returns}
                    </span>
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                      Officer Queue ({previewWorkload} cases)
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="16"
                      step="1"
                      value={previewWorkload}
                      onChange={(e) => setPreviewWorkload(Number(e.target.value))}
                      className="w-full"
                    />
                    <span className="text-[10px] text-slate-500 font-mono">
                      Points: {(Math.min(1.0, previewWorkload / 12) * riskWeights.officer_workload).toFixed(1)} / {riskWeights.officer_workload}
                    </span>
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                      Stage Inherent Risk ({previewStageRatio === 0.8 ? 'EVC / SAC (0.8)' : previewStageRatio === 0.5 ? 'Scrutiny (0.5)' : 'Draft (0.1)'})
                    </label>
                    <select
                      value={previewStageRatio}
                      onChange={(e) => setPreviewStageRatio(Number(e.target.value))}
                      className="w-full p-1 text-xs border border-slate-300 rounded bg-white"
                    >
                      <option value={0.8}>EVC / SAC / SHC (0.8)</option>
                      <option value={0.5}>Scrutiny / Verification (0.5)</option>
                      <option value={0.2}>Submission / Intake (0.2)</option>
                    </select>
                    <span className="text-[10px] text-slate-500 font-mono">
                      Points: {(previewStageRatio * riskWeights.current_stage).toFixed(1)} / {riskWeights.current_stage}
                    </span>
                  </div>
                </div>

                {/* Simulated Outcome Banner */}
                {(() => {
                  const pt1 = Math.min(1.5, previewAgeRatio) * riskWeights.age_against_time_limit;
                  const pt2 = (Math.min(previewReturns, 2) / 2) * riskWeights.past_returns;
                  const pt3 = Math.min(1.0, previewWorkload / 12) * riskWeights.officer_workload;
                  const pt4 = previewStageRatio * riskWeights.current_stage;
                  const totalScore = Math.min(100, Math.round(pt1 + pt2 + pt3 + pt4));
                  const band = totalScore >= riskThresholds.high ? 'HIGH' : totalScore >= riskThresholds.medium ? 'MEDIUM' : 'LOW';

                  return (
                    <div className="p-4 bg-white border border-indigo-200 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div>
                        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                          Simulated Delay Risk Assessment
                        </div>
                        <div className="text-xl font-bold text-slate-900 mt-0.5">
                          Risk Score: <span className="font-mono text-indigo-700">{totalScore}</span> / 100
                        </div>
                        <p className="text-xs text-slate-600 mt-1 font-sans">
                          Open for {Math.round(previewAgeRatio * 10)} of 10 working days ({pt1.toFixed(1)} of {riskWeights.age_against_time_limit} pts), {previewReturns} past returns ({pt2.toFixed(1)} pts), officer queue at {previewWorkload} cases ({pt3.toFixed(1)} pts).
                        </p>
                      </div>
                      <div className="text-right shrink-0">
                        <span className={`inline-block px-3 py-1 rounded text-xs font-bold uppercase font-mono tracking-wide ${
                          band === 'HIGH' ? 'bg-rose-100 text-rose-800 border border-rose-300' :
                          band === 'MEDIUM' ? 'bg-amber-100 text-amber-800 border border-amber-300' :
                          'bg-emerald-100 text-emerald-800 border border-emerald-300'
                        }`}>
                          Risk Band: {band}
                        </span>
                      </div>
                    </div>
                  );
                })()}
              </CardContent>
            </Card>
          </div>
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
