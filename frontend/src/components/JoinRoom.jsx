import React, { useState } from 'react';
import { PhoneCall, User, Sparkles, Mic, ShieldCheck, Zap } from 'lucide-react';

/**
 * JoinRoom component: Professional SaaS pre-call lobby.
 * Provides crisp input verification, microphone requirement guidance,
 * and seamless connection action.
 */
export default function JoinRoom({ onJoin, isLoading }) {
  const [participantName, setParticipantName] = useState('');
  const [isFocused, setIsFocused] = useState(false);

  const isNameValid = participantName.trim().length >= 2;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!isNameValid || isLoading) return;

    // Generate a random 5-digit number for a unique private room
    const randomId = Math.floor(10000 + Math.random() * 90000);
    const generatedRoomName = `support-user-${randomId}`;

    onJoin({
      participantName: participantName.trim(),
      roomName: generatedRoomName
    });
  };

  return (
    <div className="lobby-container">
      {/* Glow Backdrop Highlight */}
      <div className="lobby-ambient-halo" />

      <div className="lobby-card saas-card-glass">
        {/* Brand Header */}
        <div className="lobby-brand-header">
          <div className="brand-badge">
            <div className="brand-logo-glow">
              <Sparkles size={18} className="brand-icon" />
            </div>
            <span className="brand-badge-text">EPOXCEL VOICE ASSISTANT</span>
          </div>
          
          <h1 className="lobby-title">
            Speak with <span className="title-gradient">Epixa</span>
          </h1>
          <p className="lobby-subtitle">
            Instant voice assistance for account inquiries, appointments, and live human support.
          </p>
        </div>

        {/* Feature Highlights Pills */}
        <div className="feature-tags-row">
          <div className="feature-pill">
            <Zap size={13} className="pill-icon text-cyan" />
            <span>Zero Wait Time</span>
          </div>
          <div className="feature-pill">
            <ShieldCheck size={13} className="pill-icon text-emerald" />
            <span>Verified AI Session</span>
          </div>
        </div>

        {/* Entry Form */}
        <form onSubmit={handleSubmit} className="lobby-form">
          <div className={`input-field-group ${isFocused ? 'focused' : ''} ${participantName ? 'has-value' : ''}`}>
            <label htmlFor="participantName" className="input-field-label">
              Your Full Name
            </label>
            
            <div className="input-field-wrapper">
              <div className="input-adornment">
                <User size={18} className="field-icon" />
              </div>
              
              <input
                id="participantName"
                type="text"
                value={participantName}
                onChange={(e) => setParticipantName(e.target.value)}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setIsFocused(false)}
                placeholder="e.g. Sarah Jenkins"
                disabled={isLoading}
                autoComplete="name"
                maxLength={60}
                required
              />
            </div>
            
            <span className="input-hint-text">
              Enter your name so Epixa can personalize your session.
            </span>
          </div>

          {/* Microphone Guidance Card */}
          <div className="mic-notice-card">
            <div className="mic-icon-circle">
              <Mic size={15} />
            </div>
            <div className="mic-notice-content">
              <span className="mic-notice-title">Microphone Access Required</span>
              <span className="mic-notice-desc">Your browser will request audio permission when joining the call.</span>
            </div>
          </div>

          {/* Connect Action Button */}
          <button
            type="submit"
            className="saas-btn saas-btn-primary lobby-submit-btn"
            disabled={!isNameValid || isLoading}
          >
            {isLoading ? (
              <span className="btn-loading-state">
                <span className="lobby-spinner" />
                <span>Establishing Secure Call...</span>
              </span>
            ) : (
              <>
                <PhoneCall size={18} className="btn-icon-mr" />
                <span>Start Voice Call</span>
              </>
            )}
          </button>
        </form>

        {/* Security & Reliability Footer */}
        <div className="lobby-footer">
          <span>Encrypted WebRTC Audio Session • LiveKit Cloud</span>
        </div>
      </div>

      <style>{`
        .lobby-container {
          position: relative;
          width: 100%;
          max-width: 460px;
          display: flex;
          flex-direction: column;
          align-items: center;
          margin: auto;
          padding: 16px;
          box-sizing: border-box;
          z-index: 10;
        }

        .lobby-ambient-halo {
          position: absolute;
          top: -40px;
          left: 50%;
          transform: translateX(-50%);
          width: 320px;
          height: 220px;
          background: radial-gradient(circle, rgba(99, 102, 241, 0.28) 0%, rgba(139, 92, 246, 0.12) 50%, transparent 70%);
          filter: blur(40px);
          pointer-events: none;
          z-index: -1;
        }

        .lobby-card {
          width: 100%;
          padding: 36px 32px;
          box-sizing: border-box;
          display: flex;
          flex-direction: column;
          gap: 24px;
        }

        .lobby-brand-header {
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
          gap: 10px;
        }

        .brand-badge {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 5px 12px 5px 6px;
          background: rgba(99, 102, 241, 0.08);
          border: 1px solid rgba(99, 102, 241, 0.22);
          border-radius: var(--saas-radius-full);
          margin-bottom: 4px;
        }

        .brand-logo-glow {
          width: 24px;
          height: 24px;
          border-radius: 50%;
          background: var(--saas-brand-gradient);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          box-shadow: 0 0 10px rgba(99, 102, 241, 0.5);
        }

        .brand-badge-text {
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.06em;
          color: #c7d2fe;
          text-transform: uppercase;
        }

        .lobby-title {
          font-family: var(--saas-font-display);
          font-size: 26px;
          font-weight: 800;
          letter-spacing: -0.03em;
          color: #ffffff;
          margin: 0;
          line-height: 1.2;
        }

        .title-gradient {
          background: linear-gradient(135deg, #a5b4fc 0%, #c084fc 60%, #f472b6 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .lobby-subtitle {
          font-size: 13.5px;
          line-height: 1.55;
          color: var(--saas-text-secondary);
          margin: 0;
          max-width: 360px;
        }

        .feature-tags-row {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          flex-wrap: wrap;
        }

        .feature-pill {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 11.5px;
          font-weight: 500;
          color: #cbd5e1;
          background: rgba(255, 255, 255, 0.035);
          border: 1px solid rgba(255, 255, 255, 0.06);
          padding: 5px 11px;
          border-radius: var(--saas-radius-full);
        }

        .text-cyan {
          color: #38bdf8;
        }

        .text-emerald {
          color: #34d399;
        }

        .lobby-form {
          display: flex;
          flex-direction: column;
          gap: 20px;
          width: 100%;
        }

        .input-field-group {
          display: flex;
          flex-direction: column;
          gap: 7px;
          text-align: left;
        }

        .input-field-label {
          font-size: 12.5px;
          font-weight: 600;
          color: #cbd5e1;
          letter-spacing: 0.01em;
          margin-left: 2px;
        }

        .input-field-wrapper {
          position: relative;
          display: flex;
          align-items: center;
          width: 100%;
        }

        .input-adornment {
          position: absolute;
          left: 14px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #64748b;
          pointer-events: none;
          transition: color var(--saas-transition-fast);
        }

        .input-field-group.focused .input-adornment {
          color: var(--saas-brand-primary);
        }

        .input-field-wrapper input {
          width: 100%;
          padding: 13px 16px 13px 44px;
          border-radius: var(--saas-radius-md);
          border: 1px solid var(--saas-border-medium);
          background: rgba(10, 13, 20, 0.6);
          color: #ffffff;
          font-family: var(--saas-font-sans);
          font-size: 14.5px;
          outline: none;
          box-sizing: border-box;
          transition: all var(--saas-transition-fast);
        }

        .input-field-wrapper input:focus {
          border-color: var(--saas-brand-primary);
          background: rgba(18, 22, 33, 0.85);
          box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2), inset 0 1px 2px rgba(0, 0, 0, 0.3);
        }

        .input-field-wrapper input::placeholder {
          color: #475569;
        }

        .input-hint-text {
          font-size: 11.5px;
          color: var(--saas-text-muted);
          margin-left: 2px;
        }

        .mic-notice-card {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          padding: 12px 14px;
          background: rgba(99, 102, 241, 0.05);
          border: 1px solid rgba(99, 102, 241, 0.14);
          border-radius: var(--saas-radius-md);
        }

        .mic-icon-circle {
          width: 28px;
          height: 28px;
          border-radius: 50%;
          background: rgba(99, 102, 241, 0.12);
          color: #818cf8;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          margin-top: 1px;
        }

        .mic-notice-content {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .mic-notice-title {
          font-size: 12px;
          font-weight: 600;
          color: #e0e7ff;
        }

        .mic-notice-desc {
          font-size: 11.5px;
          color: #94a3b8;
          line-height: 1.4;
        }

        .lobby-submit-btn {
          width: 100%;
          padding: 14px;
          font-size: 15px;
          border-radius: var(--saas-radius-md);
          font-family: var(--saas-font-display);
        }

        .btn-icon-mr {
          margin-right: 2px;
        }

        .btn-loading-state {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
        }

        .lobby-spinner {
          width: 16px;
          height: 16px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-top-color: #ffffff;
          border-radius: 50%;
          animation: spinLobby 0.7s linear infinite;
        }

        @keyframes spinLobby {
          to { transform: rotate(360deg); }
        }

        .lobby-footer {
          text-align: center;
          font-size: 11px;
          color: var(--saas-text-muted);
          border-top: 1px solid var(--saas-border-subtle);
          padding-top: 16px;
        }

        @media (max-width: 480px) {
          .lobby-card {
            padding: 28px 20px;
            border-radius: var(--saas-radius-lg);
          }
          .lobby-title {
            font-size: 22px;
          }
        }
      `}</style>
    </div>
  );
}
