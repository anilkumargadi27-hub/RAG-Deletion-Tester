import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  PlayCircle,
  FlaskConical,
  FileText,
  MessageSquare,
  History,
  GitCompare,
  FileDown,
  Settings
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const isAuditorOrAdmin = user?.role === 'admin' || user?.role === 'auditor';

  const navItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/demo', label: 'Guided Demo', icon: PlayCircle, badge: 'Interactive' },
    ...(isAuditorOrAdmin ? [{ to: '/lab', label: 'Synthetic Lab', icon: FlaskConical }] : []),
    { to: '/documents', label: 'Documents & ACLs', icon: FileText },
    { to: '/playground', label: 'Assistant Playground', icon: MessageSquare },
    ...(isAuditorOrAdmin ? [
      { to: '/runs', label: 'Run History', icon: History },
      { to: '/compare', label: 'Compare Runs', icon: GitCompare },
      { to: '/reports', label: 'Reports & Exports', icon: FileDown },
    ] : []),
    ...(isAdmin ? [{ to: '/admin', label: 'Admin Settings', icon: Settings }] : []),
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="p-4 flex-1">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 mb-2">
          Navigation
        </div>
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-brand-600 text-white'
                      : 'hover:bg-slate-800 text-slate-300 hover:text-white'
                  }`
                }
              >
                <div className="flex items-center gap-2.5">
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="px-1.5 py-0.5 text-[10px] font-bold bg-amber-400 text-slate-950 rounded">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      <div className="p-4 border-t border-slate-800 text-xs text-slate-400 space-y-1">
        <div className="flex justify-between">
          <span>Boundary:</span>
          <span className="text-slate-300">Retrieval & Cache</span>
        </div>
        <div className="flex justify-between">
          <span>Standard:</span>
          <span className="text-emerald-400 font-medium">No leakage observed</span>
        </div>
      </div>
    </aside>
  );
};
