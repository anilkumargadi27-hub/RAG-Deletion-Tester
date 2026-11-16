import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../api/client';
import { ChatMessage, ChatSession } from '../types';
import {
  MessageSquare, Send, Sparkles, User, Bot,
  ExternalLink, Plus, Zap, ShieldAlert
} from 'lucide-react';

export const Playground: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [inputMessage, setInputMessage] = useState('');
  const [principalId, setPrincipalId] = useState('general_employee');
  const [answerMode, setAnswerMode] = useState('local_extractive');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { data: sessions } = useQuery<ChatSession[]>({
    queryKey: ['chat_sessions'],
    queryFn: () => apiFetch<ChatSession[]>('/api/chat/sessions'),
  });

  useEffect(() => {
    if (sessions && sessions.length > 0 && !activeSessionId) {
      setActiveSessionId(sessions[0].id);
    }
  }, [sessions, activeSessionId]);

  const { data: messages, isLoading: messagesLoading } = useQuery<ChatMessage[]>({
    queryKey: ['messages', activeSessionId],
    queryFn: () => apiFetch<ChatMessage[]>(`/api/chat/sessions/${activeSessionId}/messages`),
    enabled: !!activeSessionId,
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMutation = useMutation({
    mutationFn: (msg: string) =>
      apiFetch<ChatMessage>('/api/chat/message', {
        method: 'POST',
        body: JSON.stringify({
          message: msg,
          session_id: activeSessionId,
          principal_id: principalId,
          answer_mode: answerMode,
        }),
      }),
    onSuccess: (data) => {
      setInputMessage('');
      if (!activeSessionId) {
        setActiveSessionId(data.session_id);
      }
      queryClient.invalidateQueries({ queryKey: ['messages', activeSessionId] });
      queryClient.invalidateQueries({ queryKey: ['chat_sessions'] });
    },
    onError: (err: any) => {
      alert(`Message error: ${err.message}`);
    },
  });

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || sendMutation.isPending) return;
    sendMutation.mutate(inputMessage.trim());
  };

  const startNewSession = () => {
    setActiveSessionId(null);
  };

  return (
    <div className="h-[calc(100vh-4rem)] flex overflow-hidden">
      {/* Session History Sidebar */}
      <div className="w-72 bg-white border-r border-slate-200 flex flex-col shrink-0">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">Chat Sessions</span>
          <button
            onClick={startNewSession}
            className="p-1.5 text-brand-600 hover:bg-brand-50 rounded-lg transition-colors"
            title="Start New Session"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          {sessions?.map((s) => (
            <button
              key={s.id}
              onClick={() => setActiveSessionId(s.id)}
              className={`w-full text-left p-3 rounded-xl text-xs font-medium transition-colors ${
                activeSessionId === s.id
                  ? 'bg-brand-50 text-brand-900 border border-brand-200'
                  : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <div className="font-semibold truncate">{s.title}</div>
              <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1">
                <span className="capitalize">{s.principal_id}</span>
                <span>{s.message_count} msgs</span>
              </div>
            </button>
          ))}
        </div>

        {/* Configuration Selectors */}
        <div className="p-4 border-t border-slate-200 bg-slate-50/50 space-y-3 text-xs">
          <div>
            <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
              Simulated Principal
            </label>
            <select
              value={principalId}
              onChange={(e) => setPrincipalId(e.target.value)}
              className="w-full p-2 border border-slate-300 rounded-lg text-xs bg-white"
            >
              <option value="general_employee">General Employee (Default)</option>
              <option value="hr_manager">HR Manager</option>
              <option value="finance_director">Finance Director</option>
              <option value="engineering_lead">Engineering Lead</option>
              <option value="contractor">External Contractor</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
              Answer Mode
            </label>
            <select
              value={answerMode}
              onChange={(e) => setAnswerMode(e.target.value)}
              className="w-full p-2 border border-slate-300 rounded-lg text-xs bg-white"
            >
              <option value="local_extractive">Local Extractive (Deterministic)</option>
              <option value="live_gemini">Live Gemini Mode (via SDK)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-slate-50">
        <div className="p-4 bg-white border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-brand-600" />
            <h2 className="font-bold text-slate-900 text-sm">Assistant Grounded Playground</h2>
          </div>
          <span className="text-xs px-2.5 py-1 bg-slate-100 rounded-full font-medium text-slate-700">
            Current Principal: <strong className="text-slate-900 font-mono">{principalId}</strong>
          </span>
        </div>

        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {(!messages || messages.length === 0) && (
            <div className="text-center py-16 text-slate-400 space-y-2">
              <MessageSquare className="w-10 h-10 mx-auto text-slate-300" />
              <p className="text-sm font-medium">Ask a question grounded in permitted documentation.</p>
              <p className="text-xs max-w-sm mx-auto">
                Try: <em>"What health insurance covers employees?"</em> or <em>"What is the daily meal per diem?"</em>
              </p>
            </div>
          )}

          {messages?.map((m) => (
            <div
              key={m.id}
              className={`flex gap-3 max-w-3xl ${m.role === 'user' ? 'ml-auto flex-row-reverse' : 'mr-auto'}`}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-xs font-bold ${
                  m.role === 'user'
                    ? 'bg-slate-900 text-white'
                    : 'bg-brand-600 text-white'
                }`}
              >
                {m.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              <div className="space-y-2 max-w-xl">
                <div
                  className={`p-4 rounded-2xl text-sm leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-brand-600 text-white rounded-tr-none'
                      : 'bg-white text-slate-800 border border-slate-200 shadow-sm rounded-tl-none'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{m.content}</p>
                </div>

                {/* Citations block for assistant response */}
                {m.role === 'assistant' && m.citations && m.citations.length > 0 && (
                  <div className="bg-white/80 border border-slate-200 rounded-xl p-3 text-xs space-y-1.5 shadow-xs">
                    <span className="font-bold text-slate-600 uppercase text-[10px] tracking-wider block">
                      Permitted Citations ({m.citations.length})
                    </span>
                    {m.citations.map((c, i) => (
                      <div key={i} className="text-slate-700 bg-slate-50 p-2 rounded-lg border border-slate-100">
                        <strong className="text-brand-700">{c.document_title}</strong>:
                        <span className="text-slate-600 ml-1 italic font-mono text-[11px]">"{c.snippet}"</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 bg-white border-t border-slate-200">
          <form onSubmit={handleSend} className="flex gap-2 max-w-4xl mx-auto">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask a question about company documents..."
              className="flex-1 p-3 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-slate-50/50"
            />
            <button
              type="submit"
              disabled={sendMutation.isPending || !inputMessage.trim()}
              className="px-5 py-3 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-sm font-semibold flex items-center gap-2 shadow-sm transition-colors disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
              <span>{sendMutation.isPending ? 'Sending...' : 'Send'}</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
