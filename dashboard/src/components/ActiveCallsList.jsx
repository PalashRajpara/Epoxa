import React, { useEffect, useState } from 'react';
import { Phone, Users, ShieldAlert, Zap, Clock, PhoneOff } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

export default function ActiveCallsList({ selectedCall, onSelectCall }) {
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Poll for active calls every 3 seconds
  useEffect(() => {
    const fetchActiveCalls = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/rooms/active-sessions`);
        if (!response.ok) {
          throw new Error('Failed to retrieve active call sessions from backend.');
        }
        const data = await response.json();
        setCalls(data.sessions || []);
        setError(null);
      } catch (err) {
        console.error('Error fetching active calls:', err);
        setError('Connection to backend failed. Retrying...');
      } finally {
        setLoading(false);
      }
    };

    fetchActiveCalls();
    const interval = setInterval(fetchActiveCalls, 3000);
    return () => clearInterval(interval);
  }, []);

  if (loading && calls.length === 0) {
    return (
      <div className="status-container">
        <div className="spinner"></div>
        <p>Loading active sessions...</p>
      </div>
    );
  }

  const liveCalls = calls.filter(c => c.status === 'active' || c.status === 'escalated');
  const endedCalls = calls.filter(c => c.status !== 'active' && c.status !== 'escalated');

  const renderCallCard = (call) => {
    const isEscalated = call.status === 'escalated';
    const isEnded = call.status === 'completed' || call.status === 'dropped' || call.status === 'error' || call.status === 'timeout';
    const isSelected = selectedCall && selectedCall.id === call.id;
    
    return (
      <div
        key={call.id}
        className={`call-card glass ${isSelected ? 'selected' : ''} ${isEscalated ? 'escalated' : ''} ${isEnded ? 'ended' : ''}`}
        onClick={() => onSelectCall(call)}
      >
        {/* Header status bar */}
        <div className="card-top">
          <div className="call-id">
            <span className="id-label">Session ID:</span>
            <span className="id-val">{call.id.substring(0, 8)}</span>
          </div>
          
          {isEscalated ? (
            <div className="status-indicator alert pulsing">
              <ShieldAlert size={14} />
              <span>Needs Handoff</span>
            </div>
          ) : isEnded ? (
            <div className="status-indicator ended">
              <PhoneOff size={14} />
              <span>Call Ended</span>
            </div>
          ) : (
            <div className="status-indicator active">
              <Zap size={14} />
              <span>AI Active</span>
            </div>
          )}
        </div>

        {/* Details */}
        <div className="card-body">
          <div className="caller-info">
            <Users size={16} className="body-icon" />
            <span className="caller-name">
              {call.participant_name || 'Anonymous Customer'}
            </span>
          </div>
          
          <div className="room-info">
            <span className="room-label">Room:</span>
            <span className="room-val">{call.room_name}</span>
          </div>
        </div>

        {/* Duration/Footer */}
        <div className="card-footer">
          <div className="time-start">
            <Clock size={12} className="footer-icon" />
            {isEnded ? (
              <span>
                Started: {new Date(call.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                {call.ended_at && ` | Ended: ${new Date(call.ended_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`}
              </span>
            ) : (
              <span>Started: {new Date(call.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            )}
          </div>
          <span className="join-hint">Click to open</span>
        </div>
      </div>
    );
  };

  return (
    <div className="list-wrapper">
      <div className="list-header">
        <h3 className="section-title">Support Console ({calls.length})</h3>
        {error && <span className="error-badge">{error}</span>}
      </div>

      {calls.length === 0 ? (
        <div className="empty-state">
          <Phone size={36} className="empty-icon text-muted" />
          <p>No call sessions at the moment.</p>
          <span className="subtext">Calls will appear here as soon as customers join the queue.</span>
        </div>
      ) : (
        <div className="calls-grid">
          {liveCalls.length > 0 && (
            <div className="queue-section">
              <div className="queue-section-header">
                <span className="live-dot-pulse"></span>
                <h4>Live Queue ({liveCalls.length})</h4>
              </div>
              <div className="queue-cards">
                {liveCalls.map(renderCallCard)}
              </div>
            </div>
          )}
          
          {endedCalls.length > 0 && (
            <div className="queue-section">
              <div className="queue-section-header">
                <h4>Past Call Logs ({endedCalls.length})</h4>
              </div>
              <div className="queue-cards">
                {endedCalls.map(renderCallCard)}
              </div>
            </div>
          )}
        </div>
      )}

      <style>{`
        .list-wrapper {
          display: flex;
          flex-direction: column;
          gap: 16px;
          height: 100%;
        }

        .list-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .section-title {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
          color: #e2e8f0;
        }

        .error-badge {
          background: rgba(ef, 68, 68, 0.15);
          color: #f87171;
          border: 1px solid rgba(ef, 68, 68, 0.2);
          font-size: 12px;
          padding: 4px 8px;
          border-radius: 9999px;
          animation: pulse 2s infinite;
        }

        .status-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 40px;
          color: #94a3b8;
          gap: 12px;
        }

        .spinner {
          width: 24px;
          height: 24px;
          border: 2px solid rgba(255, 255, 255, 0.1);
          border-top-color: #6366f1;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
          padding: 60px 20px;
          background: rgba(30, 41, 59, 0.3);
          border: 1px dashed rgba(255, 255, 255, 0.08);
          border-radius: 20px;
          color: #94a3b8;
        }

        .empty-icon {
          margin-bottom: 16px;
          color: #475569;
        }

        .empty-state p {
          margin: 0 0 6px 0;
          font-weight: 500;
          font-size: 16px;
          color: #cbd5e1;
        }

        .subtext {
          font-size: 13px;
          color: #64748b;
        }

        .queue-section {
          display: flex;
          flex-direction: column;
          gap: 12px;
          margin-bottom: 8px;
        }

        .queue-section-header {
          display: flex;
          align-items: center;
          gap: 8px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.04);
          padding-bottom: 6px;
          margin-top: 4px;
        }

        .queue-section-header h4 {
          margin: 0;
          font-size: 13px;
          font-weight: 600;
          color: #64748b;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .live-dot-pulse {
          width: 8px;
          height: 8px;
          background-color: #10b981;
          border-radius: 50%;
          display: inline-block;
          box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
          animation: live-pulse-key 1.6s infinite;
        }

        @keyframes live-pulse-key {
          0% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
          }
          70% {
            transform: scale(1);
            box-shadow: 0 0 0 6px rgba(16, 185, 129, 0);
          }
          100% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
          }
        }

        .queue-cards {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .calls-grid {
          display: flex;
          flex-direction: column;
          gap: 20px;
          overflow-y: auto;
          max-height: calc(100vh - 220px);
          padding-right: 4px;
        }

        .call-card {
          padding: 16px;
          cursor: pointer;
          border: 1px solid rgba(255, 255, 255, 0.06);
          display: flex;
          flex-direction: column;
          gap: 12px;
          position: relative;
          overflow: hidden;
        }

        .call-card:hover {
          background: rgba(255, 255, 255, 0.03);
          border-color: rgba(255, 255, 255, 0.12);
          transform: translateY(-1px);
        }

        .call-card.selected {
          border-color: #6366f1;
          background: rgba(99, 102, 241, 0.06);
          box-shadow: 0 0 15px rgba(99, 102, 241, 0.15);
        }

        .call-card.escalated {
          border-left: 4px solid #ef4444;
        }

        .call-card.escalated.selected {
          border-color: #ef4444;
          background: rgba(239, 68, 68, 0.05);
          box-shadow: 0 0 15px rgba(239, 68, 68, 0.1);
        }

        .call-card.ended {
          opacity: 0.6;
          background: rgba(15, 23, 42, 0.45);
          border-color: rgba(255, 255, 255, 0.02);
          transition: all 0.2s ease;
        }

        .call-card.ended:hover {
          opacity: 0.95;
          background: rgba(15, 23, 42, 0.65);
        }

        .call-card.ended.selected {
          border-color: #475569;
          background: rgba(71, 85, 105, 0.08);
          box-shadow: 0 0 15px rgba(71, 85, 105, 0.1);
        }

        .card-top {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .call-id {
          font-size: 11px;
          font-family: monospace;
          color: #64748b;
        }

        .id-label {
          margin-right: 4px;
        }

        .id-val {
          color: #94a3b8;
          font-weight: 600;
        }

        .status-indicator {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 11px;
          font-weight: 600;
          padding: 2px 8px;
          border-radius: 9999px;
        }

        .status-indicator.active {
          background: rgba(16, 185, 129, 0.12);
          color: #34d399;
          border: 1px solid rgba(16, 185, 129, 0.2);
        }

        .status-indicator.alert {
          background: rgba(239, 68, 68, 0.12);
          color: #f87171;
          border: 1px solid rgba(239, 68, 68, 0.2);
        }

        .status-indicator.ended {
          background: rgba(148, 163, 184, 0.12);
          color: #94a3b8;
          border: 1px solid rgba(148, 163, 184, 0.2);
        }

        .pulsing {
          animation: card-pulse 1.5s ease-in-out infinite;
        }

        .card-body {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .caller-info {
          display: flex;
          align-items: center;
          gap: 8px;
          color: #cbd5e1;
        }

        .caller-name {
          font-size: 15px;
          font-weight: 500;
        }

        .body-icon {
          color: #94a3b8;
        }

        .room-info {
          display: flex;
          gap: 6px;
          font-size: 12px;
          color: #64748b;
          margin-left: 24px;
        }

        .room-val {
          color: #94a3b8;
          font-weight: 500;
        }

        .card-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 11px;
          color: #64748b;
          border-top: 1px solid rgba(255, 255, 255, 0.04);
          padding-top: 8px;
          margin-top: 4px;
        }

        .time-start {
          display: flex;
          align-items: center;
          gap: 4px;
        }

        .join-hint {
          color: #6366f1;
          font-weight: 500;
          opacity: 0;
          transition: opacity 0.2s ease;
        }

        .call-card:hover .join-hint {
          opacity: 1;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        @keyframes card-pulse {
          0%, 100% {
            box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4);
          }
          50% {
            box-shadow: 0 0 0 4px rgba(239, 68, 68, 0);
          }
        }
      `}</style>
    </div>
  );
}
