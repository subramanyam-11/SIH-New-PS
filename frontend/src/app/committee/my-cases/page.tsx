'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth';
import { committeeApi, CommitteeAssignment, CommitteeObservation } from '@/lib/api';
import { DecisionSupportBadge } from '@/components/ui/DecisionSupportBadge';
import { 
  ClipboardList, 
  Calendar, 
  MapPin, 
  Building2, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  MessageSquare,
  Send,
  X
} from 'lucide-react';

export default function CommitteeCasesPage() {
  const { scope } = useAuth();
  const [assignments, setAssignments] = useState<CommitteeAssignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal state
  const [selectedAssignment, setSelectedAssignment] = useState<CommitteeAssignment | null>(null);
  const [observations, setObservations] = useState('');
  const [recommendation, setRecommendation] = useState<string>('RECOMMEND_APPROVAL');
  const [submitting, setSubmitting] = useState(false);
  const [modalSuccess, setModalSuccess] = useState<string | null>(null);
  const [existingObservations, setExistingObservations] = useState<CommitteeObservation[]>([]);

  useEffect(() => {
    loadCases();
  }, []);

  const loadCases = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await committeeApi.getMyCases();
      setAssignments(data);
    } catch (err: any) {
      console.error('Failed to load committee cases', err);
      setError(err?.response?.data?.detail || 'Failed to load assigned committee cases');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = async (assignment: CommitteeAssignment) => {
    setSelectedAssignment(assignment);
    setObservations('');
    setRecommendation('RECOMMEND_APPROVAL');
    setModalSuccess(null);
    try {
      const obs = await committeeApi.getObservations(assignment.application_id);
      setExistingObservations(obs);
    } catch (e) {
      console.error('Failed to load existing observations', e);
      setExistingObservations([]);
    }
  };

  const handleSubmitObservation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAssignment || !observations.trim()) return;

    try {
      setSubmitting(true);
      await committeeApi.addObservation(selectedAssignment.application_id, {
        committee_type: selectedAssignment.committee_type,
        observations: observations.trim(),
        recommendation: recommendation,
      });
      setModalSuccess('Observation and advisory recommendation recorded successfully.');
      setObservations('');
      // Reload observations
      const obs = await committeeApi.getObservations(selectedAssignment.application_id);
      setExistingObservations(obs);
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to record observation');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">Committee Member Portal</h1>
            <DecisionSupportBadge size="sm" />
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Assigned applications for EVC inspection, SAC hearing, or SHC review.
          </p>
        </div>
      </div>

      {/* Advisory Banner */}
      <div className="p-4 rounded-xl border border-blue-500/20 bg-blue-950/20 flex items-start gap-3">
        <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 shrink-0 mt-0.5">
          <ClipboardList className="w-5 h-5" />
        </div>
        <div className="text-xs text-slate-300 leading-relaxed">
          <span className="font-semibold text-white">Decision Support Notice: </span>
          As a committee member, your recorded observations and recommendations are purely non-binding decision support. They provide technical and expert guidance to AICTE Scrutiny Officers, Regional Heads, and the Competent Authority, who retain full statutory decision authority.
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="p-12 text-center text-slate-400">Loading assigned cases...</div>
      ) : error ? (
        <div className="p-6 rounded-xl border border-red-500/20 bg-red-950/20 text-red-400 flex items-center gap-3">
          <AlertCircle className="w-5 h-5" />
          <span>{error}</span>
        </div>
      ) : assignments.length === 0 ? (
        <div className="p-12 rounded-xl border border-slate-800 bg-slate-900/50 text-center">
          <ClipboardList className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-300">No Committee Cases Assigned</h3>
          <p className="text-sm text-slate-500 mt-1">
            You do not currently have any active committee visit or meeting assignments.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {assignments.map((item) => (
            <div
              key={item.id}
              className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-blue-950/60 text-blue-400 border border-blue-800/40">
                    {item.application_number}
                  </span>
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded-full border ${
                      item.committee_type === 'EVC'
                        ? 'bg-amber-950/40 text-amber-300 border-amber-800/40'
                        : item.committee_type === 'SAC'
                        ? 'bg-purple-950/40 text-purple-300 border-purple-800/40'
                        : 'bg-emerald-950/40 text-emerald-300 border-emerald-800/40'
                    }`}
                  >
                    {item.committee_type} Committee
                  </span>
                </div>

                <div>
                  <h4 className="text-sm font-semibold text-white line-clamp-1">{item.institution_name}</h4>
                  <p className="text-xs text-slate-400 mt-0.5">{item.category_title}</p>
                </div>

                <div className="pt-2 border-t border-slate-800/60 space-y-1.5 text-xs text-slate-400">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    <span>Meeting/Visit: {item.meeting_date || 'Scheduled'}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <MapPin className="w-3.5 h-3.5 text-slate-500" />
                    <span className="truncate">{item.venue || 'Regional Office / Campus'}</span>
                  </div>
                </div>
              </div>

              <div className="mt-5 pt-3 border-t border-slate-800/60 flex items-center justify-between">
                <span className="text-xs text-slate-500">Status: {item.status}</span>
                <button
                  onClick={() => handleOpenModal(item)}
                  className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-medium text-white transition flex items-center gap-1.5"
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>Observations</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Observation Modal */}
      {selectedAssignment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-bold text-white">Record Committee Observation</h3>
                  <DecisionSupportBadge size="sm" />
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  {selectedAssignment.application_number} • {selectedAssignment.institution_name}
                </p>
              </div>
              <button
                onClick={() => setSelectedAssignment(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Existing Observations */}
            {existingObservations.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-semibold uppercase text-slate-400 tracking-wider">
                  Submitted Advisory Observations ({existingObservations.length})
                </h4>
                <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
                  {existingObservations.map((obs) => (
                    <div key={obs.id} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs space-y-1">
                      <div className="flex items-center justify-between text-slate-400">
                        <span className="font-semibold text-slate-300">{obs.member_name} ({obs.committee_type})</span>
                        <span className="text-[11px] font-mono text-blue-400">{obs.recommendation}</span>
                      </div>
                      <p className="text-slate-300 whitespace-pre-wrap">{obs.observations}</p>
                      <div className="text-[10px] text-slate-500 pt-1">
                        {new Date(obs.created_at).toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Success message */}
            {modalSuccess && (
              <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{modalSuccess}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmitObservation} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-400 tracking-wider mb-1.5">
                  Advisory Recommendation <span className="text-red-400">*</span>
                </label>
                <select
                  value={recommendation}
                  onChange={(e) => setRecommendation(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                >
                  <option value="RECOMMEND_APPROVAL">Recommend Approval (Satisfactory Compliance)</option>
                  <option value="RECOMMEND_REJECTION">Recommend Rejection (Major Deficiencies Unresolved)</option>
                  <option value="RECOMMEND_RE_INSPECTION">Recommend Re-Inspection (Physical Verification Needed)</option>
                  <option value="NEEDS_CLARIFICATION">Needs Clarification (Queries for Institution)</option>
                </select>
                <p className="text-[11px] text-slate-500 mt-1">
                  Decision support only: this advisory recommendation is recorded for the scrutiny committee and does not alter the case stage.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-slate-400 tracking-wider mb-1.5">
                  Inspection / Review Observations <span className="text-red-400">*</span>
                </label>
                <textarea
                  rows={4}
                  value={observations}
                  onChange={(e) => setObservations(e.target.value)}
                  placeholder="Record factual observations regarding land area, built-up space, lab equipment, faculty qualifications, or committee deliberations..."
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedAssignment(null)}
                  className="px-4 py-2 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 text-xs font-medium transition"
                >
                  Close
                </button>
                <button
                  type="submit"
                  disabled={submitting || !observations.trim()}
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-medium transition flex items-center gap-1.5"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{submitting ? 'Submitting...' : 'Submit Observation'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
