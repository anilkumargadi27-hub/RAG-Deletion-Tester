import React from 'react';
import { useAuth } from '../context/AuthContext';
import { ShieldCheck, LogOut, User as UserIcon, Sparkles } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 bg-brand-600 rounded-lg flex items-center justify-center text-white shadow-sm">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-lg text-slate-900 tracking-tight">ForgetCheck</span>
            <span className="px-2 py-0.5 text-xs font-semibold bg-brand-50 text-brand-700 rounded-full border border-brand-200">
              RAG Deletion Tester
            </span>
          </div>
          <p className="text-xs text-slate-500 hidden sm:block">
            Check what your AI can still reveal after access changes.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="hidden md:flex items-center gap-1.5 px-3 py-1 bg-slate-100 rounded-full text-xs font-medium text-slate-700 border border-slate-200">
          <Sparkles className="w-3.5 h-3.5 text-brand-600" />
          <span>Mode: <strong className="text-slate-900">Local Extractive</strong> (Deterministic)</span>
        </div>

        {user && (
          <div className="flex items-center gap-3 pl-3 border-l border-slate-200">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-slate-700 text-xs font-bold">
                {user.username.slice(0, 2).toUpperCase()}
              </div>
              <div className="text-left hidden lg:block">
                <div className="text-sm font-semibold text-slate-800 leading-none">{user.username}</div>
                <span className="text-[10px] uppercase font-bold tracking-wider text-brand-600">{user.role}</span>
              </div>
            </div>

            <button
              onClick={() => logout()}
              title="Sign Out"
              className="p-1.5 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
