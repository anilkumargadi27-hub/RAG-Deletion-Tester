import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../api/client';
import { TestRun } from '../types';
import { FileDown, FileText, CheckCircle2, ShieldCheck, AlertCircle } from 'lucide-react';

export const Reports: React.FC = () => {
  const { data: runs, isLoading } = useQuery<TestRun[]>({
    queryKey: ['runs'],
    queryFn: () => apiFetch<TestRun[]>('/api/synthetic/runs?limit=100'),
  });

  const completedRuns = runs?.filter(r => r.status === 'completed') || [];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Audit Reports & Exports</h1>
        <p className="text-sm text-slate-500 mt-1">
          Export formal compliance reports and raw evidence in PDF, CSV, and JSON formats.
        </p>
      </div>

      <div className="bg-brand-50 border border-brand-200 rounded-2xl p-5 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-brand-600 shrink-0 mt-0.5" />
        <div className="text-xs text-brand-900 space-y-1">
          <h4 className="font-bold text-sm">Audit Compliance Guarantee & Boundary</h4>
          <p>
            Reports generated here include complete run metadata, evaluated probe verdicts, evidence spans, and
            storage attribution traces. CSV exports include strict formula-injection escaping (cell prefixes <code>=, +, -, @</code>).
            PDF reports strictly adhere to the product boundary standard: <em>"No leakage observed in these tests"</em>, never <em>"Guaranteed secure"</em>.
          </p>
        </div>
      </div>

      {/* Reports Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center">
          <h2 className="text-base font-bold text-slate-900">Completed Test Audits ({completedRuns.length})</h2>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-sm text-slate-400">Loading audit reports...</div>
        ) : completedRuns.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">
            No completed runs yet. Run a test suite or guided demo to generate exportable reports.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 text-xs font-semibold text-slate-700 uppercase border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3">Audit Run Name</th>
                  <th className="px-6 py-3">Fault Mode</th>
                  <th className="px-6 py-3">Probes</th>
                  <th className="px-6 py-3">Observed Leaks</th>
                  <th className="px-6 py-3">Completion Date</th>
                  <th className="px-6 py-3 text-right">Available Downloads</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-xs">
                {completedRuns.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/80">
                    <td className="px-6 py-4 font-semibold text-slate-900">
                      {r.name}
                      {r.is_guided_demo && (
                        <span className="ml-2 px-1.5 py-0.5 text-[10px] bg-amber-100 text-amber-800 rounded font-semibold">
                          Demo
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 font-mono capitalize text-slate-700">
                      {r.fault_mode.replace('_', ' ')}
                    </td>
                    <td className="px-6 py-4">{r.completed_probes} probes</td>
                    <td className="px-6 py-4 font-bold">
                      {r.leaked_count > 0 ? (
                        <span className="text-red-600">{r.leaked_count} leaks</span>
                      ) : (
                        <span className="text-emerald-600">0 leaks (Passed)</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-slate-400">
                      {r.completed_at ? new Date(r.completed_at).toLocaleString() : 'N/A'}
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <a
                        href={`/api/reports/${r.id}/json`}
                        download
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg text-xs"
                      >
                        <FileDown className="w-3.5 h-3.5" />
                        <span>JSON</span>
                      </a>
                      <a
                        href={`/api/reports/${r.id}/csv`}
                        download
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg text-xs"
                      >
                        <FileDown className="w-3.5 h-3.5" />
                        <span>CSV</span>
                      </a>
                      <a
                        href={`/api/reports/${r.id}/pdf`}
                        download
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white font-semibold rounded-lg text-xs shadow-xs"
                      >
                        <FileDown className="w-3.5 h-3.5" />
                        <span>Formal PDF</span>
                      </a>
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
