import React, { useEffect, useState } from 'react';
import { Mic, Shield, Radio, Activity, LogOut, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../api/client';
import { HealthStatus, SupervisorProfile } from '../types';

interface NavbarProps {
  activeTab: 'customer' | 'supervisor';
  onTabChange: (tab: 'customer' | 'supervisor') => void;
  supervisor: SupervisorProfile | null;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onTabChange,
  supervisor,
  onLogout,
}) => {
  const [health, setHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    const check = async () => {
      try {
        const res = await api.getHealth();
        setHealth(res);
      } catch (e) {
        setHealth(null);
      }
    };
    check();
    const interval = setInterval(check, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0.9rem 2rem',
      backgroundColor: 'rgba(15, 20, 34, 0.85)',
      backdropFilter: 'blur(16px)',
      borderBottom: '1px solid var(--border-subtle)',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    }}>
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <div style={{
          width: '38px',
          height: '38px',
          borderRadius: '10px',
          background: 'linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: 'var(--glow-primary)',
        }}>
          <Mic size={20} color="#ffffff" />
        </div>
        <div>
          <span style={{ fontSize: '1.25rem', fontWeight: 800, letterSpacing: '-0.03em', color: '#ffffff' }}>
            EPOXA
          </span>
          <span style={{
            marginLeft: '0.5rem',
            fontSize: '0.68rem',
            padding: '0.15rem 0.45rem',
            borderRadius: '999px',
            background: 'rgba(99, 102, 241, 0.2)',
            color: '#a5b4fc',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em'
          }}>
            V1 Production
          </span>
        </div>
      </div>

      {/* Supervisor Command Center Title in Center */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.6rem',
        padding: '0.45rem 1.1rem',
        borderRadius: '999px',
        background: 'rgba(99, 102, 241, 0.12)',
        border: '1px solid rgba(99, 102, 241, 0.3)',
      }}>
        <Shield size={16} color="#818cf8" />
        <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#e0e7ff', letterSpacing: '0.02em' }}>
          Supervisor Command Center
        </span>
      </div>

      {/* Right side: Backend Health & User */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
        {/* Backend health status pill */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          fontSize: '0.75rem',
          fontWeight: 600,
          padding: '0.3rem 0.7rem',
          borderRadius: '999px',
          background: health ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
          color: health ? '#34d399' : '#f87171',
          border: `1px solid ${health ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'}`,
        }}>
          {health ? <CheckCircle2 size={13} /> : <AlertCircle size={13} />}
          <span>{health ? 'API Ready' : 'API Connecting'}</span>
        </div>

        {/* Supervisor Profile / Signout */}
        {supervisor && activeTab === 'supervisor' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-end',
            }}>
              <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                {supervisor.full_name}
              </span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                {supervisor.role.toUpperCase()}
              </span>
            </div>
            <button
              onClick={onLogout}
              className="btn btn-secondary"
              title="Sign Out"
              style={{ padding: '0.45rem', borderRadius: '0.5rem' }}
            >
              <LogOut size={16} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
