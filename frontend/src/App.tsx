import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MainLayout } from './layouts/MainLayout';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { ReportsPage } from './pages/ReportsPage';
import { SubmitReportPage } from './pages/SubmitReportPage';
import { ReportDetailPage } from './pages/ReportDetailPage';
import { RiskIntelligencePage } from './pages/RiskIntelligencePage';
import { SIFPrecursorsPage } from './pages/SIFPrecursorsPage';
import { BarrierFailuresPage } from './pages/BarrierFailuresPage';
import { PatternsPage } from './pages/PatternsPage';
import { LifeSavingRulesPage } from './pages/LifeSavingRulesPage';
import { RecommendationsPage } from './pages/RecommendationsPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { ModelPerformancePage } from './pages/ModelPerformancePage';
import { AuditLogPage } from './pages/AuditLogPage';
import { ReviewQueuePage } from './pages/ReviewQueuePage';
import { SettingsPage } from './pages/SettingsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 1000 * 60 * 5,
    },
  },
});

/**
 * Gate the console behind a session. Unauthenticated visitors are sent to the
 * login page with the page they wanted, so they land there after signing in
 * instead of always being dumped on the dashboard.
 */
function RequireAuth({ children }: { children: ReactElement }) {
  const location = useLocation();
  const token = typeof window === 'undefined' ? null : window.localStorage.getItem('sentinel_token');

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return children;
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />

          <Route
            element={
              <RequireAuth>
                <MainLayout />
              </RequireAuth>
            }
          >
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/submit" element={<SubmitReportPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/reports/:id" element={<ReportDetailPage />} />
            <Route path="/risk-intelligence" element={<RiskIntelligencePage />} />
            <Route path="/sif-precursors" element={<SIFPrecursorsPage />} />
            <Route path="/barriers" element={<BarrierFailuresPage />} />
            <Route path="/patterns" element={<PatternsPage />} />
            <Route path="/life-saving-rules" element={<LifeSavingRulesPage />} />
            <Route path="/recommendations" element={<RecommendationsPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/model-performance" element={<ModelPerformancePage />} />
            <Route path="/audit-log" element={<AuditLogPage />} />
            <Route path="/review-queue" element={<ReviewQueuePage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
