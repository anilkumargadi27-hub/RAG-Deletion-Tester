import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { Login } from './pages/Login';
import { Overview } from './pages/Overview';
import { GuidedDemo } from './pages/GuidedDemo';
import { SyntheticLab } from './pages/SyntheticLab';
import { Documents } from './pages/Documents';
import { Playground } from './pages/Playground';
import { RunHistory } from './pages/RunHistory';
import { RunDetail } from './pages/RunDetail';
import { CompareRuns } from './pages/CompareRuns';
import { Reports } from './pages/Reports';
import { AdminSettings } from './pages/AdminSettings';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const ProtectedLayout: React.FC = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center text-white text-sm">
        Initializing ForgetCheck...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <Navbar />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/demo" element={<GuidedDemo />} />
            <Route path="/lab" element={<SyntheticLab />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/playground" element={<Playground />} />
            <Route path="/runs" element={<RunHistory />} />
            <Route path="/runs/:id" element={<RunDetail />} />
            <Route path="/compare" element={<CompareRuns />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/admin" element={<AdminSettings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
};

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/*" element={<ProtectedLayout />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
