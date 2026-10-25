import React, { useState, useEffect } from 'react';
import { CustomerVoiceView } from './views/CustomerVoiceView';
import { SupervisorDashboard } from './views/supervisor/SupervisorDashboard';
import { SupervisorLogin } from './views/supervisor/SupervisorLogin';
import { Navbar } from './components/Navbar';
import { SupervisorProfile } from './types';
import { api } from './api/client';

export function App() {
  // Determine mode based on port 5174 vs 5173, path, or query parameter
  const determineInitialMode = (): 'customer' | 'supervisor' => {
    const port = window.location.port;
    const path = window.location.pathname;
    const search = window.location.search;

    if (port === '5174' || path.startsWith('/supervisor') || search.includes('portal=supervisor') || search.includes('mode=supervisor')) {
      return 'supervisor';
    }
    return 'customer';
  };

  const [mode, setMode] = useState<'customer' | 'supervisor'>(determineInitialMode());
  const [supervisor, setSupervisor] = useState<SupervisorProfile | null>(null);

  useEffect(() => {
    // If supervisor mode, verify existing token if stored
    if (mode === 'supervisor') {
      if (api.getToken()) {
        api.getMe()
          .then((profile) => setSupervisor(profile))
          .catch(() => {
            api.setToken(null);
            setSupervisor(null);
          });
      }
    }
  }, [mode]);

  const handleLogout = () => {
    api.setToken(null);
    setSupervisor(null);
  };

  const isSupervisorPort = window.location.port === '5174';

  // --- CUSTOMER PORTAL (PORT 5173 / Default) ---
  if (mode === 'customer') {
    return (
      <div style={{
        height: '100vh',
        maxHeight: '100vh',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}>
        <div style={{ flex: 1, height: '100%', overflow: 'hidden' }}>
          <CustomerVoiceView />
        </div>
      </div>
    );
  }

  // --- SUPERVISOR PORTAL (PORT 5174 / Admin) ---
  return (
    <div style={{
      height: '100vh',
      maxHeight: '100vh',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--bg-main)',
    }}>
      {/* Supervisor Top Navbar */}
      <Navbar
        activeTab="supervisor"
        onTabChange={(tab) => {
          if (tab === 'customer') setMode('customer');
        }}
        supervisor={supervisor}
        onLogout={handleLogout}
      />

      {/* Main Supervisor Body */}
      <main style={{ flex: 1, height: 'calc(100vh - 65px)', overflow: 'hidden' }}>
        {supervisor ? (
          <SupervisorDashboard supervisor={supervisor} />
        ) : (
          <SupervisorLogin onSuccess={(profile) => setSupervisor(profile)} />
        )}
      </main>
    </div>
  );
}

export default App;
