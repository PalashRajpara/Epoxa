import React, { useState } from 'react';
import ActiveCallsList from './components/ActiveCallsList';
import TranscriptView from './components/TranscriptView';
import JoinCallButton from './components/JoinCallButton';
import { Shield, Sparkles, PhoneCall, HelpCircle, Activity, Headphones } from 'lucide-react';

export default function App() {
  const [selectedCall, setSelectedCall] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected'); // 'disconnected' | 'connecting' | 'connected'

  const handleSelectCall = (call) => {
    // Only allow changing calls if not currently connected
    if (connectionStatus !== 'disconnected') {
      alert("Please disconnect from the current live call before switching sessions.");
      return;
    }
    setSelectedCall(call);
  };

  return (
    <div className="saas-dashboard-shell">
      {/* Top Enterprise Application Header */}
      <header className="dashboard-top-navbar saas-card-glass">
        <div className="navbar-left">
          <div className="brand-emblem-box">
            <Shield size={20} className="brand-emblem-icon" />
          </div>
          <div className="brand-title-lockup">
            <div className="brand-name-row">
              <span className="brand-name">Epoxcel</span>
              <span className="brand-version-badge">v3.0 Production</span>
            </div>
            <span className="brand-subtitle">Voice AI Supervisor & Escalation Console</span>
          </div>
        </div>

        <div className="navbar-right">
          <div className="system-telemetry-chip">
            <Activity size={13} className="telemetry-live-icon" />
            <span className="telemetry-label">System Active • Real-time DB Sync</span>
          </div>

          <div className="supervisor-profile-chip">
            <div className="supervisor-av-circle">
              <Headphones size={13} />
            </div>
            <span className="supervisor-role-title">Supervisor Console</span>
          </div>
        </div>
      </header>

      {/* Sticky "Supervisor Live in Room" Alert Ribbon */}
      {connectionStatus === 'connected' && selectedCall && (
        <div className="supervisor-live-ribbon">
          <div className="ribbon-content">
            <div className="ribbon-pulse-dot" />
            <span className="ribbon-text">
              <strong>YOU ARE LIVE:</strong> Connected to room <span className="saas-mono">{selectedCall.room_name}</span> speaking with <strong>{selectedCall.participant_name || 'Customer'}</strong>. AI responses are muted.
            </span>
          </div>
        </div>
      )}

      {/* Main Workspace Layout (Sidebar + Detail Stage) */}
      <main className="dashboard-body-grid">
        {/* Sidebar Container */}
        <aside className="dashboard-sidebar-column">
          <div className="sidebar-inner-card saas-card-glass">
            <ActiveCallsList 
              selectedCall={selectedCall} 
              onSelectCall={handleSelectCall} 
            />
          </div>
        </aside>

        {/* Content Details Column */}
        <section className="dashboard-stage-column">
          {selectedCall ? (
            <div className="session-inspector-view">
              {/* Session Overview Card */}
              <div className="session-header-plate saas-card-glass">
                <div className="plate-top-row">
                  <div className="caller-identity-group">
                    <div className="caller-av-box">
                      <PhoneCall size={20} />
                    </div>
                    <div className="caller-text-group">
                      <div className="caller-name-heading-row">
                        <h2 className="caller-full-name">{selectedCall.participant_name || 'Anonymous Customer'}</h2>
                        <span className={`status-badge-saas ${
                          selectedCall.status === 'escalated' ? 'badge-saas-escalated' :
                          selectedCall.status === 'completed' || selectedCall.status === 'dropped' || selectedCall.status === 'error' || selectedCall.status === 'timeout' ? 'badge-saas-ended' : 'badge-saas-active'
                        }`}>
                          {selectedCall.status === 'escalated' ? 'Handoff Alert' :
                           selectedCall.status === 'completed' || selectedCall.status === 'dropped' || selectedCall.status === 'error' || selectedCall.status === 'timeout' ? 'Call Ended' : 'AI Active'}
                        </span>
                      </div>
                      <span className="room-subtag saas-mono">Room: {selectedCall.room_name}</span>
                    </div>
                  </div>

                  <div className="plate-action-group">
                    <JoinCallButton 
                      roomName={selectedCall.room_name}
                      sessionId={selectedCall.id}
                      status={selectedCall.status}
                      onConnectionChange={(status) => setConnectionStatus(status)}
                    />
                  </div>
                </div>

                <div className="plate-divider-line" />

                {/* Structured Metadata Grid */}
                <div className="session-meta-grid">
                  <div className="meta-data-cell">
                    <span className="cell-label">Session UUID</span>
                    <span className="cell-value saas-mono" title={selectedCall.id}>
                      {selectedCall.id.substring(0, 16)}...
                    </span>
                  </div>

                  <div className="meta-data-cell">
                    <span className="cell-label">Date</span>
                    <span className="cell-value">
                      {new Date(selectedCall.started_at).toLocaleDateString([], { month: 'short', day: '2-digit', year: 'numeric' })}
                    </span>
                  </div>

                  <div className="meta-data-cell">
                    <span className="cell-label">Started At</span>
                    <span className="cell-value saas-mono">
                      {new Date(selectedCall.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  </div>

                  <div className="meta-data-cell">
                    <span className="cell-label">Ended At</span>
                    <span className="cell-value saas-mono">
                      {selectedCall.ended_at
                        ? new Date(selectedCall.ended_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                        : 'Live Session'}
                    </span>
                  </div>

                  <div className="meta-data-cell">
                    <span className="cell-label">Duration</span>
                    <span className="cell-value cell-highlight saas-mono">
                      {selectedCall.duration_seconds 
                        ? `${Math.floor(selectedCall.duration_seconds / 60)}m ${selectedCall.duration_seconds % 60}s`
                        : 'Active Call'}
                    </span>
                  </div>
                </div>

                {/* Disconnect Reason or Summary Preview if present */}
                {(selectedCall.summary || selectedCall.disconnect_reason) && (
                  <div className="post-call-summary-strip">
                    <span className="summary-title">Call Outcome:</span>
                    <span className="summary-text">
                      {selectedCall.summary || selectedCall.disconnect_reason}
                    </span>
                  </div>
                )}
              </div>

              {/* Live Transcript View Component */}
              <TranscriptView sessionId={selectedCall.id} />
            </div>
          ) : (
            /* Empty State Guide */
            <div className="stage-empty-welcome saas-card-glass">
              <div className="welcome-halo-icon">
                <Sparkles size={48} className="welcome-sparkle-svg" />
              </div>
              
              <h3 className="welcome-main-title">Supervisor Console Ready</h3>
              <p className="welcome-sub-lead">
                Select any active call from the queue on the left to monitor live transcripts or join the voice conversation.
              </p>

              <div className="quick-guide-card">
                <div className="guide-header">
                  <HelpCircle size={17} className="guide-info-icon" />
                  <h4>Escalation & Handoff Playbook</h4>
                </div>
                
                <div className="guide-steps-list">
                  <div className="guide-step-item">
                    <div className="step-num">1</div>
                    <p>When customer verification fails or a user asks for a human, the session status badge turns <strong>RED (Handoff Needed)</strong>.</p>
                  </div>
                  <div className="guide-step-item">
                    <div className="step-num">2</div>
                    <p>Click the call in the queue to review the real-time transcript and obtain full conversation context.</p>
                  </div>
                  <div className="guide-step-item">
                    <div className="step-num">3</div>
                    <p>Click <strong>Join Live Call</strong> to speak directly. When finished, click <strong>Hand Back to AI</strong> to resume automated assistance.</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </section>
      </main>

      <style>{`
        .saas-dashboard-shell {
          width: 100%;
          max-width: 100vw;
          height: 100vh;
          margin: 0;
          padding: 14px 20px;
          display: flex;
          flex-direction: column;
          gap: 12px;
          box-sizing: border-box;
          overflow: hidden;
        }

        /* Top Navbar */
        .dashboard-top-navbar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 10px 20px;
          border-radius: var(--saas-radius-lg);
          gap: 16px;
          flex-shrink: 0;
        }

        .navbar-left {
          display: flex;
          align-items: center;
          gap: 14px;
        }

        .brand-emblem-box {
          width: 40px;
          height: 40px;
          border-radius: var(--saas-radius-md);
          background: var(--saas-brand-gradient);
          display: flex;
          align-items: center;
          justify-content: center;
          color: #ffffff;
          box-shadow: 0 4px 16px var(--saas-brand-glow);
        }

        .brand-emblem-icon {
          color: #ffffff;
        }

        .brand-title-lockup {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .brand-name-row {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .brand-name {
          font-family: var(--saas-font-display);
          font-size: 19px;
          font-weight: 800;
          letter-spacing: -0.03em;
          color: #ffffff;
        }

        .brand-version-badge {
          font-size: 10.5px;
          font-weight: 700;
          color: #a5b4fc;
          background: rgba(99, 102, 241, 0.12);
          border: 1px solid rgba(99, 102, 241, 0.25);
          padding: 2px 7px;
          border-radius: var(--saas-radius-full);
          letter-spacing: 0.02em;
        }

        .brand-subtitle {
          font-size: 12px;
          color: var(--saas-text-muted);
        }

        .navbar-right {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .system-telemetry-chip {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 12px;
          font-weight: 600;
          color: #cbd5e1;
          background: rgba(255, 255, 255, 0.035);
          border: 1px solid var(--saas-border-subtle);
          padding: 6px 12px;
          border-radius: var(--saas-radius-full);
        }

        .telemetry-live-icon {
          color: #10b981;
          animation: pulseRecord 1.6s infinite;
        }

        .supervisor-profile-chip {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 12px;
          font-weight: 600;
          color: #e2e8f0;
          background: rgba(99, 102, 241, 0.08);
          border: 1px solid rgba(99, 102, 241, 0.2);
          padding: 5px 12px 5px 6px;
          border-radius: var(--saas-radius-full);
        }

        .supervisor-av-circle {
          width: 24px;
          height: 24px;
          border-radius: 50%;
          background: rgba(99, 102, 241, 0.3);
          color: #a5b4fc;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .supervisor-role-title {
          letter-spacing: 0.01em;
        }

        /* Live Ribbon */
        .supervisor-live-ribbon {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 10px 20px;
          background: linear-gradient(90deg, rgba(16, 185, 129, 0.2) 0%, rgba(6, 78, 59, 0.35) 100%);
          border: 1px solid rgba(16, 185, 129, 0.4);
          border-radius: var(--saas-radius-md);
          animation: ribbonGlow 2s infinite alternate;
          flex-shrink: 0;
        }

        @keyframes ribbonGlow {
          0% { box-shadow: 0 0 10px rgba(16, 185, 129, 0.2); }
          100% { box-shadow: 0 0 20px rgba(16, 185, 129, 0.4); }
        }

        .ribbon-content {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .ribbon-pulse-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #10b981;
          box-shadow: 0 0 8px #10b981;
          animation: pulseRecord 1.2s infinite;
        }

        .ribbon-text {
          font-size: 13px;
          color: #ecfdf5;
        }

        /* Body Layout Grid */
        .dashboard-body-grid {
          display: grid;
          grid-template-columns: 350px 1fr;
          gap: 14px;
          flex: 1;
          min-height: 0;
          height: 100%;
          overflow: hidden;
        }

        .dashboard-sidebar-column {
          display: flex;
          flex-direction: column;
          height: 100%;
          min-height: 0;
          overflow: hidden;
        }

        .sidebar-inner-card {
          padding: 14px;
          height: 100%;
          min-height: 0;
          box-sizing: border-box;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }

        .dashboard-stage-column {
          display: flex;
          flex-direction: column;
          height: 100%;
          min-height: 0;
          overflow: hidden;
        }

        .session-inspector-view {
          display: flex;
          flex-direction: column;
          gap: 12px;
          height: 100%;
          min-height: 0;
          overflow: hidden;
        }

        /* Plate Card */
        .session-header-plate {
          padding: 14px 18px;
          display: flex;
          flex-direction: column;
          gap: 10px;
          flex-shrink: 0;
        }

        .plate-top-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 16px;
        }

        .caller-identity-group {
          display: flex;
          align-items: center;
          gap: 14px;
        }

        .caller-av-box {
          width: 44px;
          height: 44px;
          border-radius: var(--saas-radius-md);
          background: rgba(99, 102, 241, 0.1);
          color: #8b5cf6;
          display: flex;
          align-items: center;
          justify-content: center;
          border: 1px solid rgba(99, 102, 241, 0.2);
        }

        .caller-text-group {
          display: flex;
          flex-direction: column;
          gap: 3px;
        }

        .caller-name-heading-row {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .caller-full-name {
          font-family: var(--saas-font-display);
          font-size: 20px;
          font-weight: 700;
          color: #ffffff;
          margin: 0;
          letter-spacing: -0.02em;
        }

        .status-badge-saas {
          display: inline-flex;
          align-items: center;
          padding: 2px 8px;
          border-radius: var(--saas-radius-full);
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.04em;
          text-transform: uppercase;
        }

        .badge-saas-escalated {
          background: rgba(239, 68, 68, 0.15);
          color: #fca5a5;
          border: 1px solid rgba(239, 68, 68, 0.35);
        }

        .badge-saas-active {
          background: rgba(16, 185, 129, 0.12);
          color: #34d399;
          border: 1px solid rgba(16, 185, 129, 0.25);
        }

        .badge-saas-ended {
          background: rgba(255, 255, 255, 0.05);
          color: #94a3b8;
          border: 1px solid var(--saas-border-subtle);
        }

        .room-subtag {
          font-size: 12px;
          color: var(--saas-text-muted);
        }

        .plate-divider-line {
          height: 1px;
          background: var(--saas-border-subtle);
          width: 100%;
        }

        /* Meta Grid */
        .session-meta-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
          gap: 16px;
        }

        .meta-data-cell {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .cell-label {
          font-size: 10.5px;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: var(--saas-text-muted);
          font-weight: 600;
        }

        .cell-value {
          font-size: 13.5px;
          font-weight: 500;
          color: #cbd5e1;
        }

        .cell-highlight {
          color: #ffffff;
          font-weight: 600;
        }

        .post-call-summary-strip {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          padding: 10px 14px;
          background: rgba(99, 102, 241, 0.05);
          border: 1px solid rgba(99, 102, 241, 0.12);
          border-radius: var(--saas-radius-md);
          font-size: 12.5px;
          line-height: 1.45;
        }

        .summary-title {
          font-weight: 700;
          color: #a5b4fc;
          flex-shrink: 0;
        }

        .summary-text {
          color: #e2e8f0;
        }

        /* Welcome Empty State */
        .stage-empty-welcome {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          text-align: center;
          padding: 60px 32px;
          gap: 16px;
        }

        .welcome-halo-icon {
          width: 72px;
          height: 72px;
          border-radius: 50%;
          background: rgba(99, 102, 241, 0.08);
          color: var(--saas-brand-primary);
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 0 35px var(--saas-brand-glow);
          animation: floatSparkle 3s ease-in-out infinite;
        }

        @keyframes floatSparkle {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-6px); }
        }

        .welcome-main-title {
          font-family: var(--saas-font-display);
          font-size: 22px;
          font-weight: 800;
          letter-spacing: -0.02em;
          color: #ffffff;
          margin: 0;
        }

        .welcome-sub-lead {
          font-size: 14px;
          color: var(--saas-text-secondary);
          max-width: 460px;
          line-height: 1.55;
          margin: 0;
        }

        .quick-guide-card {
          margin-top: 16px;
          background: rgba(255, 255, 255, 0.025);
          border: 1px solid var(--saas-border-subtle);
          padding: 20px 24px;
          border-radius: var(--saas-radius-lg);
          max-width: 580px;
          width: 100%;
          text-align: left;
          box-sizing: border-box;
          display: flex;
          flex-direction: column;
          gap: 14px;
        }

        .guide-header {
          display: flex;
          align-items: center;
          gap: 9px;
        }

        .guide-info-icon {
          color: var(--saas-brand-violet);
        }

        .guide-header h4 {
          font-family: var(--saas-font-display);
          font-size: 13.5px;
          font-weight: 700;
          color: #ffffff;
          margin: 0;
          letter-spacing: -0.01em;
        }

        .guide-steps-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .guide-step-item {
          display: flex;
          align-items: flex-start;
          gap: 10px;
        }

        .step-num {
          width: 18px;
          height: 18px;
          border-radius: 50%;
          background: rgba(99, 102, 241, 0.15);
          color: #a5b4fc;
          font-size: 10.5px;
          font-weight: 700;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          margin-top: 1px;
        }

        .guide-step-item p {
          margin: 0;
          font-size: 12.5px;
          color: var(--saas-text-secondary);
          line-height: 1.45;
        }

        .guide-step-item strong {
          color: #e2e8f0;
        }

        @media (max-width: 1080px) {
          .dashboard-body-grid {
            grid-template-columns: 1fr;
          }
          .dashboard-sidebar-column {
            max-height: 380px;
          }
        }

        @media (max-width: 640px) {
          .saas-dashboard-shell {
            padding: 12px 14px 20px;
          }
          .dashboard-top-navbar {
            padding: 12px 16px;
          }
          .navbar-right {
            display: none;
          }
          .plate-top-row {
            flex-direction: column;
            align-items: flex-start;
          }
        }
      `}</style>
    </div>
  );
}
