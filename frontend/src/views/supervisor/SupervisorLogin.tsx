import React, { useState } from 'react';
import { Shield, KeyRound, Lock, Mail, AlertCircle, CheckCircle2 } from 'lucide-react';
import { api } from '../../api/client';
import { SupervisorProfile } from '../../types';

interface SupervisorLoginProps {
  onSuccess: (profile: SupervisorProfile) => void;
}

export const SupervisorLogin: React.FC<SupervisorLoginProps> = ({ onSuccess }) => {
  const [email, setEmail] = useState('supervisor@epoxa.demo');
  const [password, setPassword] = useState('EpoxaDemo@2026');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsLoading(true);

    try {
      const res = await api.login(email.trim(), password);
      onSuccess(res.user);
    } catch (e: any) {
      setErrorMsg(e.message || 'Invalid email or password. Access denied by database.');
    } finally {
      setIsLoading(false);
    }
  };

  const fillDemo = () => {
    setEmail('supervisor@epoxa.demo');
    setPassword('EpoxaDemo@2026');
    setErrorMsg(null);
  };

  return (
    <div style={{
      width: '100%',
      minHeight: 'calc(100vh - 120px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '1.5rem',
      boxSizing: 'border-box',
    }}>
      <div className="card" style={{
        maxWidth: '440px',
        width: '100%',
        padding: '2rem',
        borderRadius: '1rem',
        boxShadow: 'var(--shadow-card)',
        border: '1px solid var(--border-subtle)',
      }}>
        {/* Header Icon & Title */}
        <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
          <div style={{
            width: '52px',
            height: '52px',
            borderRadius: '14px',
            background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 1rem',
            boxShadow: 'var(--glow-primary)',
          }}>
            <Shield size={26} color="#ffffff" />
          </div>
          <h2 style={{ fontSize: '1.4rem', color: '#ffffff', marginBottom: '0.3rem' }}>
            Supervisor Command Center
          </h2>
          <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
            Database-backed supervisor credentials required to monitor and take over live calls.
          </p>
        </div>

        {/* Error Alert */}
        {errorMsg && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.6rem',
            padding: '0.75rem 1rem',
            borderRadius: '0.5rem',
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#fca5a5',
            fontSize: '0.84rem',
            marginBottom: '1.25rem',
          }}>
            <AlertCircle size={16} style={{ flexShrink: 0 }} />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Credentials Form */}
        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
              Supervisor Email
            </label>
            <div style={{ position: 'relative' }}>
              <Mail size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)' }} />
              <input
                id="supervisor-email-input"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="supervisor@epoxa.demo"
                style={{
                  width: '100%',
                  padding: '0.65rem 0.85rem 0.65rem 2.4rem',
                  borderRadius: '0.5rem',
                  border: '1px solid var(--border-subtle)',
                  background: 'var(--bg-main)',
                  color: '#ffffff',
                  fontSize: '0.88rem',
                  outline: 'none',
                }}
              />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
              Database Password
            </label>
            <div style={{ position: 'relative' }}>
              <Lock size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)' }} />
              <input
                id="supervisor-password-input"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                style={{
                  width: '100%',
                  padding: '0.65rem 0.85rem 0.65rem 2.4rem',
                  borderRadius: '0.5rem',
                  border: '1px solid var(--border-subtle)',
                  background: 'var(--bg-main)',
                  color: '#ffffff',
                  fontSize: '0.88rem',
                  outline: 'none',
                }}
              />
            </div>
          </div>

          <button
            id="supervisor-signin-btn"
            type="submit"
            disabled={isLoading}
            className="btn btn-primary"
            style={{
              width: '100%',
              padding: '0.75rem',
              fontSize: '0.92rem',
              marginTop: '0.25rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
            }}
          >
            <KeyRound size={17} />
            {isLoading ? 'Verifying in PostgreSQL...' : 'Sign In as Supervisor'}
          </button>
        </form>

        {/* Demo Helper Box */}
        <div style={{
          marginTop: '1.25rem',
          padding: '0.85rem 1rem',
          borderRadius: '0.5rem',
          background: 'rgba(99, 102, 241, 0.08)',
          border: '1px solid rgba(99, 102, 241, 0.2)',
          fontSize: '0.78rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.4rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontWeight: 600, color: '#a5b4fc' }}>PostgreSQL Demo Credentials:</span>
            <button
              type="button"
              onClick={fillDemo}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#6366f1',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.75rem',
                textDecoration: 'underline',
              }}
            >
              Fill Defaults
            </button>
          </div>
          <div style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
            User: <strong>supervisor@epoxa.demo</strong><br />
            Pass: <strong>EpoxaDemo@2026</strong>
          </div>
        </div>
      </div>
    </div>
  );
};
