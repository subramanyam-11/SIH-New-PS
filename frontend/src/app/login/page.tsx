'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { apiClient } from '@/lib/api';
import { Shield, Lock, Mail, ArrowRight, UserCheck } from 'lucide-react';

interface DemoPersona {
  role: string;
  label: string;
  name: string;
  email: string;
  badge: 'neutral' | 'info' | 'success' | 'warning' | 'danger';
}

const DEMO_PERSONAS: DemoPersona[] = [
  {
    role: 'REGIONAL_HEAD',
    label: 'Regional Head (North)',
    name: 'Er. Sunil Trivedi',
    email: 'ro.north@demo.example',
    badge: 'info'
  },
  {
    role: 'SCRUTINY_OFFICER',
    label: 'Scrutiny Officer',
    name: 'Amit Sharma',
    email: 'scrutiny1@demo.example',
    badge: 'info'
  },
  {
    role: 'EVC_COORDINATOR',
    label: 'EVC Coordinator',
    name: 'Prof. K. Ramanathan',
    email: 'evc.coord@demo.example',
    badge: 'warning'
  },
  {
    role: 'COMPETENT_AUTHORITY',
    label: 'Competent Authority',
    name: 'Dr. Anand V. Joshi',
    email: 'chairman@demo.example',
    badge: 'success'
  },
  {
    role: 'ADMIN',
    label: 'System Admin',
    name: 'Dr. Rajesh Verma',
    email: 'admin@demo.example',
    badge: 'neutral'
  },
  {
    role: 'INSTITUTION_USER',
    label: 'Institution User',
    name: 'Apex Institute (Kanpur)',
    email: 'principal@apexkanpur.demo.example',
    badge: 'neutral'
  },
  {
    role: 'BUREAU_OFFICER',
    label: 'Bureau Officer',
    name: 'Dr. Alok Verma',
    email: 'bureau.officer@demo.example',
    badge: 'info'
  },
  {
    role: 'COMMITTEE_MEMBER',
    label: 'Committee Member',
    name: 'Dr. Ramesh Sharma (EVC)',
    email: 'evc.member@demo.example',
    badge: 'warning'
  }
];

export default function LoginPage() {
  const { login, demoLogin } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [demoModeEnabled, setDemoModeEnabled] = useState(true);

  useEffect(() => {
    // Check demo mode from health endpoint
    apiClient.get('/../health').then((res) => {
      if (res.data && typeof res.data.demo_mode === 'boolean') {
        setDemoModeEnabled(res.data.demo_mode);
      }
    }).catch(() => {
      // Default to true for dev environment
      setDemoModeEnabled(true);
    });
  }, []);

  const handleStandardLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setErrorMsg('Please enter both email and password.');
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMsg(null);
      await login(email, password);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Invalid email or password.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDemoClick = async (persona: DemoPersona) => {
    try {
      setIsSubmitting(true);
      setErrorMsg(null);
      await demoLogin(persona.role, persona.email);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || `Failed to sign in as ${persona.label}.`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col justify-center items-center py-12 px-4 sm:px-6 lg:px-8">
      {/* AICTE Header */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center mb-6">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-lg bg-[#0f2b5c] text-white shadow-sm mb-3">
          <Shield className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">
          AICTE Approval Management System
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Smart India Hackathon 2026 | Problem ID: SIH26262
        </p>
      </div>

      <div className="w-full max-w-md space-y-6">
        {/* Standard Login Card */}
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Sign in to your account</CardTitle>
              <CardDescription>Enter your official administrative credentials</CardDescription>
            </div>
          </CardHeader>

          <CardContent>
            {errorMsg && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-md">
                {errorMsg}
              </div>
            )}

            <form onSubmit={handleStandardLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Email Address
                </label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Mail className="w-4 h-4" />
                  </span>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="officer@demo.example"
                    className="w-full pl-9 pr-3 py-2 text-sm rounded border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0f2b5c] focus:border-transparent bg-white text-slate-900"
                    disabled={isSubmitting}
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Password
                </label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </span>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-9 pr-3 py-2 text-sm rounded border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0f2b5c] focus:border-transparent bg-white text-slate-900"
                    disabled={isSubmitting}
                  />
                </div>
              </div>

              <Button
                type="submit"
                variant="primary"
                className="w-full py-2 text-sm flex items-center justify-center gap-2"
                disabled={isSubmitting}
              >
                <span>{isSubmitting ? 'Authenticating...' : 'Sign In'}</span>
                <ArrowRight className="w-4 h-4" />
              </Button>
            </form>
          </CardContent>

          <CardFooter>
            <div className="text-[11px] text-slate-400">
              Role-based access strictly governed by APH 2026-27 guidelines.
            </div>
          </CardFooter>
        </Card>

        {/* Demo Fast-Login Chips (Only when DEMO_MODE=true) */}
        {demoModeEnabled && (
          <Card className="border-dashed border-slate-300 bg-slate-50/80">
            <CardHeader className="py-3 px-4">
              <div className="flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-slate-600" />
                <CardTitle className="text-xs uppercase tracking-wider text-slate-700">
                  One-Click Demo Personas
                </CardTitle>
              </div>
              <Badge variant="neutral" size="sm">DEMO_MODE</Badge>
            </CardHeader>

            <CardContent className="p-4 pt-2">
              <p className="text-xs text-slate-500 mb-3">
                Select any verified demo persona to authenticate instantly without entering credentials:
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {DEMO_PERSONAS.map((persona) => (
                  <button
                    key={persona.email}
                    onClick={() => handleDemoClick(persona)}
                    disabled={isSubmitting}
                    className="text-left p-2.5 rounded-md border border-slate-200 bg-white hover:bg-blue-50/50 hover:border-blue-300 transition-all focus:outline-none focus:ring-1 focus:ring-blue-500"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-semibold text-slate-800">
                        {persona.label}
                      </span>
                      <Badge variant={persona.badge} size="sm">
                        {persona.role.split('_')[0]}
                      </Badge>
                    </div>
                    <div className="text-[11px] text-slate-500 truncate">{persona.name}</div>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
