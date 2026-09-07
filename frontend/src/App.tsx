import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MainLayout } from './layouts/MainLayout';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { ReportsPage } from './pages/ReportsPage';
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

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route element={<MainLayout />}>
            <Route path="/dashboard" element={<DashboardPage />} />
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

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
