'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { apiClient } from '@/lib/api';
import {
  Compass,
  ArrowRight,
  UserCheck,
  CheckCircle2,
  Clock,
  RotateCcw,
  FastForward,
  ExternalLink,
  ShieldCheck,
  AlertTriangle
} from 'lucide-react';

interface DemoStep {
  step: number;
  timeEstimate: string;
  title: string;
  targetEntity: string;
  personaEmail: string;
  personaRole: string;
  personaName: string;
  targetUrl: string;
  whatToShow: string;
  whatToSay: string;
}

const DEMO_STEPS: DemoStep[] = [
  {
    step: 1,
    timeEstimate: '0:00 - 0:25',
    title: 'New Submission & Auto-Path Selection',
    targetEntity: 'APP-10001 (App #1)',
    personaEmail: 'principal@apexkanpur.demo.example',
    personaRole: 'Institution User',
    personaName: 'Apex Institute (Kanpur)',
    targetUrl: '/portal',
    whatToShow: 'Statutory stepper, automated NEW_INSTITUTION path, WITH_AICTE status chip, and fair pendency clock.',
    whatToSay: 'The institution submits once. The rule engine determines the statutory path and starts the fair pendency clock under AICTE responsibility.'
  },
  {
    step: 2,
    timeEstimate: '0:25 - 0:50',
    title: 'Scrutiny Clearance & Conflict-Free EVC Panel',
    targetEntity: 'APP-10021 (App #21)',
    personaEmail: 'evc.coord@demo.example',
    personaRole: 'EVC Coordinator',
    personaName: 'Prof. K. Ramanathan',
    targetUrl: '/evc-queue',
    whatToShow: 'EVC Queue, 3-member candidate suggestions ranked for decision support, transparent conflict warnings (same city, max concurrency).',
    whatToSay: 'EVC panel suggestions are decision support only. The system detects geographical and concurrency conflicts, but officers retain full selection authority.'
  },
  {
    step: 3,
    timeEstimate: '0:50 - 1:15',
    title: 'Early Delay Risk Warning (Explainable)',
    targetEntity: 'APP-10033 (App #33)',
    personaEmail: 'ro.north@demo.example',
    personaRole: 'Regional Head (North)',
    personaName: 'Er. Sunil Trivedi',
    targetUrl: '/applications/33',
    whatToShow: 'Score 70.7 (High Risk band), 4-factor plain English breakdown (Age, Returns, Workload, Stage Complexity), Decision Support Only badge.',
    whatToSay: 'Before an SLA breaches, our transparent risk engine warns officers with exact factor points. It explains why a delay is forming instead of giving a black-box number.'
  },
  {
    step: 4,
    timeEstimate: '1:15 - 1:40',
    title: 'Time Travel & 3-Tier Escalation Ladder',
    targetEntity: 'APP-10006 (App #6)',
    personaEmail: 'ro.north@demo.example',
    personaRole: 'Regional Head (North)',
    personaName: 'Er. Sunil Trivedi',
    targetUrl: '/escalation-matrix',
    whatToShow: 'Click Advance Clock (+7d), notice alert escalating to Tier 2 (Regional Head) and Tier 3 (Competent Authority), explainable drawer citing APH clause.',
    whatToSay: 'If a desk is delayed, the escalation ladder fires in strict hierarchy. Every alert cites the exact Approval Process Handbook clause for accountability.'
  },
  {
    step: 5,
    timeEstimate: '1:40 - 2:05',
    title: 'Deficiency Return & Fair Clock Pause',
    targetEntity: 'APP-10001 (App #1)',
    personaEmail: 'scrutiny1@demo.example',
    personaRole: 'Scrutiny Officer',
    personaName: 'Amit Sharma',
    targetUrl: '/applications/1',
    whatToShow: 'Return with deficiency tags; notice case holder shifts to WITH_INSTITUTION, pausing the AICTE pendency clock. Institution reply resumes AICTE clock.',
    whatToSay: 'The fair clock segregates AICTE processing days from applicant response days. Neither party is unfairly blamed for the others time.'
  },
  {
    step: 6,
    timeEstimate: '2:05 - 2:25',
    title: 'Conditional Undertaking Compliance Audit',
    targetEntity: 'Undertaking #16 (Apex)',
    personaEmail: 'scrutiny1@demo.example',
    personaRole: 'Scrutiny Officer',
    personaName: 'Amit Sharma',
    targetUrl: '/undertakings',
    whatToShow: 'Institution uploads compliance evidence; officer reviews uploaded evidence and marks Verified in one click, resolving linked alerts.',
    whatToSay: 'Conditional approvals are tracked systematically. Evidence is audited with full audit history and auto-resolves overdue compliance alerts.'
  },
  {
    step: 7,
    timeEstimate: '2:25 - 2:45',
    title: 'Expiring Statutory Document & Renewal Audit',
    targetEntity: 'Document #26 (Fire NOC v2)',
    personaEmail: 'scrutiny1@demo.example',
    personaRole: 'Scrutiny Officer',
    personaName: 'Amit Sharma',
    targetUrl: '/document-validity',
    whatToShow: 'Renewal submitted queue, version chain (v1 -> v2), approval transitions old document to SUPERSEDED and new version to VALID.',
    whatToSay: 'Statutory certificates like Fire NOCs and leases expire over time. The system tracks version lineage and automatically reminds institutions before expiration.'
  },
  {
    step: 8,
    timeEstimate: '2:45 - 3:00',
    title: 'Competent Authority Approval, LoA & Audit',
    targetEntity: 'APP-10041 (App #41)',
    personaEmail: 'chairman@demo.example',
    personaRole: 'Competent Authority',
    personaName: 'Dr. Anand V. Joshi',
    targetUrl: '/applications/41',
    whatToShow: 'Record statutory decision, inspect formal Letter of Approval (SAMPLE watermark), close case, and verify cryptographic SHA-256 audit chain.',
    whatToSay: 'The Competent Authority executes the final statutory order with a tamper-evident audit trail that proves every event from submission to closure.'
  }
];

export default function DemoPresenterPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [switching, setSwitching] = useState<string | null>(null);
  const [clockStatus, setClockStatus] = useState<string | null>(null);

  const handleStepSwitch = async (step: DemoStep) => {
    try {
      setSwitching(step.personaEmail);
      await login(step.personaEmail, 'Password@123');
      router.push(step.targetUrl);
    } catch (err: any) {
      alert(`Login failed: ${err.message || 'Error'}`);
    } finally {
      setSwitching(null);
    }
  };

  const handleAdvanceClock = async (hours: number) => {
    try {
      setClockStatus('Advancing clock +7 days...');
      const res = await apiClient.post<any>('/demo/advance-clock', { hours });
      setClockStatus(`Advanced clock by ${hours}h. ${res.data?.evaluation?.alerts_escalated || 0} alerts escalated.`);
      setTimeout(() => setClockStatus(null), 4000);
    } catch (err: any) {
      alert(`Error advancing clock: ${err.message || 'Error'}`);
      setClockStatus(null);
    }
  };

  const handleResetClock = async () => {
    try {
      setClockStatus('Resetting clock to 0h offset...');
      await apiClient.post<any>('/demo/reset-clock', {});
      setClockStatus('Clock reset to real time (0h offset).');
      setTimeout(() => setClockStatus(null), 3000);
    } catch (err: any) {
      alert(`Error resetting clock: ${err.message || 'Error'}`);
      setClockStatus(null);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto pb-12">
        {/* Header Bar */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 pb-4">
          <div>
            <div className="flex items-center gap-3">
              <Compass className="w-7 h-7 text-[#0f2b5c]" />
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                Demo Presenter Guide (Continuous Story)
              </h1>
              <Badge variant="info">DEMO_MODE ACTIVE</Badge>
            </div>
            <p className="text-sm text-slate-600 mt-1">
              3-Minute uninterrupted demonstration thread following Apex Institute of Technology (Kanpur, Northern RO).
            </p>
          </div>

          {/* Quick Clock Actions */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleAdvanceClock(168)}
              className="gap-1.5 text-xs text-amber-800 border-amber-300 hover:bg-amber-50"
            >
              <FastForward className="w-3.5 h-3.5" />
              Advance +7 Days (+168h)
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleResetClock}
              className="gap-1.5 text-xs text-slate-700 hover:bg-slate-100"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset Clock (0h)
            </Button>
          </div>
        </div>

        {clockStatus && (
          <div className="p-3 bg-blue-50 border border-blue-200 rounded text-xs text-blue-900 font-medium flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0" />
            <span>{clockStatus}</span>
          </div>
        )}

        {/* Presenter Summary Callout */}
        <div className="bg-slate-50 border border-slate-300 rounded-lg p-4 text-xs text-slate-700 space-y-1.5">
          <div className="font-semibold text-slate-900 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#0f2b5c]" />
            Continuous Rehearsal Rule:
          </div>
          <div>
            Click <strong>Switch Persona & Open Screen</strong> on each step sequentially. To restore the pristine starting state at any time, run <code>make demo-reset</code> or <code>make demo-check</code> in the terminal.
          </div>
        </div>

        {/* 8-Step Interactive Grid */}
        <div className="space-y-4">
          {DEMO_STEPS.map((s) => (
            <Card key={s.step} className="border border-slate-200 hover:border-slate-300 transition-all shadow-sm">
              <CardContent className="p-5">
                <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                  {/* Step Info */}
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center gap-3">
                      <div className="w-7 h-7 rounded-full bg-[#0f2b5c] text-white flex items-center justify-center font-bold text-xs shrink-0">
                        {s.step}
                      </div>
                      <h3 className="text-base font-bold text-slate-900">
                        {s.title}
                      </h3>
                      <Badge variant="neutral" className="font-mono text-[11px]">
                        {s.timeEstimate}
                      </Badge>
                      <Badge variant="info" className="font-mono text-[11px]">
                        {s.targetEntity}
                      </Badge>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 text-xs">
                      <div className="bg-slate-50 rounded p-2.5 border border-slate-200">
                        <span className="font-semibold text-slate-800 block mb-0.5">What the audience sees:</span>
                        <p className="text-slate-600 leading-relaxed">{s.whatToShow}</p>
                      </div>
                      <div className="bg-blue-50/60 rounded p-2.5 border border-blue-200/60">
                        <span className="font-semibold text-[#0f2b5c] block mb-0.5">What you say (Script):</span>
                        <p className="text-slate-700 leading-relaxed italic">&ldquo;{s.whatToSay}&rdquo;</p>
                      </div>
                    </div>
                  </div>

                  {/* Persona Switch Action */}
                  <div className="flex flex-col items-start lg:items-end gap-2 shrink-0 pt-1">
                    <div className="text-right">
                      <div className="text-[11px] text-slate-500">Demo Persona</div>
                      <div className="text-xs font-semibold text-slate-900">{s.personaName}</div>
                      <div className="text-[11px] font-mono text-slate-500">{s.personaEmail}</div>
                    </div>

                    <Button
                      size="sm"
                      onClick={() => handleStepSwitch(s)}
                      disabled={switching === s.personaEmail}
                      className="bg-[#0f2b5c] hover:bg-[#0c234b] text-white gap-1.5 text-xs font-medium mt-1 w-full lg:w-auto"
                    >
                      <UserCheck className="w-3.5 h-3.5" />
                      {switching === s.personaEmail ? 'Switching...' : 'Switch Persona & Open Screen'}
                      <ExternalLink className="w-3 h-3 ml-0.5" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
