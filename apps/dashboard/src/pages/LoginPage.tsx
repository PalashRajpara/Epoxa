import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { AlertCircle, Headphones, Lock, Mail, Shield, Sparkles } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const { signIn } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please provide your email and password.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await signIn(email, password);
      navigate('/calls');
    } catch (err: any) {
      console.error('Sign-in failed:', err);
      setError(err.message || 'Invalid credentials or inactive membership.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-viewport-shell">
      <div className="ambient-background-glow glow-top-left" />
      <div className="ambient-background-glow glow-bottom-right" />

      <div className="login-card-container saas-card-glass">
        <div className="login-header-center">
          <div className="brand-orb-logo-box">
            <Shield size={30} className="brand-orb-icon" />
          </div>
          <h1 className="login-title">Voice AI Agent</h1>
          <p className="login-subtitle">
            Enterprise Voice AI Monitoring & Real-Time Escalation Console
          </p>
        </div>

        {error && (
          <div className="login-error-alert" role="alert">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="input-group-saas">
            <label htmlFor="login-email" className="input-label-saas">
              Staff Email Address
            </label>
            <div className="input-field-wrapper">
              <Mail size={16} className="input-field-icon" />
              <input
                id="login-email"
                type="email"
                placeholder="supervisor@voiceai.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="saas-input"
                required
                disabled={isLoading}
              />
            </div>
          </div>

          <div className="input-group-saas">
            <label htmlFor="login-password" className="input-label-saas">
              Password
            </label>
            <div className="input-field-wrapper">
              <Lock size={16} className="input-field-icon" />
              <input
                id="login-password"
                type="password"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="saas-input"
                required
                disabled={isLoading}
              />
            </div>
          </div>

          <button
            type="submit"
            className="start-call-action-btn"
            disabled={isLoading}
            id="btn-login-submit"
          >
            {isLoading ? (
              <span className="btn-spinner-row">
                <span className="btn-spinner" />
                Authenticating Session...
              </span>
            ) : (
              <span className="btn-content-row">
                <Lock size={16} />
                Access Supervisor Console
              </span>
            )}
          </button>
        </form>

        <div className="login-footer-security">
          <Shield size={14} className="security-icon" />
          <span>Restricted Portal. Authorized personnel only.</span>
        </div>
      </div>
    </div>
  );
};
