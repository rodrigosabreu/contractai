'use client';

import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { useAuth } from '@/lib/auth';
import { ContractsView } from './ContractsView';
import { AnalysisView } from './AnalysisView';
import { ReportsView } from './ReportsView';
import { ConnectorsView } from './ConnectorsView';
import { SettingsView } from './SettingsView';
import { useState } from 'react';

type View = 'contracts' | 'analysis' | 'reports' | 'connectors' | 'settings';

export function Dashboard() {
  const { user } = useAuth();
  const [currentView, setCurrentView] = useState<View>('contracts');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const views = {
    contracts: <ContractsView />,
    analysis: <AnalysisView />,
    reports: <ReportsView />,
    connectors: <ConnectorsView />,
    settings: <SettingsView />,
  };

  return (
    <div className="min-h-screen bg-secondary-50">
      <Sidebar
        currentView={currentView}
        onViewChange={setCurrentView}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(!sidebarOpen)}
      />
      <div className={`lg:pl-64 transition-all duration-300 ${sidebarOpen ? 'pl-64' : 'pl-0'}`}>
        <Header
          user={user}
          onMenuClick={() => setSidebarOpen(!sidebarOpen)}
        />
        <main className="p-4 lg:p-8">
          <div className="max-w-7xl mx-auto">
            {views[currentView]}
          </div>
        </main>
      </div>
    </div>
  );
}