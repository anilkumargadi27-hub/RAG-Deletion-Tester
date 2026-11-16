import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiFetch } from '../api/client';
import { Scenario, TestRun } from '../types';
import { SyntheticLabBanner } from '../components/SyntheticLabBanner';
import {
  FlaskConical, PlayCircle, ShieldCheck, Database,
  Layers, MessageSquare, AlertTriangle, ArrowRight
} from 'lucide-react';

export const SyntheticLab: React.FC = () => {
  const [faultMode, setFaultMode] = useState<string>('secure_baseline');
  const [answerMode, setAnswerMode] = useState<string>('local_extractive');
  const [retrievalMode, setRetrievalMode] = useState<string>('semantic_vector');
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  const { data: scenarios, isLoading } = useQuery<Scenario[]>({
    queryKey: ['scenarios'],
    queryFn: () => apiFetch<Scenario[]>('/api/synthetic/scenarios'),
  });

  const launchRun = async () => {
    setSubmitting(true);
    try {
      const run = await apiFetch<TestRun>('/api/synthetic/runs', {
        method: 'POST',
        body: JSON.stringify({
          name: `Synthetic Lab - ${faultMode.replace('_', ' ')}`,
          fault_mode: faultMode,
          answer_mode: answerMode,
          retrieval_mode: retrievalMode,
          is_guided_demo: false,
        }),
      });
      navigate(`/runs/${run.id}`);
    } catch (err: any) {
      alert(err.message || 'Failed to start run');
    } finally {
      setSubmitting(false);
    }
  };

  const faultProfiles = [
    {
      id: 'secure_baseline',
      name: 'Secure Baseline',
      desc: 'All storage layers (vector store, cache, memory) authoritatively revalidated against DB tombstones.',
      icon: ShieldCheck,
      color: 'border-emerald-300 text-emerald-800 bg-emerald-50/50',
    },
    {
      id: 'stale_index',
      name: 'Stale Vector Index',
      desc: 'Simulates unpurged vector chunk retention after document deletion; exercises retrieval filter leaks.',
      icon: Database,
      color: 'border-amber-300 text-amber-800 bg-amber-50/50',
    },
    {
      id: 'stale_cache',
      name: 'Stale Answer Cache',
      desc: 'Simulates missing cache invalidation; serves cached pre-mutation answer without dependency checks.',
      icon: Layers,
      color: 'border-blue-300 text-blue-800 bg-blue-50/50',
    },
    {
      id: 'stale_memory',
      name: 'Stale Conversation Memory',
      desc: 'Simulates unpruned multi-turn chat history; tests retained assistant responses in active sessions.',
      icon: MessageSquare,
      color: 'border-purple-300 text-purple-800 bg-purple-50/50',
    },
    {
      id: 'combined_stale',
      name: 'Combined Stale Copies',
      desc: 'Simulates multiple uncoordinated failures across index, cache, and memory simultaneously.',
      icon: AlertTriangle,
      color: 'border-red-300 text-red-800 bg-red-50/50',
    },
  ];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Synthetic Testing Laboratory</h1>
            <p className="text-sm text-slate-500 mt-1">
              Configure fault profiles and evaluate RAG retention across 20 synthetic scenarios.
            </p>
          </div>
          <button
            onClick={() => navigate('/demo')}
            className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg"
          >
            <PlayCircle className="w-4 h-4 text-brand-600" />
            <span>Launch Guided Demo</span>
          </button>
        </div>
      </div>

      <SyntheticLabBanner />

      {/* Fault Profile Selector */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-6">
        <div>
          <h2 className="text-base font-bold text-slate-900">1. Select Storage Fault Profile</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Choose which storage layer invalidation to test. Ordinary documents always use Secure Baseline.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {faultProfiles.map((p) => {
            const Icon = p.icon;
            const isSelected = faultMode === p.id;
            return (
              <div
                key={p.id}
                onClick={() => setFaultMode(p.id)}
                className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                  isSelected ? 'border-brand-600 bg-brand-50/40 shadow-sm' : 'border-slate-200 hover:border-slate-300 bg-white'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <div className={`p-2 rounded-lg border ${p.color}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="font-bold text-sm text-slate-900">{p.name}</span>
                </div>
                <p className="text-xs text-slate-600 mt-2 leading-relaxed">{p.desc}</p>
              </div>
            );
          })}
        </div>

        {/* Answer & Retrieval Mode Selection */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 border-t border-slate-100">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
              Answer Mode
            </label>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => setAnswerMode('local_extractive')}
                className={`p-2.5 rounded-lg border font-semibold text-left ${
                  answerMode === 'local_extractive'
                    ? 'border-brand-600 bg-brand-50 text-brand-900'
                    : 'border-slate-200 text-slate-700 hover:bg-slate-50'
                }`}
              >
                <div>Local Extractive</div>
                <span className="text-[10px] font-normal text-slate-500">Deterministic, no API key</span>
              </button>
              <button
                type="button"
                onClick={() => setAnswerMode('live_gemini')}
                className={`p-2.5 rounded-lg border font-semibold text-left ${
                  answerMode === 'live_gemini'
                    ? 'border-brand-600 bg-brand-50 text-brand-900'
                    : 'border-slate-200 text-slate-700 hover:bg-slate-50'
                }`}
              >
                <div>Live Gemini Mode</div>
                <span className="text-[10px] font-normal text-slate-500">Official SDK with citations</span>
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
              Retrieval Mode
            </label>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => setRetrievalMode('semantic_vector')}
                className={`p-2.5 rounded-lg border font-semibold text-left ${
                  retrievalMode === 'semantic_vector'
                    ? 'border-brand-600 bg-brand-50 text-brand-900'
                    : 'border-slate-200 text-slate-700 hover:bg-slate-50'
                }`}
              >
                <div>Semantic Vector</div>
                <span className="text-[10px] font-normal text-slate-500">Chroma + BGE embeddings</span>
              </button>
              <button
                type="button"
                onClick={() => setRetrievalMode('tfidf_lexical')}
                className={`p-2.5 rounded-lg border font-semibold text-left ${
                  retrievalMode === 'tfidf_lexical'
                    ? 'border-brand-600 bg-brand-50 text-brand-900'
                    : 'border-slate-200 text-slate-700 hover:bg-slate-50'
                }`}
              >
                <div>TF-IDF Lexical</div>
                <span className="text-[10px] font-normal text-slate-500">Deterministic keyword index</span>
              </button>
            </div>
          </div>
        </div>

        <div className="pt-2 flex justify-end">
          <button
            onClick={launchRun}
            disabled={submitting}
            className="flex items-center gap-2 px-6 py-3 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-sm font-semibold shadow-md transition-colors disabled:opacity-50"
          >
            <FlaskConical className="w-4 h-4" />
            <span>{submitting ? 'Queuing Run...' : 'Launch Synthetic Test Suite'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Scenarios Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900">Seeded Synthetic Scenarios (20)</h2>
          <span className="text-xs text-slate-500">Across HR, Finance, Engineering, and Operations</span>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-sm text-slate-400">Loading scenario fixtures...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 text-xs font-semibold text-slate-700 uppercase border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3">Dept</th>
                  <th className="px-6 py-3">Scenario Title</th>
                  <th className="px-6 py-3">Mutation</th>
                  <th className="px-6 py-3">Canary String</th>
                  <th className="px-6 py-3">Protected Fact</th>
                  <th className="px-6 py-3">Positive Control</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-xs">
                {scenarios?.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-50/80">
                    <td className="px-6 py-3 font-semibold text-slate-900">{s.department}</td>
                    <td className="px-6 py-3 font-medium text-slate-800">{s.title}</td>
                    <td className="px-6 py-3">
                      <span className={`px-2 py-0.5 rounded font-semibold text-[10px] uppercase ${
                        s.mutation_type === 'deletion'
                          ? 'bg-rose-100 text-rose-800'
                          : 'bg-purple-100 text-purple-800'
                      }`}>
                        {s.mutation_type}
                      </span>
                    </td>
                    <td className="px-6 py-3 font-mono text-[11px] text-slate-600">{s.canary_string}</td>
                    <td className="px-6 py-3 font-medium text-slate-900">{s.protected_fact}</td>
                    <td className="px-6 py-3 text-slate-500 truncate max-w-xs">{s.positive_control_question}</td>
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
