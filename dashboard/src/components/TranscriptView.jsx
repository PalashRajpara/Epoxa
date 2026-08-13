import React, { useEffect, useState, useRef } from 'react';
import { MessageSquare, RefreshCw, User, Bot } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

export default function TranscriptView({ sessionId }) {
  const [transcript, setTranscript] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pollingActive, setPollingActive] = useState(true);
  const messagesEndRef = useRef(null);

  // Reset polling state when selected session changes
  useEffect(() => {
    if (sessionId) {
      setPollingActive(true);
    }
  }, [sessionId]);

  // Poll for transcripts
  useEffect(() => {
    if (!sessionId) return;
    
    setLoading(true);
    const fetchTranscript = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/rooms/${sessionId}/transcript`);
        if (!response.ok) {
          throw new Error('Failed to fetch transcript');
        }
        const data = await response.json();
        setTranscript(data.transcript || []);
        
        // If the call has finished (status is completed, dropped, etc.), turn off live syncing
        if (data.status && data.status !== 'active' && data.status !== 'escalated') {
          setPollingActive(false);
          console.log(`[TranscriptView] Session ${sessionId.substring(0, 8)} ended. Stopping live sync.`);
        }
      } catch (err) {
        console.error('Error fetching transcript:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchTranscript();
    
    // Poll every 2 seconds during active sessions
    let interval;
    if (pollingActive) {
      interval = setInterval(fetchTranscript, 2000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [sessionId, pollingActive]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript]);

  if (!sessionId) {
    return (
      <div className="transcript-empty-state">
        <MessageSquare size={48} className="empty-icon text-muted" />
        <p>No Call Selected</p>
        <span>Select an active call session from the sidebar to inspect its live transcript.</span>
      </div>
    );
  }

  return (
    <div className="transcript-wrapper">
      <div className="transcript-header">
        <div className="header-title">
          <MessageSquare size={18} className="title-icon" />
          <h4>Live Transcript</h4>
        </div>
        <div className="header-actions">
          <button 
            className={`btn-icon ${pollingActive ? 'active' : ''}`}
            onClick={() => setPollingActive(!pollingActive)}
            title={pollingActive ? "Pause Auto-refresh" : "Resume Auto-refresh"}
          >
            <RefreshCw size={14} className={pollingActive ? "spinning" : ""} />
            <span>{pollingActive ? "Live Syncing" : "Paused"}</span>
          </button>
        </div>
      </div>

      <div className="transcript-messages">
        {loading && transcript.length === 0 ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading conversation history...</p>
          </div>
        ) : transcript.length === 0 ? (
          <div className="loading-state">
            <p className="no-msgs-text">Conversation started. Waiting for speech...</p>
          </div>
        ) : (
          <div className="message-list">
            {transcript.map((msg, index) => {
              const isUser = msg.role === 'user';
              
              return (
                <div key={index} className={`msg-row ${isUser ? 'user-row' : 'agent-row'}`}>
                  <div className="msg-bubble">
                    <div className="avatar-wrapper">
                      {isUser ? (
                        <div className="avatar user">
                          <User size={12} />
                        </div>
                      ) : (
                        <div className="avatar agent">
                          <Bot size={12} />
                        </div>
                      )}
                      <span className="sender-name">
                        {isUser ? 'Customer' : 'AI Assistant'}
                      </span>
                    </div>
                    <p className="msg-text">{msg.content}</p>
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <style>{`
        .transcript-empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          text-align: center;
          padding: 80px 20px;
          height: 350px;
          background: rgba(30, 41, 59, 0.15);
          border: 1px dashed rgba(255, 255, 255, 0.05);
          border-radius: 20px;
          color: #64748b;
        }

        .transcript-empty-state h3, .transcript-empty-state p {
          margin: 12px 0 6px 0;
          font-size: 18px;
          font-weight: 600;
          color: #94a3b8;
        }

        .transcript-empty-state span {
          font-size: 13px;
          max-width: 320px;
          line-height: 1.5;
        }

        .transcript-wrapper {
          display: flex;
          flex-direction: column;
          background: rgba(15, 23, 42, 0.4);
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-radius: 20px;
          height: 520px;
          overflow: hidden;
        }

        .transcript-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 16px 20px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.06);
          background: rgba(15, 23, 42, 0.6);
        }

        .header-title {
          display: flex;
          align-items: center;
          gap: 10px;
          color: #e2e8f0;
        }

        .header-title h4 {
          margin: 0;
          font-size: 15px;
          font-weight: 600;
        }

        .title-icon {
          color: #6366f1;
        }

        .btn-icon {
          background: rgba(255, 255, 255, 0.04);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 9999px;
          color: #94a3b8;
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          font-size: 11px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .btn-icon:hover {
          background: rgba(255, 255, 255, 0.08);
          color: #cbd5e1;
        }

        .btn-icon.active {
          color: #34d399;
          background: rgba(52, 211, 153, 0.08);
          border-color: rgba(52, 211, 153, 0.15);
        }

        .spinning {
          animation: spin 3s linear infinite;
        }

        .transcript-messages {
          flex: 1;
          padding: 20px;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 16px;
          background: radial-gradient(circle at bottom, rgba(15, 23, 42, 0.2), transparent);
        }

        .loading-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          gap: 12px;
          color: #64748b;
          font-size: 14px;
        }

        .no-msgs-text {
          font-style: italic;
        }

        .message-list {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .msg-row {
          display: flex;
          width: 100%;
        }

        .user-row {
          justify-content: flex-end;
        }

        .agent-row {
          justify-content: flex-start;
        }

        .msg-bubble {
          max-width: 80%;
          padding: 12px 16px;
          border-radius: 16px;
          display: flex;
          flex-direction: column;
          gap: 6px;
          line-height: 1.5;
        }

        .user-row .msg-bubble {
          background: #3b82f6;
          color: #ffffff;
          border-bottom-right-radius: 4px;
        }

        .agent-row .msg-bubble {
          background: rgba(255, 255, 255, 0.04);
          color: #e2e8f0;
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-bottom-left-radius: 4px;
        }

        .avatar-wrapper {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .avatar {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .avatar.user {
          background: rgba(255, 255, 255, 0.2);
          color: #ffffff;
        }

        .avatar.agent {
          background: rgba(99, 102, 241, 0.2);
          color: #a78bfa;
        }

        .sender-name {
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .user-row .sender-name {
          color: rgba(255, 255, 255, 0.7);
        }

        .agent-row .sender-name {
          color: #a78bfa;
        }

        .msg-text {
          margin: 0;
          font-size: 14px;
          white-space: pre-wrap;
          word-break: break-word;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
