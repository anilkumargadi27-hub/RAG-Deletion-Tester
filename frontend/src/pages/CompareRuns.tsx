import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../api/client';
import { TestRun, ProbeResult } from '../types';
import {
  GitCompare,
  CheckCircle2,
  XCircle,
  ArrowRight,
  ArrowLeftRight,
  ShieldCheck,
  AlertTriangle,
  Sparkles,
  Search,
  Filter,
  FlaskConical,
  Play
} from 'lucide-react';

export const CompareRuns: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const faultyParam = searchParams.get('faulty') || '';
  const secureParam = searchParams.get('secure') || '';

  const [faultyId, setFaultyId] = useState<string>(faultyParam);
  const [secureId, setSecureId] = useState<string>(secureParam);
  const [queryFilter, setQueryFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'resolved' | 'unresolved' | 'positive'>('all');
  const [isGeneratingPair, setIsGeneratingPair] = useState<boolean>(false);
  const [generationError, setGenerationError] = useState<string | null>(null);

  const { data: allRuns, isLoading: isLoadingRuns } = useQuery<TestRun[]>({
    queryKey: ['runs'],
    queryFn: () => apiFetch<TestRun[]>('/api/synthetic/runs?limit=50'),
  });

  const { data: runA, isLoading: isLoadingA } = useQuery<TestRun>({
    queryKey: ['run', faultyId],
    queryFn: () => apiFetch<TestRun>(`/api/synthetic/runs/${faultyId}`),
    enabled: !!faultyId,
  });

  const { data: runB, isLoading: isLoadingB } = useQuery<TestRun>({
    queryKey: ['run', secureId],
    queryFn: () => apiFetch<TestRun>(`/api/synthetic/runs/${secureId}`),
    enabled: !!secureId,
  });

  // Auto-select smart defaults if not provided in search params
  useEffect(() => {
    if (!allRuns || allRuns.length === 0) return;

    if (!faultyId || !allRuns.some(r => r.id === faultyId)) {
      // Find first run with leaks or non-secure baseline
      const defaultFaulty = allRuns.find(r => r.leaked_count > 0) ||
                            allRuns.find(r => r.fault_mode !== 'secure_baseline') ||
                            allRuns[0];
      if (defaultFaulty) {
        setFaultyId(defaultFaulty.id);
      }
    }

    if (!secureId || !allRuns.some(r => r.id === secureId)) {
      // Find first secure baseline run
      const defaultSecure = allRuns.find(r => r.fault_mode === 'secure_baseline') ||
                            (allRuns.length > 1 ? allRuns[1] : allRuns[0]);
      if (defaultSecure) {
        setSecureId(defaultSecure.id);
      }
    }
  }, [allRuns, faultyId, secureId]);

  // Synchronize state with URL parameters
  useEffect(() => {
    if (faultyId && secureId) {
      setSearchParams({ faulty: faultyId, secure: secureId }, { replace: true });
    }
  }, [faultyId, secureId, setSearchParams]);

  const handleSwap = () => {
    const temp = faultyId;
    setFaultyId(secureId);
    setSecureId(temp);
  };

  const handleGenerateDemoPair = async () => {
    setIsGeneratingPair(true);
    setGenerationError(null);
    try {
      const res = await apiFetch<{
        faulty_id: string;
        secure_id: string;
        faulty_name: string;
        secure_name: string;
      }>('/api/synthetic/runs/demo-pair', {
        method: 'POST',
      });
      await queryClient.invalidateQueries({ queryKey: ['runs'] });
      setFaultyId(res.faulty_id);
      setSecureId(res.secure_id);
    } catch (err: any) {
      setGenerationError(err?.message || 'Failed to generate demonstration comparison runs.');
    } finally {
      setIsGeneratingPair(false);
    }
  };

  // Group runs for selector optgroups
  const faultyRuns = useMemo(() => {
    return allRuns?.filter(r => r.fault_mode !== 'secure_baseline' || r.leaked_count > 0) || [];
  }, [allRuns]);

  const secureRuns = useMemo(() => {
    return allRuns?.filter(r => r.fault_mode === 'secure_baseline') || [];
  }, [allRuns]);

  // Probe comparison list with smart matching
  const matchedProbes = useMemo(() => {
    if (!runA?.probes) return [];
    return runA.probes.map((pA, idx) => {
      const pB = runB?.probes?.find(
        (p) => p.scenario_key === pA.scenario_key && p.probe_index === pA.probe_index
      ) || runB?.probes?.find((p) => p.query.toLowerCase().trim() === pA.query.toLowerCase().trim())
         || runB?.probes?.[idx];

      const isResolved = pA.verdict === 'leaked' && pB?.verdict === 'blocked';
      const isUnresolved = pA.verdict === 'leaked' && pB?.verdict === 'leaked';
      const isPositive = pA.probe_type === 'positive_control' || pB?.probe_type === 'positive_control';

      return {
        pA,
        pB,
        isResolved,
        isUnresolved,
        isPositive,
      };
    });
  }, [runA, runB]);

  // Filtered probes based on search and status tabs
  const filteredProbes = useMemo(() => {
    return matchedProbes.filter(({ pA, isResolved, isUnresolved, isPositive }) => {
      if (statusFilter === 'resolved' && !isResolved) return false;
      if (statusFilter === 'unresolved' && !isUnresolved) return false;
      if (statusFilter === 'positive' && !isPositive) return false;

      if (queryFilter.trim()) {
        const q = queryFilter.toLowerCase();
        return (
          pA.query.toLowerCase().includes(q) ||
          pA.target_principal.toLowerCase().includes(q) ||
          pA.response_text.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [matchedProbes, statusFilter, queryFilter]);

  const resolvedCount = useMemo(() => matchedProbes.filter(m => m.isResolved).length, [matchedProbes]);
  const unresolvedCount = useMemo(() => matchedProbes.filter(m => m.isUnresolved).length, [matchedProbes]);
  const positiveCount = useMemo(() => matchedProbes.filter(m => m.isPositive).length, [matchedProbes]);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl border border-indigo-100">
              <GitCompare className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Compare Runs Side-by-Side</h1>
              <p className="text-sm text-slate-500">
                Evaluate exact question-by-question differences between faulty storage configurations and the corrected secure baseline.
              </p>
            </div>
          </div>
        </div>

        {allRuns && allRuns.length > 0 && (
          <button
            onClick={handleGenerateDemoPair}
            disabled={isGeneratingPair}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold rounded-xl border border-indigo-200 transition-colors disabled:opacity-60"
            title="Runs a fresh benchmark test pair"
          >
            <Sparkles className={`w-4 h-4 ${isGeneratingPair ? 'animate-spin' : ''}`} />
            {isGeneratingPair ? 'Generating Benchmark Pair...' : 'Run New Demo Comparison Pair'}
          </button>
        )}
      </div>

      {generationError && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0 text-red-600" />
          <span>{generationError}</span>
        </div>
      )}

      {/* Empty State: When no runs exist yet */}
      {!isLoadingRuns && (!allRuns || allRuns.length === 0) && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-12 text-center max-w-2xl mx-auto space-y-6">
          <div className="w-16 h-16 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center mx-auto border border-indigo-100">
            <GitCompare className="w-8 h-8" />
          </div>

          <div className="space-y-2">
            <h2 className="text-xl font-bold text-slate-900">No Test Runs Available for Comparison</h2>
            <p className="text-sm text-slate-500 leading-relaxed">
              Side-by-side comparison evaluates how a corrected secure configuration eliminates information leakage
              compared to a faulty storage profile (stale vector index, stale cache, or stale conversation memory).
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
            <button
              onClick={handleGenerateDemoPair}
              disabled={isGeneratingPair}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm rounded-xl shadow-sm transition-all disabled:opacity-60"
            >
              <Sparkles className={`w-4 h-4 ${isGeneratingPair ? 'animate-spin' : ''}`} />
              {isGeneratingPair ? 'Generating Benchmark Pair...' : '⚡ Generate Demo Comparison Runs Now'}
            </button>

            <Link
              to="/synthetic"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-sm rounded-xl transition-colors"
            >
              <FlaskConical className="w-4 h-4" />
              Open Synthetic Lab
            </Link>
          </div>

          <div className="text-xs text-slate-400 border-t border-slate-100 pt-4">
            Runs will be saved to your local database and can be re-analyzed or exported as PDF audit reports at any time.
          </div>
        </div>
      )}

      {/* When exactly 1 run exists */}
      {!isLoadingRuns && allRuns && allRuns.length === 1 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
            <div className="text-xs text-amber-900">
              <span className="font-bold">1 test run detected.</span> For an effective side-by-side comparison, generate a second run with a contrasting storage configuration.
            </div>
          </div>
          <button
            onClick={handleGenerateDemoPair}
            disabled={isGeneratingPair}
            className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold rounded-lg shadow-sm whitespace-nowrap"
          >
            {isGeneratingPair ? 'Generating...' : 'Generate Secure Baseline'}
          </button>
        </div>
      )}

      {/* Selectors Bar: Visible when at least 1 run is in the database */}
      {allRuns && allRuns.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-11 gap-4 items-center bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          {/* Run A Selector */}
          <div className="lg:col-span-5 space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-1.5 text-xs font-bold text-red-700 uppercase tracking-wide">
                <XCircle className="w-4 h-4" />
                Run A (Faulty / Pre-Fix Configuration)
              </label>
              {runA && (
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-red-100 text-red-800">
                  {runA.leaked_count} leaks detected
                </span>
              )}
            </div>

            <select
              value={faultyId}
              onChange={(e) => setFaultyId(e.target.value)}
              className="w-full p-2.5 border border-red-200 focus:border-red-400 focus:ring-1 focus:ring-red-400 rounded-xl text-xs bg-red-50/20 font-medium text-slate-800 transition-all cursor-pointer"
            >
              <option value="">-- Select Pre-Fix / Faulty Run --</option>
              {faultyRuns.length > 0 && (
                <optgroup label="⚠️ Faulty / Leaking Storage Profiles">
                  {faultyRuns.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} ({r.fault_mode}) — {r.leaked_count} leaks • {r.status}
                    </option>
                  ))}
                </optgroup>
              )}
              {secureRuns.length > 0 && (
                <optgroup label="Other Storage Runs">
                  {secureRuns.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} ({r.fault_mode}) — {r.leaked_count} leaks • {r.status}
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
          </div>

          {/* Swap Button in center */}
          <div className="lg:col-span-1 flex justify-center py-2 lg:py-0">
            <button
              onClick={handleSwap}
              type="button"
              className="p-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl transition-all shadow-sm border border-slate-200"
              title="Swap Run A and Run B"
            >
              <ArrowLeftRight className="w-4 h-4" />
            </button>
          </div>

          {/* Run B Selector */}
          <div className="lg:col-span-5 space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-1.5 text-xs font-bold text-emerald-700 uppercase tracking-wide">
                <CheckCircle2 className="w-4 h-4" />
                Run B (Corrected Secure Baseline)
              </label>
              {runB && (
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                  {runB.leaked_count === 0 ? '0 Leaks (No leakage)' : `${runB.leaked_count} leaks`}
                </span>
              )}
            </div>

            <select
              value={secureId}
              onChange={(e) => setSecureId(e.target.value)}
              className="w-full p-2.5 border border-emerald-200 focus:border-emerald-400 focus:ring-1 focus:ring-emerald-400 rounded-xl text-xs bg-emerald-50/20 font-medium text-slate-800 transition-all cursor-pointer"
            >
              <option value="">-- Select Post-Fix / Secure Baseline --</option>
              {secureRuns.length > 0 && (
                <optgroup label="✅ Corrected Secure Baselines">
                  {secureRuns.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} ({r.fault_mode}) — {r.leaked_count} leaks • {r.status}
                    </option>
                  ))}
                </optgroup>
              )}
              {faultyRuns.length > 0 && (
                <optgroup label="Other Storage Runs">
                  {faultyRuns.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} ({r.fault_mode}) — {r.leaked_count} leaks • {r.status}
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
          </div>
        </div>
      )}

      {/* High-Level Delta Cards */}
      {runA && runB && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Leak Elimination */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Leak Elimination</span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-extrabold text-red-600">{runA.leaked_count}</span>
              <ArrowRight className="w-4 h-4 text-slate-400" />
              <span className="text-2xl font-extrabold text-emerald-600">{runB.leaked_count}</span>
            </div>
            <div className="pt-1">
              {runA.leaked_count > runB.leaked_count ? (
                <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  {runA.leaked_count - runB.leaked_count} Leaks Eliminated
                </span>
              ) : runA.leaked_count === runB.leaked_count ? (
                <span className="text-xs font-medium text-slate-500">Identical leak counts</span>
              ) : (
                <span className="text-xs font-bold text-red-700 bg-red-50 px-2 py-0.5 rounded-md">
                  Regression (+{runB.leaked_count - runA.leaked_count})
                </span>
              )}
            </div>
          </div>

          {/* Card 2: Blocked / Proper Refusals */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Proper Refusals (Blocked)</span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-extrabold text-slate-700">{runA.blocked_count}</span>
              <ArrowRight className="w-4 h-4 text-slate-400" />
              <span className="text-2xl font-extrabold text-slate-900">{runB.blocked_count}</span>
            </div>
            <p className="text-xs text-slate-500">
              Post-mutation queries correctly rejected
            </p>
          </div>

          {/* Card 3: Authorized Utility */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Authorized Utility</span>
            <div className="text-2xl font-extrabold text-indigo-600">
              {runB.authorized_success_count} Passed
            </div>
            <p className="text-xs text-slate-500">
              Positive controls verified answerable
            </p>
          </div>

          {/* Card 4: Engine Profiles */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Storage & Engine Profile</span>
            <div className="space-y-1 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Fault Tested:</span>
                <span className="font-mono font-semibold text-red-700">{runA.fault_mode}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Corrected:</span>
                <span className="font-mono font-semibold text-emerald-700">{runB.fault_mode}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Answer Mode:</span>
                <span className="font-mono text-slate-700">{runB.answer_mode}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Side-by-Side Probe Comparison Table */}
      {runA && runB && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden space-y-4">
          {/* Table Toolbar & Filters */}
          <div className="p-5 border-b border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">Side-by-Side Probes Comparison</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Exact query comparison between pre-fix and corrected response states.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {/* Filter Pills */}
              <div className="flex items-center bg-slate-100 p-1 rounded-xl text-xs font-medium">
                <button
                  onClick={() => setStatusFilter('all')}
                  className={`px-3 py-1 rounded-lg transition-colors ${
                    statusFilter === 'all' ? 'bg-white text-slate-900 shadow-sm font-semibold' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  All ({matchedProbes.length})
                </button>
                <button
                  onClick={() => setStatusFilter('resolved')}
                  className={`px-3 py-1 rounded-lg transition-colors flex items-center gap-1 ${
                    statusFilter === 'resolved' ? 'bg-emerald-600 text-white shadow-sm font-semibold' : 'text-slate-600 hover:text-emerald-700'
                  }`}
                >
                  <ShieldCheck className="w-3 h-3" />
                  Leaks Resolved ({resolvedCount})
                </button>
                {unresolvedCount > 0 && (
                  <button
                    onClick={() => setStatusFilter('unresolved')}
                    className={`px-3 py-1 rounded-lg transition-colors flex items-center gap-1 ${
                      statusFilter === 'unresolved' ? 'bg-red-600 text-white shadow-sm font-semibold' : 'text-slate-600 hover:text-red-700'
                    }`}
                  >
                    <AlertTriangle className="w-3 h-3" />
                    Unresolved ({unresolvedCount})
                  </button>
                )}
                <button
                  onClick={() => setStatusFilter('positive')}
                  className={`px-3 py-1 rounded-lg transition-colors ${
                    statusFilter === 'positive' ? 'bg-indigo-600 text-white shadow-sm font-semibold' : 'text-slate-600 hover:text-indigo-700'
                  }`}
                >
                  Positive ({positiveCount})
                </button>
              </div>

              {/* Search Bar */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Filter queries..."
                  value={queryFilter}
                  onChange={(e) => setQueryFilter(e.target.value)}
                  className="pl-8 pr-3 py-1.5 border border-slate-200 rounded-xl text-xs w-44 focus:w-60 transition-all focus:outline-none focus:border-indigo-400"
                />
              </div>
            </div>
          </div>

          {/* Probes Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-slate-700 uppercase font-semibold border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 w-12">#</th>
                  <th className="px-4 py-3 min-w-[220px]">Probe Query & Principal</th>
                  <th className="px-4 py-3 text-red-700 min-w-[280px]">Run A (Faulty) Response & Verdict</th>
                  <th className="px-4 py-3 text-emerald-700 min-w-[280px]">Run B (Secure) Response & Verdict</th>
                  <th className="px-4 py-3 text-center w-36">Outcome Delta</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredProbes.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center text-slate-400">
                      No probes matching current filter criteria.
                    </td>
                  </tr>
                ) : (
                  filteredProbes.map(({ pA, pB, isResolved, isUnresolved, isPositive }) => (
                    <tr key={pA.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-4 py-3 font-mono text-slate-400">{pA.probe_index}</td>

                      {/* Query & Metadata */}
                      <td className="px-4 py-3 space-y-1">
                        <div className="font-semibold text-slate-900 leading-snug">{pA.query}</div>
                        <div className="flex flex-wrap items-center gap-1">
                          <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 text-[10px] font-mono">
                            {pA.probe_type}
                          </span>
                          <span className="px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 text-[10px] font-mono">
                            {pA.target_principal}
                          </span>
                        </div>
                      </td>

                      {/* Run A Answer */}
                      <td className="px-4 py-3 space-y-1.5">
                        <div className={`p-2.5 rounded-xl font-mono text-[11px] leading-relaxed border ${
                          pA.verdict === 'leaked'
                            ? 'bg-red-50 text-red-950 border-red-200 shadow-sm'
                            : 'bg-slate-50 text-slate-800 border-slate-200'
                        }`}>
                          {pA.response_text}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`inline-flex items-center gap-1 font-bold uppercase text-[10px] px-2 py-0.5 rounded-md ${
                            pA.verdict === 'leaked'
                              ? 'bg-red-100 text-red-800'
                              : pA.verdict === 'blocked'
                              ? 'bg-slate-100 text-slate-700'
                              : 'bg-blue-100 text-blue-800'
                          }`}>
                            {pA.verdict === 'leaked' && <XCircle className="w-3 h-3 text-red-600" />}
                            Verdict: {pA.verdict}
                          </span>
                          {pA.evidence_span && (
                            <span className="text-[10px] text-red-600 font-mono font-medium truncate max-w-[180px]">
                              Canary: {pA.evidence_span}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Run B Answer */}
                      <td className="px-4 py-3 space-y-1.5">
                        {pB ? (
                          <>
                            <div className={`p-2.5 rounded-xl font-mono text-[11px] leading-relaxed border ${
                              pB.verdict === 'blocked'
                                ? 'bg-emerald-50 text-emerald-950 border-emerald-200 shadow-sm'
                                : pB.verdict === 'authorized_success'
                                ? 'bg-blue-50 text-blue-950 border-blue-200'
                                : 'bg-red-50 text-red-950 border-red-200'
                            }`}>
                              {pB.response_text}
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`inline-flex items-center gap-1 font-bold uppercase text-[10px] px-2 py-0.5 rounded-md ${
                                pB.verdict === 'blocked'
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : pB.verdict === 'authorized_success'
                                  ? 'bg-blue-100 text-blue-800'
                                  : 'bg-red-100 text-red-800'
                              }`}>
                                {pB.verdict === 'blocked' && <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
                                Verdict: {pB.verdict}
                              </span>
                              {pB.verdict === 'blocked' && (
                                <span className="text-[10px] text-emerald-700 font-semibold">
                                  Properly Refused
                                </span>
                              )}
                            </div>
                          </>
                        ) : (
                          <span className="text-slate-400 italic">No matching probe in Run B</span>
                        )}
                      </td>

                      {/* Outcome Delta */}
                      <td className="px-4 py-3 text-center align-middle">
                        {isResolved ? (
                          <div className="inline-flex flex-col items-center gap-1">
                            <span className="px-2.5 py-1 bg-emerald-100 text-emerald-800 border border-emerald-200 rounded-full font-bold text-[10px] shadow-sm flex items-center gap-1">
                              <ShieldCheck className="w-3 h-3 text-emerald-600" />
                              LEAK ELIMINATED
                            </span>
                            <span className="text-[10px] text-emerald-600 font-medium">Safe baseline active</span>
                          </div>
                        ) : isPositive ? (
                          <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full font-semibold text-[10px]">
                            AUTHORIZED PASS
                          </span>
                        ) : isUnresolved ? (
                          <span className="px-2 py-1 bg-red-100 text-red-800 rounded-full font-bold text-[10px]">
                            LEAK PERSISTS
                          </span>
                        ) : pA.verdict === pB?.verdict ? (
                          <span className="px-2 py-1 bg-slate-100 text-slate-600 rounded-full font-medium text-[10px]">
                            Clean ({pA.verdict})
                          </span>
                        ) : (
                          <span className="text-slate-600 font-medium text-[10px]">
                            {pA.verdict} → {pB?.verdict}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};