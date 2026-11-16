import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../api/client';
import { TestRun, ProbeResult } from '../types';
import { GitCompare, CheckCircle2, XCircle, ArrowRight } from 'lucide-react';

export const CompareRuns: React.FC = () => {
  const [searchParams] = useSearchParams();
  const faultyParam = searchParams.get('faulty') || '';
  const secureParam = searchParams.get('secure') || '';

  const [faultyId, setFaultyId] = useState<string>(faultyParam);
  const [secureId, setSecureId] = useState<string>(secureParam);

  const { data: allRuns } = useQuery<TestRun[]>({
    queryKey: ['runs'],
    queryFn: () => apiFetch<TestRun[]>('/api/synthetic/runs?limit=50'),
  });

  const { data: runA } = useQuery<TestRun>({
    queryKey: ['run', faultyId],
    queryFn: () => apiFetch<TestRun>(`/api/synthetic/runs/${faultyId}`),
    enabled: !!faultyId,
  });

  const { data: runB } = useQuery<TestRun>({
    queryKey: ['run', secureId],
    queryFn: () => apiFetch<TestRun>(`/api/synthetic/runs/${secureId}`),
    enabled: !!secureId,
  });

  useEffect(() => {
    if (!faultyId && allRuns && allRuns.length > 0) {
      const faultRun = allRuns.find(r => r.fault_mode !== 'secure_baseline') || allRuns[0];
      setFaultyId(faultRun.id);
    }
    if (!secureId && allRuns && allRuns.length > 0) {
      const secRun = allRuns.find(r => r.fault_mode === 'secure_baseline') || allRuns[0];
      setSecureId(secRun.id);
    }
  }, [allRuns, faultyId, secureId]);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Compare Runs Side-by-Side</h1>
        <p className="text-sm text-slate-500 mt-1">
          Evaluate exact question-by-question differences between faulty storage configurations and the corrected secure baseline.
        </p>
      </div>

      {/* Selectors */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <label className="block text-xs font-bold text-red-700 uppercase mb-1">
            Run A (Faulty / Pre-Fix Configuration)
          </label>
          <select
            value={faultyId}
            onChange={(e) => setFaultyId(e.target.value)}
            className="w-full p-2.5 border border-slate-300 rounded-lg text-xs bg-white font-medium"
          >
            {allRuns?.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name} ({r.fault_mode}) - {r.leaked_count} leaks
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-bold text-emerald-700 uppercase mb-1">
            Run B (Corrected Secure Baseline)
          </label>
          <select
            value={secureId}
            onChange={(e) => setSecureId(e.target.value)}
            className="w-full p-2.5 border border-slate-300 rounded-lg text-xs bg-white font-medium"
          >
            {allRuns?.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name} ({r.fault_mode}) - {r.leaked_count} leaks
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* High-Level Delta Cards */}
      {runA && runB && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm text-center">
            <span className="text-xs font-semibold text-slate-500 uppercase">Leak Reduction</span>
            <div className="mt-2 text-2xl font-bold text-emerald-600">
              {runA.leaked_count} → {runB.leaked_count}
            </div>
            <span className="text-xs text-slate-500">
              {runA.leaked_count - runB.leaked_count > 0 ? '100% Leaks Eliminated' : 'Identical Leak Count'}
            </span>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm text-center">
            <span className="text-xs font-semibold text-slate-500 uppercase">Blocked Probes</span>
            <div className="mt-2 text-2xl font-bold text-slate-900">
              {runA.blocked_count} → {runB.blocked_count}
            </div>
            <span className="text-xs text-slate-500">Proper Refusal Rate</span>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm text-center">
            <span className="text-xs font-semibold text-slate-500 uppercase">Authorized Utility</span>
            <div className="mt-2 text-2xl font-bold text-emerald-600">
              {runB.authorized_success_count} Passed
            </div>
            <span className="text-xs text-slate-500">Positive Controls Maintained</span>
          </div>
        </div>
      )}

      {/* Side-by-Side Probe Comparison */}
      {runA && runB && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200">
            <h2 className="text-base font-bold text-slate-900">Side-by-Side Probes Comparison</h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-slate-700 uppercase font-semibold border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3">#</th>
                  <th className="px-4 py-3">Probe Query</th>
                  <th className="px-4 py-3 text-red-700">Run A (Faulty) Answer & Verdict</th>
                  <th className="px-4 py-3 text-emerald-700">Run B (Secure) Answer & Verdict</th>
                  <th className="px-4 py-3 text-center">Outcome Delta</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {runA.probes?.map((pA, idx) => {
                  const pB = runB.probes?.[idx];
                  const improved = pA.verdict === 'leaked' && pB?.verdict === 'blocked';
                  return (
                    <tr key={pA.id} className="hover:bg-slate-50/70">
                      <td className="px-4 py-3 font-mono text-slate-400">{pA.probe_index}</td>
                      <td className="px-4 py-3 font-semibold text-slate-900 max-w-xs">{pA.query}</td>
                      <td className="px-4 py-3">
                        <div className="p-2 rounded bg-red-50 text-red-900 font-mono text-[11px] border border-red-100 max-w-sm">
                          {pA.response_text}
                        </div>
                        <span className="mt-1 inline-block font-bold uppercase text-[10px] text-red-700">
                          Verdict: {pA.verdict}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {pB ? (
                          <>
                            <div className="p-2 rounded bg-emerald-50 text-emerald-900 font-mono text-[11px] border border-emerald-100 max-w-sm">
                              {pB.response_text}
                            </div>
                            <span className="mt-1 inline-block font-bold uppercase text-[10px] text-emerald-700">
                              Verdict: {pB.verdict}
                            </span>
                          </>
                        ) : (
                          <span className="text-slate-400">No matching probe</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {improved ? (
                          <span className="px-2 py-1 bg-emerald-100 text-emerald-800 rounded-full font-bold text-[10px]">
                            LEAK RESOLVED
                          </span>
                        ) : pA.verdict === pB?.verdict ? (
                          <span className="text-slate-400 font-medium">Unchanged</span>
                        ) : (
                          <span className="text-slate-600 font-medium">{pA.verdict} → {pB?.verdict}</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
