import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../api/client';
import { Diagnostics, User } from '../types';
import {
  Settings, Server, Database, Activity, Sparkles,
  Users, Trash2, CheckCircle2, AlertCircle, RefreshCw
} from 'lucide-react';

export const AdminSettings: React.FC = () => {
  const queryClient = useQueryClient();
  const [newUsername, setNewUsername] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState('auditor');
  const [userError, setUserError] = useState<string | null>(null);

  const [geminiResult, setGeminiResult] = useState<any>(null);
  const [geminiLoading, setGeminiLoading] = useState(false);

  const { data: diag, isLoading: diagLoading } = useQuery<Diagnostics>({
    queryKey: ['diagnostics'],
    queryFn: () => apiFetch<Diagnostics>('/api/admin/diagnostics'),
  });

  const { data: users, isLoading: usersLoading } = useQuery<User[]>({
    queryKey: ['users'],
    queryFn: () => apiFetch<User[]>('/api/auth/users'),
  });

  const createUserMutation = useMutation({
    mutationFn: () =>
      apiFetch('/api/auth/users', {
        method: 'POST',
        body: JSON.stringify({
          username: newUsername,
          email: newEmail,
          password: newPassword,
          role: newRole,
        }),
      }),
    onSuccess: () => {
      setNewUsername('');
      setNewEmail('');
      setNewPassword('');
      setUserError(null);
      queryClient.invalidateQueries({ queryKey: ['users'] });
      alert('User created successfully!');
    },
    onError: (err: any) => setUserError(err.message),
  });

  const testGeminiConnection = async () => {
    setGeminiLoading(true);
    setGeminiResult(null);
    try {
      const res = await apiFetch('/api/admin/test-gemini', { method: 'POST' });
      setGeminiResult(res);
    } catch (err: any) {
      setGeminiResult({ status: 'error', message: err.message });
    } finally {
      setGeminiLoading(false);
    }
  };

  const resetSyntheticData = async () => {
    if (confirm('Are you sure you want to reset all synthetic test runs and probe evidence? Production documents will remain untouched.')) {
      try {
        await apiFetch('/api/admin/reset-synthetic', { method: 'POST' });
        queryClient.invalidateQueries();
        alert('Synthetic test runs reset successfully.');
      } catch (err: any) {
        alert(err.message);
      }
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Admin Diagnostics & Settings</h1>
        <p className="text-sm text-slate-500 mt-1">
          System infrastructure health, vector store state, AI provider status, and user account management.
        </p>
      </div>

      {/* Diagnostics Cards */}
      {diagLoading ? (
        <div className="p-8 text-center text-sm text-slate-400">Loading system diagnostics...</div>
      ) : diag ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {/* Database Info */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase">SQLite Database</span>
              <Database className="w-4 h-4 text-brand-600" />
            </div>
            <div className="text-2xl font-bold text-slate-900">
              {diag.database.total_documents} Documents
            </div>
            <div className="text-xs text-slate-500 space-y-1">
              <div>Tombstoned: <strong>{diag.database.tombstoned_documents}</strong></div>
              <div>Total Chunks: <strong>{diag.database.total_chunks}</strong></div>
              <div>Pending Cleanups: <strong>{diag.database.pending_cleanup_jobs}</strong></div>
            </div>
          </div>

          {/* Vector Store */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase">Chroma Vector Store</span>
              <Server className="w-4 h-4 text-purple-600" />
            </div>
            <div className="text-2xl font-bold text-slate-900">
              {diag.vector_store.production_chunks_count} Chunks
            </div>
            <div className="text-xs text-slate-500 space-y-1">
              <div>Type: <strong>{diag.vector_store.type}</strong></div>
              <div className="truncate">Path: <span className="font-mono">{diag.vector_store.directory}</span></div>
            </div>
          </div>

          {/* Embedding Service */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase">Embedding Engine</span>
              <Activity className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="text-lg font-bold text-slate-900 font-mono capitalize">
              {diag.embedding_service.active_mode.replace('_', ' ')}
            </div>
            <div className="text-xs text-slate-500 space-y-1">
              <div>Model: <strong>BGE-Small-EN-v1.5</strong></div>
              <div>Fallback: <strong>Labelled TF-IDF</strong></div>
            </div>
          </div>

          {/* AI Provider */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase">AI Provider</span>
              <Sparkles className="w-4 h-4 text-amber-500" />
            </div>
            <div className="text-lg font-bold text-slate-900 capitalize">
              {diag.ai_provider.gemini_configured ? 'Gemini Configured' : 'Local Extractive'}
            </div>
            <div className="text-xs text-slate-500 space-y-1">
              <div>Model: <span className="font-mono">{diag.ai_provider.gemini_model}</span></div>
              <div>Status: {diag.ai_provider.gemini_configured ? (
                <span className="text-emerald-600 font-semibold">Key Detected</span>
              ) : (
                <span className="text-slate-400">Unconfigured (Safe Local Mode)</span>
              )}</div>
            </div>
          </div>
        </div>
      ) : null}

      {/* Provider Connection Test Block */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-base font-bold text-slate-900">Google Gemini Live Provider Test</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Admin connection test verifying live server-side Google GenAI credentials without exposing the API key.
            </p>
          </div>
          <button
            onClick={testGeminiConnection}
            disabled={geminiLoading}
            className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-xs disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${geminiLoading ? 'animate-spin' : ''}`} />
            <span>{geminiLoading ? 'Testing API...' : 'Test Connection'}</span>
          </button>
        </div>

        {geminiResult && (
          <div className={`p-4 rounded-xl text-xs font-mono border ${
            geminiResult.status === 'connected'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
              : geminiResult.status === 'unconfigured'
              ? 'bg-amber-50 border-amber-200 text-amber-900'
              : 'bg-red-50 border-red-200 text-red-900'
          }`}>
            <div className="font-bold uppercase text-[11px] mb-1">Status: {geminiResult.status}</div>
            <div>{geminiResult.message}</div>
            {geminiResult.latency_ms && <div className="mt-1">Latency: {geminiResult.latency_ms} ms</div>}
          </div>
        )}
      </div>

      {/* User Accounts Management */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-slate-500" />
            <h2 className="text-base font-bold text-slate-900">Application User Accounts</h2>
          </div>
        </div>

        {/* Create User Form */}
        <div className="p-6 bg-slate-50/50 border-b border-slate-200">
          <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3">Create New Account</h3>
          {userError && (
            <div className="mb-3 p-2 bg-red-50 text-red-700 text-xs rounded border border-red-200">{userError}</div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
            <input
              type="text"
              placeholder="Username"
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              className="p-2 border border-slate-300 rounded-lg bg-white"
            />
            <input
              type="email"
              placeholder="Email address"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              className="p-2 border border-slate-300 rounded-lg bg-white"
            />
            <input
              type="password"
              placeholder="Password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="p-2 border border-slate-300 rounded-lg bg-white"
            />
            <div className="flex gap-2">
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                className="p-2 border border-slate-300 rounded-lg bg-white flex-1"
              >
                <option value="admin">Admin</option>
                <option value="auditor">Auditor</option>
                <option value="member">Member</option>
              </select>
              <button
                type="button"
                onClick={() => createUserMutation.mutate()}
                disabled={createUserMutation.isPending || !newUsername || !newPassword}
                className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg font-semibold disabled:opacity-50"
              >
                Add
              </button>
            </div>
          </div>
        </div>

        {/* Existing Users Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-50 text-slate-700 uppercase font-semibold border-b border-slate-200">
              <tr>
                <th className="px-6 py-3">Username</th>
                <th className="px-6 py-3">Email</th>
                <th className="px-6 py-3">Role</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {users?.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50/80">
                  <td className="px-6 py-3.5 font-semibold text-slate-900">{u.username}</td>
                  <td className="px-6 py-3.5 text-slate-600">{u.email}</td>
                  <td className="px-6 py-3.5">
                    <span className="px-2 py-0.5 rounded font-bold uppercase text-[10px] bg-slate-100 text-slate-800">
                      {u.role}
                    </span>
                  </td>
                  <td className="px-6 py-3.5">
                    <span className="px-2 py-0.5 rounded font-semibold text-[10px] bg-emerald-100 text-emerald-800">
                      Active
                    </span>
                  </td>
                  <td className="px-6 py-3.5 text-slate-400">{new Date(u.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Scoped Reset Section */}
      <div className="bg-red-50/40 p-6 rounded-2xl border border-red-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h3 className="text-sm font-bold text-red-900">Reset Synthetic Test Data</h3>
          <p className="text-xs text-red-700 mt-1">
            Wipes synthetic test runs and probe evidence. Production documents and user accounts are preserved.
          </p>
        </div>
        <button
          onClick={resetSyntheticData}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold shadow-xs"
        >
          Reset Synthetic Runs
        </button>
      </div>
    </div>
  );
};
