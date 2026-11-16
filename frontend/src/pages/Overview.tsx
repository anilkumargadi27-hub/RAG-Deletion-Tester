import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { apiFetch } from '../api/client';
import { TestRun } from '../types';
import {
  ShieldAlert, ShieldCheck, PlayCircle, History,
  Clock, ArrowUpRight, CheckCircle2, XCircle
} from 'lucide-react';

export const Overview: React.FC = () => {
  const { data: runs, isLoading } = useQuery<TestRun[]>({
    queryKey: ['runs'],
    queryFn: () => apiFetch<TestRun[]>('/api/synthetic/runs?limit=10'),
    refetchInterval: 3000,
  });

  const latestRun = runs && runs.length > 0 ? runs[0] : null;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Hero Header */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-brand-900 rounded-2xl p-8 text-white shadow-md flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/20 text-brand-300 text-xs font-semibold mb-3 border border-brand-400/30">
            <span>RAG Deletion & Access-Revocation Assurance</span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight">
            Check what your AI can still reveal after access changes.
          </h1>
          <p className="mt-2 text-slate-300 text-sm max-w-2xl leading-relaxed">
            Automatically probe your RAG pipeline across vector indexes, answer caches, and conversation memory
            to verify that deleted documents and revoked permissions never leak restricted facts into newly returned responses.
          </p>
        </div>

        <div className="flex flex-wrap gap-3 shrink-0">
          <Link
            to="/demo"
            className="flex items-center gap-2 px-4 py-2.5 bg-brand-500 hover:bg-brand-600 text-white rounded-xl text-sm font-semibold shadow-sm transition-colors"
          >
            <PlayCircle className="w-4 h-4" />
            <span>Run Guided Demo</span>
          </Link>
          <Link
            to="/lab"
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-sm font-semibold border border-slate-700 transition-colors"
          >
            <span>Open Synthetic Lab</span>
          </Link>
        </div>
      </div>

      {/* Metrics Row */}
      {latestRun ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider">
              <span>Latest Run Mode</span>
              <ShieldAlert className="w-4 h-4 text-brand-600" />
            </div>
            <div className="mt-2 text-xl font-bold text-slate-900 capitalize">
              {latestRun.fault_mode.replace('_', ' ')}
            </div>
            <span className="text-xs text-slate-500 capitalize">Status: {latestRun.status}</span>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider">
              <span>Observed Leaks</span>
              <XCircle className="w-4 h-4 text-red-500" />
            </div>
            <div className={`mt-2 text-2xl font-bold ${latestRun.leaked_count > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
              {latestRun.leaked_count}
            </div>
            <span className="text-xs text-slate-500">{latestRun.blocked_count} Probes Safely Blocked</span>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider">
              <span>Authorized Controls</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            </div>
            <div className="mt-2 text-2xl font-bold text-emerald-600">
              {latestRun.authorized_success_count} Passed
            </div>
            <span className="text-xs text-slate-500">Positive Controls Answered</span>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider">
              <span>Avg Latency</span>
              <Clock className="w-4 h-4 text-slate-400" />
            </div>
            <div className="mt-2 text-2xl font-bold text-slate-900">
              {latestRun.latency_avg_ms} ms
            </div>
            <span className="text-xs text-slate-500">{latestRun.answer_mode}</span>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500 shadow-sm">
          <ShieldCheck className="w-10 h-10 mx-auto text-brand-500 mb-2" />
          <h3 className="text-base font-semibold text-slate-900">No test runs executed yet</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
            Launch a guided demo or run a synthetic test suite to verify whether retained storage copies expose restricted facts.
          </p>
          <div className="mt-4">
            <Link
              to="/demo"
              className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-semibold hover:bg-brand-700"
            >
              <PlayCircle className="w-4 h-4" />
              <span>Launch First Guided Demo</span>
            </Link>
          </div>
        </div>
      )}

      {/* Recent Activity Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-slate-500" />
            <h2 className="text-base font-bold text-slate-900">Recent Test Runs</h2>
          </div>
          <Link to="/runs" className="text-xs font-semibold text-brand-600 hover:text-brand-700 flex items-center gap-1">
            <span>View All Runs</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-sm text-slate-400">Loading runs...</div>
        ) : !runs || runs.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">
            No test runs on record. Click "Run Guided Demo" above to start.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 text-xs font-semibold text-slate-700 uppercase border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3">Run Name</th>
                  <th className="px-6 py-3">Fault Mode</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Leaks Detected</th>
                  <th className="px-6 py-3">Blocked Probes</th>
                  <th className="px-6 py-3">Created</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {runs.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-6 py-4 font-semibold text-slate-900">
                      <Link to={`/runs/${r.id}`} className="hover:text-brand-600">
                        {r.name}
                      </Link>
                      {r.is_guided_demo && (
                        <span className="ml-2 px-1.5 py-0.5 text-[10px] bg-amber-100 text-amber-800 rounded font-semibold">
                          Demo
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-slate-700 capitalize">
                      {r.fault_mode.replace('_', ' ')}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
                        r.status === 'completed'
                          ? 'bg-emerald-100 text-emerald-800'
                          : r.status === 'running'
                          ? 'bg-brand-100 text-brand-800 animate-pulse'
                          : r.status === 'queued'
                          ? 'bg-slate-100 text-slate-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {r.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-bold">
                      {r.leaked_count > 0 ? (
                        <span className="text-red-600">{r.leaked_count} leaks</span>
                      ) : (
                        <span className="text-emerald-600">0 leaks</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-slate-700">{r.blocked_count}</td>
                    <td className="px-6 py-4 text-xs text-slate-500">
                      {new Date(r.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        to={`/runs/${r.id}`}
                        className="text-brand-600 hover:text-brand-700 font-semibold text-xs inline-flex items-center gap-1"
                      >
                        Inspect Traces
                        <ArrowUpRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
