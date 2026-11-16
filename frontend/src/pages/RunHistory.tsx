import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { apiFetch } from '../api/client';
import { TestRun } from '../types';
import { History, ArrowUpRight, Search, Filter } from 'lucide-react';

export const RunHistory: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const { data: runs, isLoading } = useQuery<TestRun[]>({
    queryKey: ['runs'],
    queryFn: () => apiFetch<TestRun[]>('/api/synthetic/runs?limit=100'),
    refetchInterval: 3000,
  });

  const filteredRuns = runs?.filter((r) => {
    const matchesStatus = statusFilter === 'all' || r.status === statusFilter;
    const matchesSearch =
      r.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.fault_mode.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Test Run History</h1>
          <p className="text-sm text-slate-500 mt-1">
            Persisted synthetic experiment runs, leak verdicts, and evidence traces.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/compare"
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors"
          >
            Compare Runs
          </Link>
          <Link
            to="/lab"
            className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors"
          >
            New Synthetic Run
          </Link>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row gap-3">
        <div className="flex-1 relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by run name or fault mode..."
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs border border-slate-200 rounded-lg p-2 bg-white"
          >
            <option value="all">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="running">Running</option>
            <option value="queued">Queued</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      {/* Runs Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-sm text-slate-400">Loading test runs...</div>
        ) : !filteredRuns || filteredRuns.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">
            No test runs matching criteria.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 text-xs font-semibold text-slate-700 uppercase border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3">Run Name</th>
                  <th className="px-6 py-3">Fault Mode</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Leaks</th>
                  <th className="px-6 py-3">Blocked</th>
                  <th className="px-6 py-3">Success Controls</th>
                  <th className="px-6 py-3">Avg Latency</th>
                  <th className="px-6 py-3">Date</th>
                  <th className="px-6 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-xs">
                {filteredRuns.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/80">
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
                    <td className="px-6 py-4 font-mono capitalize">
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
                        <span className="text-red-600">{r.leaked_count}</span>
                      ) : (
                        <span className="text-emerald-600">0</span>
                      )}
                    </td>
                    <td className="px-6 py-4">{r.blocked_count}</td>
                    <td className="px-6 py-4 text-emerald-600 font-semibold">{r.authorized_success_count}</td>
                    <td className="px-6 py-4 text-slate-500">{r.latency_avg_ms} ms</td>
                    <td className="px-6 py-4 text-slate-400">
                      {new Date(r.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        to={`/runs/${r.id}`}
                        className="text-brand-600 hover:text-brand-700 font-semibold inline-flex items-center gap-1"
                      >
                        Details
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
