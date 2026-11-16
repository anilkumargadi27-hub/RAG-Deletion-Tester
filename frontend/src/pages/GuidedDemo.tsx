import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiFetch } from '../api/client';
import { TestRun, ProbeResult } from '../types';
import {
  PlayCircle, RefreshCw, CheckCircle2, AlertTriangle, ShieldCheck,
  ArrowRight, Search, FileText, Ban, XCircle
} from 'lucide-react';

export const GuidedDemo: React.FC = () => {
  const [step, setStep] = useState<number>(0);
  const [faultyRunId, setFaultyRunId] = useState<string | null>(null);
  const [secureRunId, setSecureRunId] = useState<string | null>(null);
  const [faultyRun, setFaultyRun] = useState<TestRun | null>(null);
  const [secureRun, setSecureRun] = useState<TestRun | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  // Poll faulty run status
  useEffect(() => {
    if (!faultyRunId) return;
    const interval = setInterval(async () => {
      try {
        const res = await apiFetch<TestRun>(`/api/synthetic/runs/${faultyRunId}`);
        setFaultyRun(res);
        if (res.status === 'completed') {
          clearInterval(interval);
          setStep(3); // Move to evidence inspection
          setLoading(false);
        } else if (res.status === 'failed' || res.status === 'cancelled') {
          clearInterval(interval);
          setLoading(false);
          setError(`Faulty demonstration run ${res.status}`);
        }
      } catch (err: any) {
        setError(err.message);
      }
    }, 1200);
    return () => clearInterval(interval);
  }, [faultyRunId]);

  // Poll secure run status
  useEffect(() => {
    if (!secureRunId) return;
    const interval = setInterval(async () => {
      try {
        const res = await apiFetch<TestRun>(`/api/synthetic/runs/${secureRunId}`);
        setSecureRun(res);
        if (res.status === 'completed') {
          clearInterval(interval);
          setStep(5); // Move to comparison
          setLoading(false);
        } else if (res.status === 'failed' || res.status === 'cancelled') {
          clearInterval(interval);
          setLoading(false);
          setError(`Secure corrected run ${res.status}`);
        }
      } catch (err: any) {
        setError(err.message);
      }
    }, 1200);
    return () => clearInterval(interval);
  }, [secureRunId]);

  const startDemo = async () => {
    setError(null);
    setLoading(true);
    setStep(1);
    try {
      // Step 1: Launch Stale Index Demo Run
      const run = await apiFetch<TestRun>('/api/synthetic/runs', {
        method: 'POST',
        body: JSON.stringify({
          name: 'Guided Demo - Stale Index Fault',
          fault_mode: 'stale_index',
          answer_mode: 'local_extractive',
          retrieval_mode: 'semantic_vector',
          is_guided_demo: true,
        }),
      });
      setFaultyRunId(run.id);
      setStep(2);
    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  };

  const runCorrectedRerun = async () => {
    setError(null);
    setLoading(true);
    setStep(4);
    try {
      const run = await apiFetch<TestRun>('/api/synthetic/runs', {
        method: 'POST',
        body: JSON.stringify({
          name: 'Guided Demo - Corrected Secure Baseline',
          fault_mode: 'secure_baseline',
          answer_mode: 'local_extractive',
          retrieval_mode: 'semantic_vector',
          is_guided_demo: true,
        }),
      });
      setSecureRunId(run.id);
    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  };

  const resetDemo = () => {
    setStep(0);
    setFaultyRunId(null);
    setSecureRunId(null);
    setFaultyRun(null);
    setSecureRun(null);
    setError(null);
  };

  const faultyProbes = faultyRun?.probes || [];
  const baselineProbe = faultyProbes.find(p => p.probe_type === 'baseline');
  const leakedProbe = faultyProbes.find(p => p.verdict === 'leaked');

  const secureProbes = secureRun?.probes || [];
  const secureBlockedProbe = secureProbes.find(p => p.probe_type === 'direct');
  const secureControlProbe = secureProbes.find(p => p.probe_type === 'positive_control');

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <span className="text-xs font-bold text-brand-600 uppercase tracking-wider">
            Interactive Walkthrough
          </span>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">Guided Verification Demo</h1>
          <p className="text-sm text-slate-500 mt-1">
            Experience real leak reproduction through a stale storage copy, inspect the trace, then verify the corrected secure fix.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {step > 0 && (
            <button
              onClick={resetDemo}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Restart Demo</span>
            </button>
          )}

          {step === 0 && (
            <button
              onClick={startDemo}
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-sm font-semibold shadow-sm transition-colors"
            >
              <PlayCircle className="w-4 h-4" />
              <span>Launch Guided Demo</span>
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Stepper Display */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          { num: 1, label: '1. Authorized Baseline', active: step >= 1 },
          { num: 2, label: '2. Deletion Mutation', active: step >= 2 },
          { num: 3, label: '3. Faulty Leak Evidence', active: step >= 3 },
          { num: 4, label: '4. Secure Fix Rerun', active: step >= 4 },
          { num: 5, label: '5. Side-by-Side Result', active: step >= 5 },
        ].map((s) => (
          <div
            key={s.num}
            className={`p-3 rounded-lg border text-xs font-semibold flex items-center gap-2 ${
              s.active
                ? 'bg-brand-50 border-brand-300 text-brand-900'
                : 'bg-white border-slate-200 text-slate-400'
            }`}
          >
            <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${
              s.active ? 'bg-brand-600 text-white' : 'bg-slate-200 text-slate-600'
            }`}>
              {s.num}
            </div>
            <span>{s.label}</span>
          </div>
        ))}
      </div>

      {/* Interactive Step Content */}
      {step === 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center space-y-4 shadow-sm">
          <FileText className="w-12 h-12 text-brand-500 mx-auto" />
          <h2 className="text-xl font-bold text-slate-900">Scenario: Ravi's Compensation Record</h2>
          <p className="text-sm text-slate-600 max-w-xl mx-auto leading-relaxed">
            A fictional HR record states: <strong>"Ravi's monthly salary is INR 90,000"</strong> (Canary: <code>CANARY-HR-78923-SAL</code>).
            When this document is deleted, can an employee probe the assistant and still extract that confidential figure?
          </p>
          <button
            onClick={startDemo}
            className="inline-flex items-center gap-2 px-6 py-3 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-sm font-semibold shadow-md"
          >
            <PlayCircle className="w-5 h-5" />
            <span>Start Step-by-Step Execution</span>
          </button>
        </div>
      )}

      {/* Step 1 & 2: Baseline & Faulty Probe Running */}
      {(step === 1 || step === 2) && (
        <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center space-y-4 shadow-sm">
          <RefreshCw className="w-8 h-8 text-brand-600 animate-spin mx-auto" />
          <h3 className="text-lg font-bold text-slate-900">
            {step === 1 ? 'Executing Authorized Baseline Query...' : 'Simulating Deletion Mutation & Stale Storage Probe...'}
          </h3>
          <p className="text-sm text-slate-500 max-w-md mx-auto">
            {step === 1
              ? 'Verifying that the authorized HR manager can answer the fact before mutation.'
              : 'Committing deletion tombstone, exercising stale index fault, and probing as unauthorized principal.'}
          </p>
        </div>
      )}

      {/* Step 3: Faulty Leak Detected */}
      {step === 3 && leakedProbe && (
        <div className="space-y-6">
          <div className="bg-red-50 border border-red-200 rounded-2xl p-6">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-6 h-6 text-red-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-lg font-bold text-red-900">
                  Leak Detected: AI Disclosed Deleted Secret
                </h3>
                <p className="text-sm text-red-700 mt-1">
                  Even though the document was marked deleted, the vector store retained an unpurged chunk.
                  Because retrieval lacked authoritative database revalidation, the model exposed the restricted salary!
                </p>
              </div>
            </div>

            <div className="mt-4 bg-white rounded-xl border border-red-200 p-4 space-y-3">
              <div>
                <span className="text-xs font-semibold text-slate-500 uppercase">Unauthorized Probe Question:</span>
                <p className="text-sm font-semibold text-slate-900">{leakedProbe.query}</p>
              </div>
              <div>
                <span className="text-xs font-semibold text-slate-500 uppercase">Disclosed Answer:</span>
                <p className="text-sm text-red-800 bg-red-50/50 p-2.5 rounded font-mono border border-red-100">
                  {leakedProbe.response_text}
                </p>
              </div>
              <div className="flex flex-wrap gap-4 text-xs">
                <div>
                  <span className="text-slate-500">Detected Fact:</span>{' '}
                  <strong className="text-red-700">{leakedProbe.detected_fact}</strong>
                </div>
                <div>
                  <span className="text-slate-500">Storage Source:</span>{' '}
                  <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-800">
                    {leakedProbe.storage_contributed.join(', ') || 'vector_store'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="text-center">
            <button
              onClick={runCorrectedRerun}
              disabled={loading}
              className="inline-flex items-center gap-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-semibold shadow-md transition-colors"
            >
              <ShieldCheck className="w-5 h-5" />
              <span>Rerun with Corrected Secure Pipeline</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Secure Rerun In Progress */}
      {step === 4 && (
        <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center space-y-4 shadow-sm">
          <RefreshCw className="w-8 h-8 text-emerald-600 animate-spin mx-auto" />
          <h3 className="text-lg font-bold text-slate-900">Rerunning in Secure Baseline Pipeline...</h3>
          <p className="text-sm text-slate-500 max-w-md mx-auto">
            Enforcing database tombstones, vector chunk purges, cache invalidation, and provenance checks.
          </p>
        </div>
      )}

      {/* Step 5: Side-by-Side Comparison */}
      {step === 5 && (
        <div className="space-y-6">
          <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-6">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0" />
              <div>
                <h3 className="text-lg font-bold text-emerald-900">
                  Secure Verification Passed: No Leakage Observed
                </h3>
                <p className="text-sm text-emerald-700 mt-1">
                  The authoritative tombstone check prevented the deleted chunk from reaching the answer generator.
                  Meanwhile, permitted public policy questions continued to be answered correctly!
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Faulty Box */}
            <div className="bg-white rounded-2xl border border-red-200 p-5 space-y-3 shadow-sm">
              <div className="flex items-center justify-between border-b border-red-100 pb-2">
                <span className="text-xs font-bold text-red-700 uppercase">Faulty Configuration</span>
                <span className="px-2 py-0.5 bg-red-100 text-red-800 text-xs font-semibold rounded-full">
                  Stale Index Fault
                </span>
              </div>
              <p className="text-xs text-slate-500">Query: {leakedProbe?.query}</p>
              <div className="text-xs font-mono bg-red-50 text-red-800 p-3 rounded border border-red-100">
                {leakedProbe?.response_text}
              </div>
              <div className="flex items-center gap-2 text-xs font-bold text-red-600">
                <XCircle className="w-4 h-4" />
                <span>Verdict: LEAKED</span>
              </div>
            </div>

            {/* Corrected Secure Box */}
            <div className="bg-white rounded-2xl border border-emerald-200 p-5 space-y-3 shadow-sm">
              <div className="flex items-center justify-between border-b border-emerald-100 pb-2">
                <span className="text-xs font-bold text-emerald-700 uppercase">Corrected Pipeline</span>
                <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 text-xs font-semibold rounded-full">
                  Secure Baseline
                </span>
              </div>
              <p className="text-xs text-slate-500">Query: {secureBlockedProbe?.query}</p>
              <div className="text-xs font-mono bg-emerald-50 text-emerald-900 p-3 rounded border border-emerald-100">
                {secureBlockedProbe?.response_text}
              </div>
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-600">
                <CheckCircle2 className="w-4 h-4" />
                <span>Verdict: BLOCKED (Safe Refusal)</span>
              </div>
            </div>
          </div>

          <div className="flex justify-center gap-4 pt-4">
            <button
              onClick={() => navigate(`/compare?faulty=${faultyRunId}&secure=${secureRunId}`)}
              className="px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-sm font-semibold shadow-sm"
            >
              Open Full Comparison Dashboard
            </button>
            <button
              onClick={resetDemo}
              className="px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-sm font-semibold"
            >
              Run Again
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
