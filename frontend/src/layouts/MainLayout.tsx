import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from '../components/layout/Sidebar';
import { Topbar } from '../components/layout/Topbar';

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': 'Executive Safety Command Center',
  '/reports': 'Report Intelligence',
  '/risk-intelligence': 'Risk Intelligence Workspace',
  '/sif-precursors': 'Serious Injury & Fatality Precursors',
  '/barriers': 'Safety Barrier Intelligence',
  '/patterns': 'Emerging Risk Patterns',
  '/life-saving-rules': 'Life-Saving Rule Compliance',
  '/recommendations': 'Recommended Interventions',
  '/analytics': 'Advanced Safety Analytics',
  '/model-performance': 'AI / ML Model Performance',
  '/audit-log': 'Audit Log & Compliance',
  '/review-queue': 'HSE Review Queue (Human-in-the-Loop)',
  '/settings': 'System Configuration',
};

export const MainLayout: React.FC = () => {
  const [selectedSite, setSelectedSite] = useState('All Sites');
  const location = useLocation();

  const getTitle = () => {
    if (location.pathname.startsWith('/reports/')) return 'Report Detail Intelligence';
    return PAGE_TITLES[location.pathname] || 'Safety Intelligence Command';
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0b0f17] text-slate-100 bg-telemetry-grid">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        {/* Topbar */}
        <Topbar
          pageTitle={getTitle()}
          selectedSite={selectedSite}
          onSiteChange={(site) => setSelectedSite(site)}
        />

        {/* Dynamic Route Content */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          <Outlet context={{ selectedSite }} />
        </main>
      </div>
    </div>
  );
};
