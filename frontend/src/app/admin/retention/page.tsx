'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { retentionApi } from '@/lib/api';
import {
  Archive,
  Download,
  AlertCircle,
  Save,
  Clock,
  ShieldAlert,
  CheckCircle2,
  Lock
} from 'lucide-react';

export default function RetentionPreviewPage() {
  const [preview, setPreview] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Form policy values
  const [closedCasesYears, setClosedCasesYears] = useState(5);
  const [resolvedAlertsDays, setResolvedAlertsDays] = useState(180);
  const [notificationsDays, setNotificationsDays] = useState(90);
  const [outboxEntriesDays, setOutboxEntriesDays] = useState(60);

  const fetchPreview = async () => {
    setLoading(true);
    try {
      const data = await retentionApi.getPreview();
      setPreview(data);
      if (data.policy) {
        setClosedCasesYears(data.policy.closed_cases_years || 5);
        setResolvedAlertsDays(data.policy.resolved_alerts_days || 180);
        setNotificationsDays(data.policy.notifications_days || 90);
        setOutboxEntriesDays(data.policy.outbox_entries_days || 60);
      }
    } catch (err) {
      console.error('Failed to load retention preview', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPreview();
  }, []);

  const handleSavePolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveSuccess(false);
    try {
      await retentionApi.updatePolicy({
        closed_cases_years: Number(closedCasesYears),
        resolved_alerts_days: Number(resolvedAlertsDays),
        notifications_days: Number(notificationsDays),
        outbox_entries_days: Number(outboxEntriesDays),
      });
      setSaveSuccess(true);
      await fetchPreview();
      setTimeout(() => setSaveSuccess(false), 4000);
    } catch (err) {
      console.error('Failed to update retention policy', err);
    } finally {
      setSaving(false);
    }
  };

  const handleExportCsv = () => {
    window.location.href = retentionApi.exportPreviewCsvUrl();
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Statutory Data Retention Preview
            </h1>
            <Badge variant="warning" size="sm">
              DRY RUN ONLY
            </Badge>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Simulate and audit lifecycle retention thresholds prior to statutory compliance archiving.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportCsv}
            className="flex items-center gap-2 border-slate-300"
          >
            <Download className="w-4 h-4 text-slate-600" />
            <span>Export Preview CSV</span>
          </Button>
        </div>
      </div>

      {/* Prominent Prototype Non-Destructive Notice */}
      <div className="p-4 rounded-lg border border-amber-300 bg-amber-50 text-amber-900 flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="text-xs">
          <strong className="font-semibold uppercase tracking-wider block text-[11px] mb-0.5">
            Preview only. No data is deleted by this prototype.
          </strong>
          This interface performs non-destructive dry-run calculations against the live database according to statutory retention rules. In accordance with government records retention mandates, the cryptographic audit log is permanently exempt from archival or deletion.
        </div>
      </div>

      {/* Grid: Policy Settings & Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Policy Configuration Form */}
        <Card className="lg:col-span-1 border border-slate-200 bg-white">
          <CardHeader className="p-4 border-b border-slate-100">
            <CardTitle className="text-sm font-semibold text-slate-800 flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-600" />
              <span>Retention Period Rules</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-500">
              Update statutory retention periods. All updates are recorded in the audit trail.
            </CardDescription>
          </CardHeader>

          <CardContent className="p-4">
            <form onSubmit={handleSavePolicy} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Closed Cases Retention (Years)
                </label>
                <input
                  type="number"
                  min="1"
                  max="20"
                  value={closedCasesYears}
                  onChange={(e) => setClosedCasesYears(Number(e.target.value))}
                  className="w-full text-xs p-2 rounded border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <span className="text-[10px] text-slate-400">Statutory default: 5 years</span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Resolved Alerts Retention (Days)
                </label>
                <input
                  type="number"
                  min="30"
                  max="730"
                  value={resolvedAlertsDays}
                  onChange={(e) => setResolvedAlertsDays(Number(e.target.value))}
                  className="w-full text-xs p-2 rounded border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <span className="text-[10px] text-slate-400">Statutory default: 180 days</span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  In-App Notifications (Days)
                </label>
                <input
                  type="number"
                  min="15"
                  max="365"
                  value={notificationsDays}
                  onChange={(e) => setNotificationsDays(Number(e.target.value))}
                  className="w-full text-xs p-2 rounded border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <span className="text-[10px] text-slate-400">Default: 90 days</span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Email Outbox Logs (Days)
                </label>
                <input
                  type="number"
                  min="15"
                  max="365"
                  value={outboxEntriesDays}
                  onChange={(e) => setOutboxEntriesDays(Number(e.target.value))}
                  className="w-full text-xs p-2 rounded border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <span className="text-[10px] text-slate-400">Default: 60 days</span>
              </div>

              <div className="pt-2">
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={saving}
                  className="w-full flex items-center justify-center gap-2"
                >
                  <Save className="w-4 h-4" />
                  <span>{saving ? 'Updating...' : 'Save & Re-evaluate'}</span>
                </Button>
              </div>

              {saveSuccess && (
                <div className="p-2 bg-emerald-50 border border-emerald-200 text-emerald-800 text-[11px] rounded flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Retention thresholds saved and audited.</span>
                </div>
              )}
            </form>
          </CardContent>
        </Card>

        {/* Retention Preview Summary Table */}
        <Card className="lg:col-span-2 border border-slate-200 bg-white overflow-hidden">
          <CardHeader className="p-4 border-b border-slate-100 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-sm font-semibold text-slate-800">
                Candidate Records for Archival
              </CardTitle>
              <CardDescription className="text-xs text-slate-500">
                Evaluation timestamp: {preview?.generated_at ? preview.generated_at.replace('T', ' ').substring(0, 19) : '-'}
              </CardDescription>
            </div>
            <div className="text-right">
              <span className="text-xs text-slate-500">Total Candidates:</span>{' '}
              <strong className="text-sm font-mono text-slate-900">
                {preview?.summary?.total_candidate_records ?? 0}
              </strong>
            </div>
          </CardHeader>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Data Category</th>
                  <th className="py-2.5 px-3">Statutory Threshold</th>
                  <th className="py-2.5 px-3 text-right">Candidates</th>
                  <th className="py-2.5 px-3">Candidate Date Range</th>
                  <th className="py-2.5 px-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {loading ? (
                  <tr>
                    <td colSpan={5} className="text-center py-8 text-slate-400">
                      Evaluating retention candidate records...
                    </td>
                  </tr>
                ) : !preview?.summary?.categories ? (
                  <tr>
                    <td colSpan={5} className="text-center py-8 text-slate-400">
                      No retention preview data available.
                    </td>
                  </tr>
                ) : (
                  preview.summary.categories.map((cat: any) => (
                    <tr
                      key={cat.category}
                      className={`hover:bg-slate-50/70 transition-colors ${
                        cat.category === 'AUDIT_LOG' ? 'bg-slate-50/50 font-medium' : ''
                      }`}
                    >
                      <td className="py-3 px-3">
                        <div className="font-semibold text-slate-900 flex items-center gap-1.5">
                          {cat.category === 'AUDIT_LOG' && (
                            <Lock className="w-3.5 h-3.5 text-emerald-600" />
                          )}
                          <span>{cat.title}</span>
                        </div>
                        <div className="font-mono text-[10px] text-slate-400">{cat.category}</div>
                      </td>
                      <td className="py-3 px-3 text-slate-600">
                        {cat.statutory_threshold}
                      </td>
                      <td className="py-3 px-3 text-right font-mono font-semibold">
                        {cat.candidate_count}
                      </td>
                      <td className="py-3 px-3 text-[11px] text-slate-500 font-mono">
                        {cat.oldest_record ? (
                          <>
                            {cat.oldest_record.substring(0, 10)} to {cat.newest_candidate?.substring(0, 10)}
                          </>
                        ) : (
                          <span className="text-slate-400 italic">None eligible</span>
                        )}
                      </td>
                      <td className="py-3 px-3">
                        {cat.category === 'AUDIT_LOG' ? (
                          <Badge variant="success" size="sm">
                            EXEMPT (IMMUTABLE)
                          </Badge>
                        ) : cat.candidate_count > 0 ? (
                          <Badge variant="warning" size="sm">
                            ELIGIBLE
                          </Badge>
                        ) : (
                          <Badge variant="neutral" size="sm">
                            WITHIN LIMITS
                          </Badge>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <CardFooter className="p-3 bg-slate-50 border-t border-slate-200 text-[11px] text-slate-500">
            Records remain active until formal batch export and archival authorization.
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
