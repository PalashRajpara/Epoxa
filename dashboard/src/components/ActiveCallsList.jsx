import React, { useEffect, useState } from 'react';
import { Users, ShieldAlert, Clock, PhoneOff, Search, Sparkles } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

export default function ActiveCallsList({ selectedCall, onSelectCall }) {
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('all'); // 'all' | 'live' | 'escalated' | 'ended'
  const [searchQuery, setSearchQuery] = useState('');

  // Poll for active calls every 3 seconds — chained setTimeout to prevent request pileup
  useEffect(() => {
    let cancelled = false;
    let timeoutId = null;

    const fetchActiveCalls = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/rooms/active-sessions`);
        if (!response.ok) {
          throw new Error('Failed to retrieve active call sessions from backend.');
        }
        const data = await response.json();
        if (!cancelled) {
          setCalls(data.sessions || []);
          setError(null);
        }
      } catch (err) {
        console.error('Error fetching active calls:', err);
        if (!cancelled) {
          setError('Live database sync offline');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
          timeoutId = setTimeout(fetchActiveCalls, 3000);
        }
      }
    };

    fetchActiveCalls();
    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, []);

  // Filter calculations
  const liveCalls = calls.filter(c => c.status === 'active' || c.status === 'escalated');
  const escalatedCalls = calls.filter(c => c.status === 'escalated');
  const endedCalls = calls.filter(c => c.status !== 'active' && c.status !== 'escalated');

  // Filter calls by tab and search
  const getFilteredCalls = () => {
    let list = calls;
    if (activeTab === 'live') {
      list = liveCalls;
    } else if (activeTab === 'escalated') {
      list = escalatedCalls;
    } else if (activeTab === 'ended') {
      list = endedCalls;
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(c => 
        (c.participant_name && c.participant_name.toLowerCase().includes(q)) ||
        (c.room_name && c.room_name.toLowerCase().includes(q)) ||
        (c.id && c.id.toLowerCase().includes(q))
      );
    }

    return list;
  };

  const filteredCalls = getFilteredCalls();

  const renderCallCard = (call) => {
    const isEscalated = call.status === 'escalated';
    const isEnded = call.status === 'completed' || call.status === 'dropped' || call.status === 'error' || call.status === 'timeout';
    const isSelected = selectedCall && selectedCall.id === call.id;

    return (
      <div
        key={call.id}
        className={`saas-queue-card ${isSelected ? 'is-selected' : ''} ${isEscalated ? 'is-escalated' : ''} ${isEnded ? 'is-ended' : ''}`}
        onClick={() => onSelectCall(call)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onSelectCall(call); }}
      >
        {/* Card Header */}
        <div className="queue-card-header">
          <div className="session-id-tag">
            <span className="id-prefix">ID</span>
            <span className="id-code saas-mono">{call.id.substring(0, 8)}</span>
          </div>

          {isEscalated ? (
            <div className="badge-status badge-escalated">
              <ShieldAlert size={12} className="badge-icon-spin" />
              <span>Handoff Needed</span>
            </div>
          ) : isEnded ? (
            <div className="badge-status badge-ended">
              <PhoneOff size={11} />
              <span>{call.status === 'timeout' ? 'Timed Out' : 'Ended'}</span>
            </div>
          ) : (
            <div className="badge-status badge-active">
              <span className="pulse-green-dot" />
              <span>AI Active</span>
            </div>
          )}
        </div>

        {/* Customer & Room Info */}
        <div className="queue-card-body">
          <div className="customer-name-row">
            <Users size={14} className="user-icon-subtle" />
            <span className="customer-name-text">
              {call.participant_name || 'Anonymous Customer'}
            </span>
          </div>

          <div className="room-code-row">
            <span className="room-dim-label">Room:</span>
            <span className="room-code-tag saas-mono">{call.room_name}</span>
          </div>
        </div>

        {/* Card Footer: Timestamp & Duration */}
        <div className="queue-card-footer">
          <div className="time-info-group">
            <Clock size={11} className="time-icon" />
            <span>
              {new Date(call.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>

          <div className="card-open-prompt">
            <span>Inspect Call →</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="queue-panel-wrapper">
      {/* Panel Title & Status Header */}
      <div className="queue-panel-header">
        <div className="title-lockup">
          <h3 className="panel-heading">Live Support Sessions</h3>
          <span className="call-count-pill">{calls.length} Total</span>
        </div>

        {error && (
          <div className="error-chip" title={error}>
            <span className="error-dot" />
            <span>Sync Delayed</span>
          </div>
        )}
      </div>

      {/* Filter Tabs */}
      <div className="filter-tabs-track">
        <button
          className={`tab-btn ${activeTab === 'all' ? 'active' : ''}`}
          onClick={() => setActiveTab('all')}
        >
          <span>All</span>
          <span className="tab-count">{calls.length}</span>
        </button>

        <button
          className={`tab-btn ${activeTab === 'live' ? 'active' : ''}`}
          onClick={() => setActiveTab('live')}
        >
          <span className="tab-live-dot" />
          <span>Live</span>
          <span className="tab-count">{liveCalls.length}</span>
        </button>

        {escalatedCalls.length > 0 && (
          <button
            className={`tab-btn tab-escalated ${activeTab === 'escalated' ? 'active' : ''}`}
            onClick={() => setActiveTab('escalated')}
          >
            <ShieldAlert size={12} />
            <span>Alerts</span>
            <span className="tab-count-alert">{escalatedCalls.length}</span>
          </button>
        )}

        <button
          className={`tab-btn ${activeTab === 'ended' ? 'active' : ''}`}
          onClick={() => setActiveTab('ended')}
        >
          <span>Past</span>
          <span className="tab-count">{endedCalls.length}</span>
        </button>
      </div>

      {/* Search Filter Input */}
      <div className="search-bar-wrapper">
        <Search size={14} className="search-icon" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Filter by customer, room, or ID..."
          className="search-input-field"
        />
        {searchQuery && (
          <button onClick={() => setSearchQuery('')} className="search-clear-btn">
            ×
          </button>
        )}
      </div>

      {/* Main List Area */}
      <div className="queue-list-container">
        {loading && calls.length === 0 ? (
          /* Shimmer Skeletons */
          <div className="skeleton-list">
            <div className="queue-skeleton-card saas-skeleton" />
            <div className="queue-skeleton-card saas-skeleton" />
            <div className="queue-skeleton-card saas-skeleton" />
          </div>
        ) : filteredCalls.length === 0 ? (
          <div className="queue-empty-state">
            <div className="empty-sparkle-box">
              <Sparkles size={20} className="empty-sparkle-icon" />
            </div>
            <p className="empty-title">No sessions found</p>
            <span className="empty-desc">
              {searchQuery
                ? `No calls matching "${searchQuery}".`
                : activeTab === 'escalated'
                ? 'No human agent escalations pending.'
                : 'Customer calls will populate here in real time.'}
            </span>
          </div>
        ) : (
          <div className="queue-cards-column">
            {filteredCalls.map(renderCallCard)}
          </div>
        )}
      </div>

      <style>{`
        .queue-panel-wrapper {
          display: flex;
          flex-direction: column;
          gap: 12px;
          height: 100%;
          min-height: 0;
          overflow: hidden;
        }

        .queue-panel-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding-bottom: 2px;
        }

        .title-lockup {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .panel-heading {
          font-family: var(--saas-font-display);
          font-size: 16px;
          font-weight: 700;
          color: var(--saas-text-primary);
          margin: 0;
          letter-spacing: -0.02em;
        }

        .call-count-pill {
          font-size: 11px;
          font-weight: 600;
          color: #94a3b8;
          background: rgba(255, 255, 255, 0.05);
          padding: 2px 8px;
          border-radius: var(--saas-radius-full);
          border: 1px solid var(--saas-border-subtle);
        }

        .error-chip {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 11px;
          color: #fca5a5;
          background: rgba(239, 68, 68, 0.1);
          padding: 3px 8px;
          border-radius: var(--saas-radius-full);
          border: 1px solid rgba(239, 68, 68, 0.25);
        }

        .error-dot {
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: #ef4444;
        }

        /* Filter Tabs Track */
        .filter-tabs-track {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 4px;
          background: rgba(10, 13, 20, 0.6);
          border: 1px solid var(--saas-border-subtle);
          border-radius: var(--saas-radius-md);
          overflow-x: auto;
        }

        .tab-btn {
          flex: 1;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          padding: 6px 8px;
          border-radius: var(--saas-radius-sm);
          font-family: var(--saas-font-sans);
          font-size: 12px;
          font-weight: 600;
          color: #94a3b8;
          background: transparent;
          border: none;
          cursor: pointer;
          transition: all var(--saas-transition-fast);
          white-space: nowrap;
        }

        .tab-btn:hover {
          color: #e2e8f0;
          background: rgba(255, 255, 255, 0.04);
        }

        .tab-btn.active {
          color: #ffffff;
          background: rgba(99, 102, 241, 0.18);
          box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
        }

        .tab-count {
          font-size: 10px;
          color: #64748b;
          background: rgba(255, 255, 255, 0.05);
          padding: 1px 5px;
          border-radius: var(--saas-radius-full);
        }

        .tab-btn.active .tab-count {
          color: #c7d2fe;
          background: rgba(99, 102, 241, 0.3);
        }

        .tab-live-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background-color: var(--saas-emerald);
          box-shadow: 0 0 6px var(--saas-emerald);
        }

        .tab-escalated {
          color: #fca5a5 !important;
        }

        .tab-escalated.active {
          background: rgba(239, 68, 68, 0.2) !important;
        }

        .tab-count-alert {
          font-size: 10px;
          font-weight: 700;
          color: #ffffff;
          background: #ef4444;
          padding: 1px 5px;
          border-radius: var(--saas-radius-full);
          animation: pulseBadge 1.5s infinite;
        }

        @keyframes pulseBadge {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }

        /* Search Bar */
        .search-bar-wrapper {
          position: relative;
          display: flex;
          align-items: center;
          width: 100%;
        }

        .search-icon {
          position: absolute;
          left: 12px;
          color: #64748b;
          pointer-events: none;
        }

        .search-input-field {
          width: 100%;
          padding: 8px 30px 8px 34px;
          border-radius: var(--saas-radius-md);
          border: 1px solid var(--saas-border-subtle);
          background: rgba(10, 13, 20, 0.5);
          color: #ffffff;
          font-family: var(--saas-font-sans);
          font-size: 12.5px;
          outline: none;
          box-sizing: border-box;
          transition: all var(--saas-transition-fast);
        }

        .search-input-field:focus {
          border-color: var(--saas-brand-primary);
          background: rgba(15, 18, 25, 0.8);
          box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
        }

        .search-input-field::placeholder {
          color: #475569;
        }

        .search-clear-btn {
          position: absolute;
          right: 10px;
          background: transparent;
          border: none;
          color: #94a3b8;
          font-size: 16px;
          cursor: pointer;
          padding: 0;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        /* Queue List Container */
        .queue-list-container {
          flex: 1;
          min-height: 0;
          overflow-y: auto;
          padding-right: 4px;
        }

        .queue-cards-column {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .skeleton-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .queue-skeleton-card {
          height: 108px;
          border-radius: var(--saas-radius-lg);
        }

        /* Call Card */
        .saas-queue-card {
          padding: 14px 16px;
          border-radius: var(--saas-radius-lg);
          background: var(--saas-surface-glass);
          border: 1px solid var(--saas-border-subtle);
          display: flex;
          flex-direction: column;
          gap: 10px;
          cursor: pointer;
          transition: all var(--saas-transition-fast);
          position: relative;
          outline: none;
        }

        .saas-queue-card:hover {
          background: rgba(22, 27, 38, 0.8);
          border-color: rgba(255, 255, 255, 0.15);
          transform: translateY(-1px);
        }

        .saas-queue-card.is-selected {
          background: rgba(99, 102, 241, 0.08);
          border-color: var(--saas-brand-primary);
          box-shadow: 0 0 16px rgba(99, 102, 241, 0.2);
        }

        .saas-queue-card.is-escalated {
          border-left: 4px solid var(--saas-rose);
          background: rgba(239, 68, 68, 0.04);
        }

        .saas-queue-card.is-escalated.is-selected {
          border-color: var(--saas-rose);
          background: rgba(239, 68, 68, 0.08);
          box-shadow: 0 0 16px var(--saas-rose-glow);
        }

        .saas-queue-card.is-ended {
          opacity: 0.65;
          background: rgba(10, 13, 20, 0.4);
        }

        .saas-queue-card.is-ended:hover {
          opacity: 0.95;
        }

        /* Queue Card Internal Layout */
        .queue-card-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .session-id-tag {
          display: flex;
          align-items: center;
          gap: 5px;
          font-size: 11px;
        }

        .id-prefix {
          font-weight: 600;
          color: #64748b;
          text-transform: uppercase;
        }

        .id-code {
          font-weight: 600;
          color: #cbd5e1;
        }

        .badge-status {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          font-size: 11px;
          font-weight: 600;
          padding: 2px 8px;
          border-radius: var(--saas-radius-full);
          letter-spacing: 0.02em;
        }

        .badge-active {
          background: rgba(16, 185, 129, 0.12);
          color: #34d399;
          border: 1px solid rgba(16, 185, 129, 0.25);
        }

        .pulse-green-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: #10b981;
          box-shadow: 0 0 6px #10b981;
        }

        .badge-escalated {
          background: rgba(239, 68, 68, 0.15);
          color: #fca5a5;
          border: 1px solid rgba(239, 68, 68, 0.35);
          animation: alertPulse 1.8s infinite;
        }

        @keyframes alertPulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
          50% { box-shadow: 0 0 0 4px rgba(239, 68, 68, 0); }
        }

        .badge-ended {
          background: rgba(255, 255, 255, 0.05);
          color: #94a3b8;
          border: 1px solid var(--saas-border-subtle);
        }

        .queue-card-body {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .customer-name-row {
          display: flex;
          align-items: center;
          gap: 7px;
        }

        .user-icon-subtle {
          color: #818cf8;
        }

        .customer-name-text {
          font-size: 14.5px;
          font-weight: 600;
          color: #ffffff;
        }

        .room-code-row {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 11.5px;
        }

        .room-dim-label {
          color: var(--saas-text-muted);
        }

        .room-code-tag {
          color: #94a3b8;
        }

        .queue-card-footer {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding-top: 6px;
          border-top: 1px solid rgba(255, 255, 255, 0.04);
          font-size: 11px;
        }

        .time-info-group {
          display: flex;
          align-items: center;
          gap: 5px;
          color: #64748b;
        }

        .card-open-prompt {
          color: var(--saas-brand-primary);
          font-weight: 600;
          opacity: 0;
          transform: translateX(-4px);
          transition: all var(--saas-transition-fast);
        }

        .saas-queue-card:hover .card-open-prompt {
          opacity: 1;
          transform: translateX(0);
        }

        /* Empty State */
        .queue-empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 48px 16px;
          text-align: center;
          background: rgba(255, 255, 255, 0.015);
          border: 1px dashed var(--saas-border-subtle);
          border-radius: var(--saas-radius-lg);
          gap: 8px;
        }

        .empty-sparkle-box {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background: rgba(99, 102, 241, 0.08);
          color: #818cf8;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 4px;
        }

        .empty-title {
          font-size: 13.5px;
          font-weight: 600;
          color: #cbd5e1;
          margin: 0;
        }

        .empty-desc {
          font-size: 12px;
          color: var(--saas-text-muted);
          max-width: 240px;
          line-height: 1.4;
        }
      `}</style>
    </div>
  );
}
