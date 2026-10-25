import React, { useEffect, useState, useRef } from 'react';
import { MessageSquare, RefreshCw, User, Bot, Headphones, AlertCircle, Copy, Check, Play } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

export default function TranscriptView({ sessionId }) {
  const [transcript, setTranscript] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pollingActive, setPollingActive] = useState(true);
  const [copied, setCopied] = useState(false);
  const messagesEndRef = useRef(null);
  const transcriptScrollRef = useRef(null);

  // Reset polling state when selected session changes
  useEffect(() => {
    if (sessionId) {
      setPollingActive(true);
    }
  }, [sessionId]);

  // Poll for transcripts — chained setTimeout
  useEffect(() => {
    if (!sessionId) return;

    let cancelled = false;
    let timeoutId = null;

    setLoading(true);
    const fetchTranscript = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/rooms/${sessionId}/transcript`);
        if (!response.ok) {
          throw new Error('Failed to fetch transcript');
        }
        const data = await response.json();
        if (!cancelled) {
          setTranscript(data.transcript || []);

          // If the call has finished, turn off live syncing
          if (data.status && data.status !== 'active' && data.status !== 'escalated') {
            setPollingActive(false);
          }
        }
      } catch (err) {
        console.error('Error fetching transcript:', err);
      } finally {
        if (!cancelled) {
          setLoading(false);
          if (pollingActive) {
            timeoutId = setTimeout(fetchTranscript, 2000);
          }
        }
      }
    };

    fetchTranscript();

    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [sessionId, pollingActive]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript]);

  // Copy transcript to clipboard
  const handleCopyTranscript = () => {
    if (transcript.length === 0) return;
    const formatted = transcript
      .map((msg) => `[${(msg.role || 'user').toUpperCase()}]: ${msg.content}`)
      .join('\n\n');
    navigator.clipboard.writeText(formatted);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Helper to identify message role type
  const getRoleCategory = (role, content) => {
    const r = (role || '').toLowerCase();
    if (r === 'agent' || r === 'assistant' || r === 'ai') return 'ai';
    if (r === 'human_agent' || r === 'supervisor') return 'human_agent';
    if (r === 'system' || content?.includes('support ticket') || content?.includes('transferring')) return 'system';
    return 'user';
  };

  if (!sessionId) {
    return (
      <div className="transcript-empty-shell saas-card-glass">
        <div className="empty-icon-halo">
          <MessageSquare size={36} className="empty-chat-icon" />
        </div>
        <h4 className="empty-heading">No Call Selected</h4>
        <p className="empty-sub">Select any session from the left queue to stream its conversation transcript.</p>
      </div>
    );
  }

  return (
    <div className="saas-transcript-card saas-card-glass">
      {/* Header Toolbar */}
      <div className="transcript-top-header">
        <div className="header-meta-left">
          <div className="chat-header-icon-box">
            <MessageSquare size={16} />
          </div>
          <div className="title-group">
            <h4 className="transcript-heading">Live Conversation Stream</h4>
            <span className="msg-counter-tag">{transcript.length} Utterances</span>
          </div>
        </div>

        <div className="header-actions-right">
          {/* Copy Transcript Button */}
          {transcript.length > 0 && (
            <button
              className="saas-icon-action-btn"
              onClick={handleCopyTranscript}
              title="Copy Full Transcript"
            >
              {copied ? <Check size={14} className="text-emerald" /> : <Copy size={14} />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          )}

          {/* Live Syncing Toggle */}
          <button
            className={`saas-sync-toggle-btn ${pollingActive ? 'is-live' : 'is-paused'}`}
            onClick={() => setPollingActive(!pollingActive)}
            title={pollingActive ? 'Pause real-time stream' : 'Resume real-time stream'}
          >
            <RefreshCw size={13} className={pollingActive ? 'spin-smooth' : ''} />
            <span>{pollingActive ? 'Live Syncing' : 'Paused'}</span>
          </button>
        </div>
      </div>

      {/* Amber Alert Banner when Live Sync is Paused */}
      {!pollingActive && (
        <div className="sync-paused-banner">
          <div className="banner-left">
            <AlertCircle size={15} className="banner-icon-amber" />
            <span>Live stream is paused. New utterances will not appear automatically.</span>
          </div>
          <button className="resume-stream-btn" onClick={() => setPollingActive(true)}>
            <Play size={12} />
            <span>Resume Stream</span>
          </button>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="transcript-scroll-viewport" ref={transcriptScrollRef}>
        {loading && transcript.length === 0 ? (
          <div className="transcript-skeleton-loader">
            <div className="skeleton-msg-row user-side">
              <div className="skeleton-bubble user-bubble saas-skeleton" />
            </div>
            <div className="skeleton-msg-row agent-side">
              <div className="skeleton-bubble agent-bubble saas-skeleton" />
            </div>
            <div className="skeleton-msg-row user-side">
              <div className="skeleton-bubble user-bubble saas-skeleton" />
            </div>
          </div>
        ) : transcript.length === 0 ? (
          <div className="transcript-waiting-state">
            <div className="waiting-pulse-dot" />
            <p className="waiting-lead">Session connected. Waiting for customer or AI speech...</p>
            <span className="waiting-sub">Utterances will appear here as soon as speech is committed.</span>
          </div>
        ) : (
          <div className="transcript-conversation-thread">
            {transcript.map((msg, index) => {
              const category = getRoleCategory(msg.role, msg.content);

              if (category === 'system') {
                return (
                  <div
                    key={msg.sequence != null ? `sys-${msg.sequence}` : `idx-${index}`}
                    className="system-event-row"
                  >
                    <div className="system-event-chip">
                      <AlertCircle size={13} className="event-icon" />
                      <span>{msg.content}</span>
                    </div>
                  </div>
                );
              }

              const isUser = category === 'user';
              const isSupervisor = category === 'human_agent';

              return (
                <div
                  key={msg.sequence != null ? `seq-${msg.sequence}` : `idx-${index}`}
                  className={`dialogue-row ${isUser ? 'align-user' : isSupervisor ? 'align-supervisor' : 'align-ai'}`}
                >
                  <div className={`message-card-bubble ${isUser ? 'bubble-user' : isSupervisor ? 'bubble-supervisor' : 'bubble-ai'}`}>
                    {/* Header Avatar & Tag */}
                    <div className="bubble-header-strip">
                      <div className="sender-identity-lockup">
                        <div className={`avatar-pill ${isUser ? 'user-av' : isSupervisor ? 'sup-av' : 'ai-av'}`}>
                          {isUser ? (
                            <User size={12} />
                          ) : isSupervisor ? (
                            <Headphones size={12} />
                          ) : (
                            <Bot size={12} />
                          )}
                        </div>
                        <span className="sender-display-name">
                          {isUser ? 'Customer' : isSupervisor ? 'Supervisor (Human)' : 'Epixa AI'}
                        </span>
                      </div>

                      {msg.sequence != null && (
                        <span className="utterance-turn-tag saas-mono">#{msg.sequence}</span>
                      )}
                    </div>

                    {/* Speech Text Content */}
                    <div className="bubble-text-content">
                      <p>{msg.content}</p>
                    </div>
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <style>{`
        .saas-transcript-card {
          display: flex;
          flex-direction: column;
          border-radius: var(--saas-radius-lg);
          flex: 1;
          min-height: 0;
          height: 100%;
          overflow: hidden;
          background: rgba(12, 15, 22, 0.75);
        }

        .transcript-empty-shell {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 40px 24px;
          height: 100%;
          text-align: center;
          gap: 12px;
        }

        .empty-icon-halo {
          width: 64px;
          height: 64px;
          border-radius: 50%;
          background: rgba(99, 102, 241, 0.08);
          color: #818cf8;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .empty-heading {
          font-family: var(--saas-font-display);
          font-size: 18px;
          font-weight: 700;
          color: #ffffff;
          margin: 0;
        }

        .empty-sub {
          font-size: 13px;
          color: var(--saas-text-muted);
          max-width: 340px;
          line-height: 1.5;
        }

        /* Top Header */
        .transcript-top-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 14px 20px;
          border-bottom: 1px solid var(--saas-border-subtle);
          background: rgba(15, 18, 26, 0.9);
          backdrop-filter: blur(12px);
          gap: 12px;
        }

        .header-meta-left {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .chat-header-icon-box {
          width: 30px;
          height: 30px;
          border-radius: var(--saas-radius-sm);
          background: rgba(99, 102, 241, 0.12);
          color: #818cf8;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .title-group {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .transcript-heading {
          font-family: var(--saas-font-display);
          font-size: 14.5px;
          font-weight: 700;
          color: #ffffff;
          margin: 0;
          letter-spacing: -0.01em;
        }

        .msg-counter-tag {
          font-size: 11px;
          font-weight: 600;
          color: #94a3b8;
          background: rgba(255, 255, 255, 0.05);
          padding: 2px 7px;
          border-radius: var(--saas-radius-full);
        }

        .header-actions-right {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .saas-icon-action-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 5px 10px;
          border-radius: var(--saas-radius-md);
          font-family: var(--saas-font-sans);
          font-size: 12px;
          font-weight: 500;
          color: #94a3b8;
          background: rgba(255, 255, 255, 0.04);
          border: 1px solid var(--saas-border-subtle);
          cursor: pointer;
          transition: all var(--saas-transition-fast);
        }

        .saas-icon-action-btn:hover {
          color: #ffffff;
          background: rgba(255, 255, 255, 0.08);
        }

        .saas-sync-toggle-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 5px 12px;
          border-radius: var(--saas-radius-full);
          font-family: var(--saas-font-sans);
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          border: 1px solid;
          transition: all var(--saas-transition-fast);
        }

        .saas-sync-toggle-btn.is-live {
          color: #34d399;
          background: rgba(16, 185, 129, 0.1);
          border-color: rgba(16, 185, 129, 0.3);
        }

        .saas-sync-toggle-btn.is-live:hover {
          background: rgba(16, 185, 129, 0.18);
        }

        .saas-sync-toggle-btn.is-paused {
          color: #f59e0b;
          background: rgba(245, 158, 11, 0.1);
          border-color: rgba(245, 158, 11, 0.3);
        }

        .saas-sync-toggle-btn.is-paused:hover {
          background: rgba(245, 158, 11, 0.18);
        }

        .spin-smooth {
          animation: spinSync 2.5s linear infinite;
        }

        @keyframes spinSync {
          to { transform: rotate(360deg); }
        }

        /* Paused Alert Banner */
        .sync-paused-banner {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 16px;
          background: rgba(245, 158, 11, 0.12);
          border-bottom: 1px solid rgba(245, 158, 11, 0.25);
          font-size: 12px;
          color: #fde68a;
          gap: 12px;
        }

        .banner-left {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .banner-icon-amber {
          color: #f59e0b;
          flex-shrink: 0;
        }

        .resume-stream-btn {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          padding: 3px 9px;
          border-radius: var(--saas-radius-sm);
          background: #f59e0b;
          color: #000000;
          font-size: 11px;
          font-weight: 700;
          border: none;
          cursor: pointer;
          transition: opacity var(--saas-transition-fast);
        }

        .resume-stream-btn:hover {
          opacity: 0.9;
        }

        /* Viewport */
        .transcript-scroll-viewport {
          flex: 1;
          padding: 20px;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 16px;
          background: radial-gradient(circle at top right, rgba(99, 102, 241, 0.03), transparent 60%);
        }

        .transcript-conversation-thread {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        /* Skeleton */
        .transcript-skeleton-loader {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .skeleton-msg-row {
          display: flex;
          width: 100%;
        }

        .skeleton-msg-row.user-side {
          justify-content: flex-end;
        }

        .skeleton-msg-row.agent-side {
          justify-content: flex-start;
        }

        .skeleton-bubble {
          height: 64px;
          border-radius: var(--saas-radius-lg);
        }

        .user-bubble {
          width: 60%;
        }

        .agent-bubble {
          width: 75%;
        }

        /* Waiting state */
        .transcript-waiting-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          gap: 8px;
          text-align: center;
          color: var(--saas-text-muted);
        }

        .waiting-pulse-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          background: var(--saas-brand-primary);
          animation: pulseRecord 1.6s infinite alternate;
          margin-bottom: 4px;
        }

        .waiting-lead {
          font-size: 13.5px;
          font-weight: 500;
          color: #cbd5e1;
          margin: 0;
        }

        .waiting-sub {
          font-size: 12px;
          color: #64748b;
        }

        /* Dialogue Bubble Rows */
        .dialogue-row {
          display: flex;
          width: 100%;
        }

        .align-user {
          justify-content: flex-end;
        }

        .align-ai, .align-supervisor {
          justify-content: flex-start;
        }

        .message-card-bubble {
          max-width: 82%;
          padding: 12px 16px;
          border-radius: var(--saas-radius-lg);
          display: flex;
          flex-direction: column;
          gap: 6px;
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
          position: relative;
        }

        /* Customer Style */
        .bubble-user {
          background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
          border: 1px solid rgba(59, 130, 246, 0.35);
          color: #ffffff;
          border-bottom-right-radius: 4px;
        }

        /* AI Epixa Style */
        .bubble-ai {
          background: rgba(22, 27, 38, 0.85);
          border: 1px solid rgba(139, 92, 246, 0.25);
          color: #e2e8f0;
          border-bottom-left-radius: 4px;
        }

        /* Supervisor Style */
        .bubble-supervisor {
          background: rgba(6, 78, 59, 0.6);
          border: 1px solid rgba(16, 185, 129, 0.4);
          color: #ffffff;
          border-bottom-left-radius: 4px;
        }

        .bubble-header-strip {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
        }

        .sender-identity-lockup {
          display: flex;
          align-items: center;
          gap: 7px;
        }

        .avatar-pill {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .user-av {
          background: rgba(255, 255, 255, 0.25);
          color: #ffffff;
        }

        .ai-av {
          background: rgba(139, 92, 246, 0.25);
          color: #c084fc;
        }

        .sup-av {
          background: rgba(16, 185, 129, 0.3);
          color: #6ee7b7;
        }

        .sender-display-name {
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.04em;
          text-transform: uppercase;
        }

        .bubble-user .sender-display-name {
          color: #bfdbfe;
        }

        .bubble-ai .sender-display-name {
          color: #c084fc;
        }

        .bubble-supervisor .sender-display-name {
          color: #a7f3d0;
        }

        .utterance-turn-tag {
          font-size: 10px;
          opacity: 0.6;
        }

        .bubble-text-content p {
          margin: 0;
          font-size: 14px;
          line-height: 1.5;
          word-break: break-word;
        }

        /* System Event Row */
        .system-event-row {
          display: flex;
          justify-content: center;
          width: 100%;
          margin: 4px 0;
        }

        .system-event-chip {
          display: inline-flex;
          align-items: center;
          gap: 7px;
          padding: 4px 14px;
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.25);
          border-radius: var(--saas-radius-full);
          font-size: 11.5px;
          font-weight: 600;
          color: #fca5a5;
        }

        .event-icon {
          color: #ef4444;
        }
      `}</style>
    </div>
  );
}
