import React, { useState } from 'react';
import ActiveCallsList from './components/ActiveCallsList';
import TranscriptView from './components/TranscriptView';
import JoinCallButton from './components/JoinCallButton';
import { Shield, Sparkles, PhoneCall, HelpCircle, Activity } from 'lucide-react';

export default function App() {
  const [selectedCall, setSelectedCall] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected'); // 'disconnected' | 'connecting' | 'connected'

  const handleSelectCall = (call) => {
    // Only allow changing calls if not currently connected
    if (connectionStatus !== 'disconnected') {
      alert("Please disconnect from the current call before switching sessions.");
      return;
    }
    setSelectedCall(call);
  };

  return (
    <div className="dashboard-wrapper">
      {/* Upper header navigation */}
      <header className="dashboard-header glass">
        <div className="brand">
          <div className="logo-glow">
            <Shield size={24} className="brand-logo" />
          </div>
          <div className="brand-text">
            <h2>Epoxcel</h2>
            <span>Epixa Voice AI Support Console</span>
          </div>
        </div>
        <div className="system-status">
          <Activity size={14} className="pulse-green" />
          <span>System Status: Online</span>
        </div>
      </header>

      {/* Main dashboard content layout */}
      <main className="dashboard-main">
        {/* Sidebar container */}
        <section className="dashboard-sidebar">
          <div className="sidebar-card glass">
            <ActiveCallsList 
              selectedCall={selectedCall} 
              onSelectCall={handleSelectCall} 
            />
          </div>
        </section>

        {/* Content Pane container */}
        <section className="dashboard-content">
          {selectedCall ? (
            <div className="details-container">
              {/* Session summary card */}
              <div className="details-header-card glass">
                <div className="card-top">
                  <div className="meta-left">
                    <div className="call-avatar">
                      <PhoneCall size={20} />
                    </div>
                    <div>
                      <h3>{selectedCall.participant_name || 'Anonymous Customer'}</h3>
                      <span className="room-subtext">Active Room: {selectedCall.room_name}</span>
                    </div>
                  </div>
                  <div className="meta-right">
                    <JoinCallButton 
                      roomName={selectedCall.room_name}
                      sessionId={selectedCall.id}
                      status={selectedCall.status}
                      onConnectionChange={(status) => setConnectionStatus(status)}
                    />
                  </div>
                </div>
                
                <div className="card-divider"></div>
                
                <div className="meta-details-row">
                  <div className="meta-item">
                    <span className="label">Session ID</span>
                    <span className="val">{selectedCall.id.substring(0, 18)}...</span>
                  </div>
                  <div className="meta-item">
                    <span className="label">Status</span>
                    <span className={`val uppercase font-bold ${
                      selectedCall.status === 'escalated' ? 'text-accent' :
                      selectedCall.status === 'completed' || selectedCall.status === 'dropped' || selectedCall.status === 'error' || selectedCall.status === 'timeout' ? 'text-ended' : 'text-active'
                    }`}>
                      {selectedCall.status === 'escalated' ? 'Handoff Requested' :
                       selectedCall.status === 'completed' || selectedCall.status === 'dropped' || selectedCall.status === 'error' || selectedCall.status === 'timeout' ? 'Call Ended' : 'AI Active'}
                    </span>
                  </div>
                  <div className="meta-item">
                    <span className="label">Date</span>
                    <span className="val">{new Date(selectedCall.started_at).toLocaleDateString([], { month: 'short', day: '2-digit', year: 'numeric' })}</span>
                  </div>
                  <div className="meta-item">
                    <span className="label">Call Started</span>
                    <span className="val">{new Date(selectedCall.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                  </div>
                  {(selectedCall.status === 'completed' || selectedCall.status === 'dropped' || selectedCall.status === 'error' || selectedCall.status === 'timeout') && selectedCall.ended_at ? (
                    <div className="meta-item">
                      <span className="label">Call Ended</span>
                      <span className="val">{new Date(selectedCall.ended_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                    </div>
                  ) : (
                    <div className="meta-item">
                      <span className="label">Call Ended</span>
                      <span className="val" style={{ color: '#64748b' }}>Active</span>
                    </div>
                  )}
                  <div className="meta-item">
                    <span className="label">Duration</span>
                    <span className="val">
                      {selectedCall.duration_seconds 
                        ? `${Math.floor(selectedCall.duration_seconds / 60)}m ${selectedCall.duration_seconds % 60}s`
                        : 'Live'
                      }
                    </span>
                  </div>
                </div>
              </div>

              {/* Live transcript card */}
              <TranscriptView sessionId={selectedCall.id} />
            </div>
          ) : (
            <div className="empty-content-state glass">
              <Sparkles size={56} className="empty-sparkle" />
              <h3>Support Console Ready</h3>
              <p>No active call session is currently selected.</p>
              <span>Click on any customer call in the left panel to inspect the live transcript and join the conversation.</span>
              
              <div className="help-box">
                <HelpCircle size={16} className="help-icon" />
                <span>
                  <strong>Handoff Guide:</strong> When a customer's query requires human assistance, the call's status badge will turn red and pulse. Click the call, read the live transcript to gather context, and click <strong>Join Live Call</strong> to speak directly to the customer. When resolved, click <strong>Hand Back to AI</strong>.
                </span>
              </div>
            </div>
          )}
        </section>
      </main>

      <style>{`
        body {
          background-color: #090a0f !important;
          color: #e2e8f0;
          font-family: 'Outfit', sans-serif;
          margin: 0;
        }

        .dashboard-wrapper {
          max-width: 1400px;
          margin: 0 auto;
          padding: 24px;
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          gap: 24px;
          box-sizing: border-box;
        }

        /* Glassmorphism layout */
        .glass {
          background: rgba(20, 24, 33, 0.6);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border: 1px solid rgba(255, 255, 255, 0.05);
          border-radius: 24px;
          box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        }

        /* Header design */
        .dashboard-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 16px 32px;
          height: 72px;
          box-sizing: border-box;
        }

        .brand {
          display: flex;
          align-items: center;
          gap: 16px;
        }

        .logo-glow {
          width: 42px;
          height: 42px;
          background: linear-gradient(135deg, #a78bfa 0%, #6366f1 100%);
          border-radius: 14px;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
        }

        .brand-logo {
          color: white;
        }

        .brand-text h2 {
          margin: 0;
          font-size: 18px;
          font-weight: 700;
          letter-spacing: -0.5px;
          color: #ffffff;
        }

        .brand-text span {
          font-size: 12px;
          color: #94a3b8;
        }

        .system-status {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          font-weight: 500;
          color: #94a3b8;
          background: rgba(255, 255, 255, 0.03);
          padding: 6px 14px;
          border-radius: 9999px;
          border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .pulse-green {
          color: #10b981;
          animation: pulse-dot 1.5s infinite;
        }

        /* Main Workspace layout */
        .dashboard-main {
          display: grid;
          grid-template-columns: 360px 1fr;
          gap: 24px;
          flex: 1;
        }

        .dashboard-sidebar {
          display: flex;
          flex-direction: column;
        }

        .sidebar-card {
          padding: 24px;
          flex: 1;
          height: 100%;
        }

        .dashboard-content {
          display: flex;
          flex-direction: column;
          min-height: 520px;
        }

        .details-container {
          display: flex;
          flex-direction: column;
          gap: 20px;
          height: 100%;
        }

        .details-header-card {
          padding: 24px;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .card-top {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .meta-left {
          display: flex;
          align-items: center;
          gap: 16px;
        }

        .call-avatar {
          width: 48px;
          height: 48px;
          border-radius: 16px;
          background: rgba(99, 102, 241, 0.1);
          color: #8b5cf6;
          display: flex;
          align-items: center;
          justify-content: center;
          border: 1px solid rgba(99, 102, 241, 0.15);
        }

        .meta-left h3 {
          margin: 0;
          font-size: 20px;
          font-weight: 700;
          color: #ffffff;
        }

        .room-subtext {
          font-size: 13px;
          color: #94a3b8;
        }

        .card-divider {
          height: 1px;
          background: rgba(255, 255, 255, 0.05);
          width: 100%;
        }

        .meta-details-row {
          display: flex;
          gap: 40px;
          flex-wrap: wrap;
        }

        .meta-item {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .meta-item .label {
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: #64748b;
          font-weight: 600;
        }

        .meta-item .val {
          font-size: 14px;
          font-weight: 500;
          color: #cbd5e1;
        }

        .uppercase {
          text-transform: uppercase;
        }

        .font-bold {
          font-weight: 700 !important;
        }

        .text-accent {
          color: #f87171 !important;
        }

        .text-active {
          color: #34d399 !important;
        }

        .text-ended {
          color: #94a3b8 !important;
        }

        /* Empty state styling */
        .empty-content-state {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          text-align: center;
          padding: 80px 40px;
          color: #94a3b8;
        }

        .empty-sparkle {
          color: #6366f1;
          margin-bottom: 24px;
          filter: drop-shadow(0 0 15px rgba(99, 102, 241, 0.4));
          animation: float-sparkle 3s ease-in-out infinite;
        }

        .empty-content-state h3 {
          margin: 0 0 8px 0;
          font-size: 22px;
          font-weight: 700;
          color: #ffffff;
        }

        .empty-content-state p {
          margin: 0 0 16px 0;
          font-size: 16px;
          color: #cbd5e1;
        }

        .empty-content-state span {
          font-size: 14px;
          max-width: 440px;
          line-height: 1.6;
          color: #64748b;
        }

        .help-box {
          margin-top: 40px;
          background: rgba(99, 102, 241, 0.04);
          border: 1px solid rgba(99, 102, 241, 0.1);
          padding: 16px 20px;
          border-radius: 16px;
          max-width: 540px;
          display: flex;
          gap: 12px;
          text-align: left;
          font-size: 13px;
          line-height: 1.5;
          color: #94a3b8;
        }

        .help-icon {
          color: #8b5cf6;
          flex-shrink: 0;
          margin-top: 2px;
        }

        @keyframes pulse-dot {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }

        @keyframes float-sparkle {
          0%, 100% { transform: translateY(0) scale(1); }
          50% { transform: translateY(-8px) scale(1.05); }
        }

        @media (max-width: 1024px) {
          .dashboard-main {
            grid-template-columns: 1fr;
          }
          .dashboard-sidebar {
            max-height: 300px;
          }
        }
      `}</style>
    </div>
  );
}
