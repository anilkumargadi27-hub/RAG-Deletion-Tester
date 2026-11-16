import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../api/client';
import { TestRun, ProbeResult, TraceEntry } from '../types';
import {
  ShieldAlert, ShieldCheck, Clock, CheckCircle2,
  XCircle, AlertCircle, FileDown, ArrowLeft, RefreshCw, Bookmark,
  Layers, Database, MessageSquare, ChevronDown, ChevronRight, X
} from 'lucide-react';

export const RunDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [selectedProbe, setSelectedProbe] = useState<ProbeResult | null>(null);
  const [replayLayer, setReplayLayer] = useState<string>('vector_store');
  const [replayResult, setReplayResult] = useState<any>(null);
  const [replayLoading, setReplayLoading] = useState<boolean>(false);
  const [activeTraceDetails, setActiveTraceDetails] = useState<TraceEntry | null>(null);

  const { data: run, isLoading } = useQuery<TestRun>({
    queryKey: ['run', id],
    queryFn: () => apiFetch<TestRun>(`/api/synthetic/runs/${id}`),
    refetchInterval: (data) => (data?.state?.data?.status === 'running' || data?.state?.data?.status === 'queued' ? 1500 : false),
  });

  const saveRegressionMutation = useMutation({
    mutationFn: (probeId: string) =>
      apiFetch('/api/synthetic/regression', {
        method: 'POST',
        body: JSON.stringify({ probe_id: probeId }),
      }),
    onSuccess: () => alert('Successfully saved as regression case!'),
    onError: (err: any) => alert(err.message),
  });

  const handleReplay = async (probeId: string) => {
    setReplayLoading(true);
    setReplayResult(null);
    try {
      const res = await apiFetch('/api/synthetic/replay', {
        method: 'POST',
        body: JSON.stringify({
          probe_id: probeId,
          suppress_layer: replayLayer,
        }),
      });
      setReplayResult(res);
    } catch (err: any) {
      alert(`Replay failed: ${err.message}`);
    } finally {
      setReplayLoading(false);
    }
  };

  if (isLoading) {
    return <div className="p-8 text-center text-slate-500">Loading run details...</div>;
  }

  if (!run) {
    return <div className="p-8 text-center text-red-500">Run not found.</div>;
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header & Metadata */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <Link to="/runs" className="text-xs font-semibold text-slate-500 hover:text-slate-800 flex items-center gap-1 mb-2">
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Run History</span>
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900">{run.name}</h1>
            <span className={`px-2.5 py-0.5 text-xs font-bold rounded-full uppercase ${
              run.status === 'completed'
                ? 'bg-emerald-100 text-emerald-800'
                : run.status === 'running'
                ? 'bg-brand-100 text-brand-800 animate-pulse'
                : 'bg-red-100 text-red-800'
            }`}>
              {run.status}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1 font-mono">Run ID: {run.id}</p>
        </div>

        {/* Report Download Actions */}
        <div className="flex items-center gap-2">
          <a
            href={`/api/reports/${run.id}/json`}
            download
            className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg flex items-center gap-1.5"
          >
            <FileDown className="w-3.5 h-3.5" />
            <span>JSON</span>
          </a>
          <a
            href={`/api/reports/${run.id}/csv`}
            download
            className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg flex items-center gap-1.5"
          >
            <FileDown className="w-3.5 h-3.5" />
            <span>CSV</span>
          </a>
          <a
            href={`/api/reports/${run.id}/pdf`}
            download
            className="px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold rounded-lg shadow-sm flex items-center gap-1.5"
          >
            <FileDown className="w-3.5 h-3.5" />
            <span>PDF Audit Report</span>
          </a>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs text-slate-500 font-semibold uppercase">Fault Mode</span>
          <div className="mt-1 font-bold text-slate-900 capitalize text-sm">{run.fault_mode.replace('_', ' ')}</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs text-slate-500 font-semibold uppercase">Leaks Observed</span>
          <div className={`mt-1 font-bold text-lg ${run.leaked_count > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
            {run.leaked_count} Leaks
          </div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs text-slate-500 font-semibold uppercase">Blocked Probes</span>
          <div className="mt-1 font-bold text-slate-900 text-lg">{run.blocked_count} Blocked</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs text-slate-500 font-semibold uppercase">Positive Controls</span>
          <div className="mt-1 font-bold text-emerald-600 text-lg">{run.authorized_success_count} Passed</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs text-slate-500 font-semibold uppercase">Detector Precision</span>
          <div className="mt-1 font-bold text-slate-900 text-lg">
            {run.detector_precision !== null && run.detector_precision !== undefined
              ? `${(run.detector_precision * 100).toFixed(0)}%`
              : 'N/A'}
          </div>
        </div>
      </div>

      {/* Probes & Evidence Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900">
            Probe Evidence & Interactive Trace Explorer ({run.probes?.length || 0})
          </h2>
          <span className="text-xs text-slate-500">Click any probe to inspect storage traces and test controlled replay</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600">
            <thead className="bg-slate-50 text-xs font-semibold text-slate-700 uppercase border-b border-slate-200">
              <tr>
                <th className="px-4 py-3">#</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Target Principal</th>
                <th className="px-4 py-3">Query</th>
                <th className="px-4 py-3">Verdict</th>
                <th className="px-4 py-3">Evidence Span</th>
                <th className="px-4 py-3">Contributed Layers</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-xs">
              {run.probes?.map((p) => {
                const isLeaked = p.verdict === 'leaked';
                return (
                  <tr
                    key={p.id}
                    onClick={() => { setSelectedProbe(p); setReplayResult(null); }}
                    className={`cursor-pointer hover:bg-slate-50/90 transition-colors ${
                      selectedProbe?.id === p.id ? 'bg-brand-50/50' : isLeaked ? 'bg-red-50/20' : ''
                    }`}
                  >
                    <td className="px-4 py-3 font-mono text-slate-400">{p.probe_index}</td>
                    <td className="px-4 py-3 capitalize font-semibold">{p.probe_type.replace('_', ' ')}</td>
                    <td className="px-4 py-3 font-mono text-[11px] text-slate-800">{p.target_principal}</td>
                    <td className="px-4 py-3 text-slate-900 font-medium max-w-xs truncate">{p.query}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded font-bold text-[10px] uppercase ${
                        isLeaked
                          ? 'bg-red-100 text-red-800'
                          : p.verdict === 'authorized_success'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-slate-100 text-slate-800'
                      }`}>
                        {p.verdict}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px] text-slate-700 truncate max-w-xs">
                      {p.evidence_span || '-'}
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px]">
                      {p.storage_contributed.length > 0 ? (
                        <span className="text-red-700 font-semibold">{p.storage_contributed.join(', ')}</span>
                      ) : (
                        <span className="text-slate-400">None (Blocked)</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedProbe(p);
                        }}
                        className="text-xs font-semibold text-brand-600 hover:text-brand-800"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Selected Probe Detail & Interactive Trace Explorer */}
      {selectedProbe && (
        <div className="bg-white rounded-2xl border border-brand-200 p-6 shadow-md space-y-6">
          <div className="flex justify-between items-start border-b border-slate-200 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-brand-600">
                  Probe #{selectedProbe.probe_index} Details
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                  selectedProbe.verdict === 'leaked' ? 'bg-red-100 text-red-800' : 'bg-emerald-100 text-emerald-800'
                }`}>
                  {selectedProbe.verdict}
                </span>
              </div>
              <h3 className="text-lg font-bold text-slate-900 mt-1">{selectedProbe.query}</h3>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => saveRegressionMutation.mutate(selectedProbe.id)}
                className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5"
              >
                <Bookmark className="w-3.5 h-3.5" />
                <span>Save as Regression Case</span>
              </button>
              <button onClick={() => setSelectedProbe(null)} className="p-1 text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
            {/* Response Content */}
            <div className="space-y-3">
              <h4 className="font-bold text-slate-700 uppercase">Actual Assistant Response</h4>
              <div className="p-3 bg-slate-50 text-slate-900 rounded-xl font-mono border border-slate-200 whitespace-pre-wrap">
                {selectedProbe.response_text}
              </div>

              {selectedProbe.detected_fact && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-xl">
                  <span className="font-bold text-red-800 block">Detected Protected Fact:</span>
                  <span className="font-mono text-red-900">{selectedProbe.detected_fact}</span>
                </div>
              )}
            </div>

            {/* Controlled Replay Verification */}
            <div className="space-y-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
              <h4 className="font-bold text-slate-800 uppercase flex items-center gap-1.5">
                <RefreshCw className="w-4 h-4 text-brand-600" />
                <span>Verify Suspected Source (Controlled Replay)</span>
              </h4>
              <p className="text-slate-600 text-[11px]">
                Replay this probe with a storage layer suppressed to verify whether it eliminates the leakage.
              </p>

              <div className="flex gap-2">
                <select
                  value={replayLayer}
                  onChange={(e) => setReplayLayer(e.target.value)}
                  className="p-2 border border-slate-300 rounded-lg text-xs bg-white font-medium"
                >
                  <option value="vector_store">Suppress Vector Retrieval</option>
                  <option value="cache">Suppress Answer Cache</option>
                  <option value="conversation_memory">Suppress Conversation Memory</option>
                </select>
                <button
                  onClick={() => handleReplay(selectedProbe.id)}
                  disabled={replayLoading}
                  className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-xs disabled:opacity-50"
                >
                  {replayLoading ? 'Replaying...' : 'Replay Probe'}
                </button>
              </div>

              {replayResult && (
                <div className="p-3 bg-white rounded-lg border border-slate-200 mt-2 space-y-2">
                  <div className="flex justify-between items-center text-xs">
                    <span>Original: <strong className="uppercase">{replayResult.original_verdict}</strong></span>
                    <span>Replayed: <strong className="uppercase text-emerald-600">{replayResult.replayed_verdict}</strong></span>
                  </div>
                  <p className="text-[11px] font-semibold text-brand-800 bg-brand-50 p-2 rounded">
                    {replayResult.attribution_conclusion}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Clickable Trace Entries */}
          <div>
            <h4 className="font-bold text-slate-700 uppercase text-xs mb-3">
              Storage & Execution Traces ({selectedProbe.traces.length})
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {selectedProbe.traces.map((t) => (
                <div
                  key={t.id}
                  onClick={() => setActiveTraceDetails(t)}
                  className={`p-3 rounded-xl border text-xs cursor-pointer hover:shadow-xs transition-all ${
                    t.status === 'contributed'
                      ? 'border-red-300 bg-red-50/40 text-red-900'
                      : t.status === 'blocked'
                      ? 'border-emerald-300 bg-emerald-50/40 text-emerald-900'
                      : 'border-slate-200 bg-slate-50 text-slate-700'
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <span className="font-bold capitalize">{t.layer}</span>
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase bg-white/80">
                      {t.status}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1 truncate">{t.step_name}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Trace Details Modal */}
      {activeTraceDetails && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-3">
            <div className="flex justify-between items-center pb-2 border-b border-slate-200">
              <h3 className="font-bold text-slate-900 text-sm">Trace: {activeTraceDetails.step_name}</h3>
              <button onClick={() => setActiveTraceDetails(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="text-xs space-y-2">
              <div><strong>Layer:</strong> {activeTraceDetails.layer}</div>
              <div><strong>Status:</strong> {activeTraceDetails.status}</div>
              <div>
                <strong>Details:</strong>
                <pre className="p-3 bg-slate-900 text-slate-200 rounded-lg text-[11px] font-mono mt-1 overflow-x-auto max-h-48">
                  {JSON.stringify(activeTraceDetails.details, null, 2)}
                </pre>
              </div>
            </div>
            <div className="flex justify-end pt-2">
              <button
                onClick={() => setActiveTraceDetails(null)}
                className="px-4 py-1.5 bg-slate-100 text-slate-700 rounded-lg text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
